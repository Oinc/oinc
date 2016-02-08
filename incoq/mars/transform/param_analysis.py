"""Analysis of scopes, query parameters, and query demand."""


__all__ = [
    'make_demand_func',
    'determine_comp_demand_params',
    'make_demand_set',
    'make_demand_query',
    
    'ScopeBuilder',
    'CompContextTracker',
    
    'ParamAnalyzer',
    'DemandTransformer',
    
    'analyze_parameters',
    'transform_demand',
]


from itertools import chain

from incoq.util.collections import OrderedSet
from incoq.mars.type import T
from incoq.mars.symbol import S, N
from incoq.mars.incast import L


def make_demand_func(query):
    func = N.get_query_demand_func_name(query)
    uset = N.get_query_demand_set_name(query)
    return L.Parser.ps('''
        def _FUNC(_elem):
            if _elem not in _U:
                _U.reladd(_elem)
        ''', subst={'_FUNC': func, '_U': uset})


def determine_comp_demand_params(clausetools, comp, params, demand_params,
                                 demand_param_strat):
    """Given a Comp node, and values for the associated attributes
    params, demand_params, and demand_param_strat, return the proper
    demand_params.
    """
    assert isinstance(comp, L.Comp)
    strat = demand_param_strat
    
    if strat != S.Explicit and demand_params is not None:
        raise AssertionError('Do not supply demand_params unless '
                             'demand_param_strat is set to "explicit"')
    
    if strat == S.Unconstrained:
        uncon_vars = clausetools.uncon_lhs_vars_from_comp(comp)
        result  = tuple(p for p in params if p in uncon_vars)
    elif strat == S.All:
        result = params
    elif strat == S.Explicit:
        assert demand_params is not None
        result = demand_params
    else:
        assert()
    
    return result


def make_demand_set(symtab, query):
    """Create a demand set, update the query's demand_set attribute, and
    return the new demand set symbol.
    """
    uset_name = N.get_query_demand_set_name(query.name)
    uset_tuple = L.tuplify(query.demand_params)
    uset_tuple_type = symtab.analyze_expr_type(uset_tuple)
    uset_type = T.Set(uset_tuple_type)
    uset_sym = symtab.define_relation(uset_name, type=uset_type)
    
    query.demand_set = uset_name
    
    return uset_sym


def make_demand_query(symtab, query, left_clauses):
    """Create a demand query, update the query's demand_query attribute,
    and return the new demand query symbol.
    """
    ct = symtab.clausetools
    
    demquery_name = N.get_query_demand_query_name(query.name)
    
    demquery_tuple = L.tuplify(query.demand_params)
    demquery_tuple_type = symtab.analyze_expr_type(demquery_tuple)
    demquery_type = T.Set(demquery_tuple_type)
    
    demquery_comp = L.Comp(demquery_tuple, left_clauses)
    prefix = next(symtab.fresh_names.vars)
    demquery_comp = ct.comp_rename_lhs_vars(demquery_comp,
                                            lambda x: prefix + x)
    
    demquery_sym = symtab.define_query(demquery_name, type=demquery_type,
                                       node=demquery_comp, impl=query.impl)
    
    query.demand_query = demquery_name
    
    return demquery_sym


class ScopeBuilder(L.NodeVisitor):
    
    """Determine scope information for each Query node in the tree.
    Return a map from Query node identity (i.e. id(node)) to a pair
    of the node itself and a set of variables that are bound in scopes
    outside the node.
    
    Lexical scopes are introduced for the top level, function
    definitions, and comprehensions. Binding is flow-insensitive,
    so a name may be considered bound at a query even if it is only
    introduced below the query's occurrence.
    
    The map is keyed by Query node identity (its memory address), rather
    than by Query node value or query name, because multiple occurrences
    of the same query may have distinct scope information. This means
    that this information becomes stale and unusable when a Query node
    is transformed (even if it is replaced by a structurally identical
    copy). The node itself is included in the map value in case the user
    of the map does not already have a reference to the node, and to
    prevent the node from being garbage collected (which could lead to
    inconsistency if a new node is later allocated to the same address).
    
    If bindenv is given, these variables are assumed to be declared
    outside the given tree and are included in every scope.
    """
    
    # We maintain a scope stack -- a list of sets of bound variables,
    # one per scope, ordered outermost first. When a Query node is seen,
    # we add an entry in the map to a shallow copy of the current scope
    # stack, aliasing the underlying sets. This way, we include
    # identifiers that are only bound after the Query node is already
    # processed. At the end, we flatten the scope stacks into singular
    # sets.
    
    def __init__(self, *, bindenv=None):
        super().__init__()
        if bindenv is None:
            bindenv = []
        self.bindenv = OrderedSet(bindenv)
    
    def flatten_scope_stack(self, stack):
        return OrderedSet(chain(self.bindenv, *stack))
    
    def enter(self):
        self.current_stack.append(OrderedSet())
    
    def exit(self):
        self.current_stack.pop()
    
    def bind(self, name):
        self.current_stack[-1].add(name)
    
    def process(self, tree):
        self.current_stack = []
        self.query_scope_info = info = {}
        
        super().process(tree)
        assert len(self.current_stack) == 0
        
        for k, (node, stack) in info.items():
            info[k] = (node, self.flatten_scope_stack(stack))
        return info
    
    def visit_Module(self, node):
        self.enter()
        self.generic_visit(node)
        self.exit()
    
    def visit_fun(self, node):
        # Bind the name of the function in the outer scope,
        # its parameters in the inner scope.
        self.bind(node.name)
        self.enter()
        for a in node.args:
            self.bind(a)
        self.visit(node.body)
        self.exit()
    
    def visit_For(self, node):
        self.bind(node.target)
        self.generic_visit(node)
    
    def visit_DecompFor(self, node):
        for v in node.vars:
            self.bind(v)
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        self.bind(node.target)
        self.generic_visit(node)
    
    def visit_DecompAssign(self, node):
        for v in node.vars:
            self.bind(v)
        self.generic_visit(node)
    
    def visit_Query(self, node):
        # Shallow copy: The copy will be affected by adding new bindings
        # to stacks, but not by pushing and popping to the list itself.
        stack_copy = list(self.current_stack)
        self.query_scope_info[id(node)] = (node, stack_copy)
        self.generic_visit(node)
    
    def visit_Comp(self, node):
        self.enter()
        self.generic_visit(node)
        self.exit()
    
    def visit_RelMember(self, node):
        for v in node.vars:
            self.bind(v)
        self.generic_visit(node)
    
    def visit_SingMember(self, node):
        for v in node.vars:
            self.bind(v)
        self.generic_visit(node)
    
    def visit_VarsMember(self, node):
        for v in node.vars:
            self.bind(v)
        self.generic_visit(node)


class CompContextTracker(L.NodeTransformer):
    
    """Mixin for tracking what clauses we have already seen while
    processing a transformable comprehension query. A subclass can
    access this list by calling get_left_clauses().
    
    Comprehensions that are not the immediate child of a Query node,
    and comprehensions whose impl attribute is Normal, are not tracked
    in this manner.
    """
    
    def __init__(self, symtab):
        super().__init__()
        self.symtab = symtab
    
    def process(self, tree):
        self.comp_stack = []
        """Each stack entry corresponds to a level of nesting of a
        Query node for a comprehension whose impl is not Normal.
        The value of each entry is a list of the clauses at that
        level that have already been fully processed.
        """
        self.push_next_comp = False
        """Flag indicating whether the next call to visit_Comp should
        affect the comp stack. This is set when we are in the Query node
        just before we recurse. It helps us distinguish transformable
        comprehension queries from non-transformable ones and stray
        non-Query Comp nodes.
        """
        
        tree = super().process(tree)
        
        assert len(self.comp_stack) == 0
        return tree
    
    def push_comp(self):
        self.comp_stack.append([])
    
    def pop_comp(self):
        self.comp_stack.pop()
    
    def add_clause(self, cl):
        if len(self.comp_stack) > 0:
            self.comp_stack[-1].append(cl)
    
    def get_left_clauses(self):
        """Get the sequence of clauses to the left of the current
        containing comprehension query, or None if there is no such
        query.
        """
        if len(self.comp_stack) > 0:
            return tuple(self.comp_stack[-1])
        else:
            return None
    
    def comp_visit_helper(self, node):
        """Visit while marking clauses in the comp stack."""
        clauses = []
        for cl in node.clauses:
            cl = self.visit(cl)
            self.add_clause(cl)
            clauses.append(cl)
        resexp = self.visit(node.resexp)
        return node._replace(resexp=resexp, clauses=clauses)
    
    def visit_Comp(self, node):
        if self.push_next_comp:
            self.push_next_comp = False
            self.push_comp()
            node = self.comp_visit_helper(node)
            self.pop_comp()
        else:
            node = self.generic_visit(node)
        return node
    
    def visit_Query(self, node):
        query_sym = self.symtab.get_queries()[node.name]
        if (isinstance(node.query, L.Comp) and
            query_sym.impl != S.Normal):
            self.push_next_comp = True
        
        return self.generic_visit(node)


class ParamAnalyzer(L.NodeVisitor):
    
    """Annotate all query symbols with params and demand_params
    attribute info. Raise ProgramError if any query has multiple
    occurrences with inconsistent context information.
    """
    
    def __init__(self, symtab, scope_info):
        super().__init__()
        self.symtab = symtab
        self.scope_info = scope_info
        self.query_param_map = {}
        """Map from query name to param info."""
    
    def get_params(self, node):
        """Get parameters for the given query node. The node must be
        indexed in scope_info.
        """
        _node, scope = self.scope_info[id(node)]
        vars = L.IdentFinder.find_vars(node.query)
        params = tuple(vars.intersection(scope))
        return params
    
    def visit_Query(self, node):
        ct = self.symtab.clausetools
        querysym = self.symtab.get_queries()[node.name]
        cache = self.query_param_map
        
        # Analyze parameters from node.
        params = self.get_params(node)
        
        # If we've already analyzed this query, just confirm that this
        # occurrence's parameters match what we're expecting.
        if node.name in cache:
            if params != cache[node.name]:
                raise L.ProgramError('Inconsistent parameter info for query '
                                     '{}: {}, {}'.format(
                                     querysym.name, cache[node.name], params))
        
        # Otherwise, add to the cache and figure out the demand_params.
        else:
            cache[node.name] = params
            
            # Grab demand_params and demand_param_strat from symbol.
            demand_params = querysym.demand_params
            demand_param_strat = querysym.demand_param_strat
            
            # Compute final demand_params based on this info.
            if isinstance(node.query, L.Comp):
                demand_params = determine_comp_demand_params(
                                    ct, node.query, params, demand_params,
                                    demand_param_strat)
            elif isinstance(node.query, L.Aggr):
                # For aggregates, all parameters are demand parameters.
                demand_params = params
            
            else:
                raise L.ProgramError('No rule for analyzing parameters of '
                                     '{} query'.format(
                                     node.query.__class__.__name__))
            
            # Update the symbol.
            querysym.params = params
            querysym.demand_params = demand_params
        
        self.generic_visit(node)


class DemandTransformer(CompContextTracker):
    
    """Modify each query appearing in the tree to add demand. For
    comprehensions, this means adding a new clause, while for
    aggregates, it means turning an Aggr node into an AggrRestr node.
    
    Outer queries get a demand set, while inner queries get a demand
    query. The demand_set and demand_query symbol attributes are set
    accordingly.
    
    Only the first occurrence of a query triggers new processing.
    Subsequent occurrences are rewritten to be the same as the first.
    """
    
    # Demand rewriting happens in a top-down fashion, so that inner
    # queries are rewritten after their outer comprehensions already
    # have a clause over a demand set or demand query.
    
    def process(self, tree):
        self.queries_with_usets = OrderedSet()
        """Outer queries, for which a demand set and a call to a demand
        function are added.
        """
        self.rewrite_cache = {}
        """Map from query name to rewritten AST."""
        self.demand_queries = set()
        """Set of names of demand queries that we introduced, which
        shouldn't be recursed into.
        """
        
        return super().process(tree)
    
    def add_demand_function_call(self, query_sym, query_node):
        """Return a Query node wrapped with a call to a demand function,
        if needed.
        """
        # Skip if there's no demand set associated with this query.
        if query_sym.name not in self.queries_with_usets:
            return query_node
        
        demand_call = L.Call(N.get_query_demand_func_name(query_sym.name),
                             [L.tuplify(query_sym.demand_params)])
        return L.FirstThen(demand_call, query_node)
    
    def visit_Module(self, node):
        node = self.generic_visit(node)
        
        # Add declarations for demand functions.
        funcs = []
        for query in self.queries_with_usets:
            func = make_demand_func(query)
            funcs.append(func)
        
        node = node._replace(decls=tuple(funcs) + node.decls)
        return node
    
    def rewrite_with_demand(self, query_sym, node):
        """Given a query symbol and its associated Comp or Aggr node,
        return the demand-transformed version of that node (not
        transforming any subqueries).
        """
        symtab = self.symtab
        demand_params = query_sym.demand_params
        
        # If there are no demand parameters or we're not transforming
        # this query, no rewriting is needed.
        if len(demand_params) == 0 or query_sym.impl is S.Normal:
            return node
        
        # Make a demand set or demand query.
        left_clauses = self.get_left_clauses()
        if left_clauses is None:
            dem_sym = make_demand_set(symtab, query_sym)
            dem_node = L.Name(dem_sym.name)
            dem_clause = L.RelMember(demand_params, dem_sym.name)
            self.queries_with_usets.add(query_sym.name)
        else:
            dem_sym = make_demand_query(symtab, query_sym, left_clauses)
            dem_node = dem_sym.make_node()
            dem_clause = L.VarsMember(demand_params, dem_node)
            self.demand_queries.add(dem_sym.name)
        
        # Determine the rewritten node.
        if isinstance(node, L.Comp):
            node = node._replace(clauses=(dem_clause,) + node.clauses)
        elif isinstance(node, L.Aggr):
            node = L.AggrRestr(node.op, node.value, demand_params, dem_node)
        else:
            raise AssertionError('No rule for handling demand for {} node'
                                 .format(query.node.__class__.__name__))
        
        return node
    
    def visit_Query(self, node):
        # If this is a demand query that we added, it does not need
        # transformation.
        if node.name in self.demand_queries:
            return node
        
        # If we've seen it before, reuse previous result.
        if node.name in self.rewrite_cache:
            return self.rewrite_cache[node.name]
        
        query_sym = self.symtab.get_queries()[node.name]
        
        # Rewrite to use demand.
        inner_node = self.rewrite_with_demand(query_sym, query_sym.node)
        node = node._replace(query=inner_node)
        
        # Recurse to handle subqueries.
        node = super().visit_Query(node)
        
        # Update symbol.
        query_sym.node = node.query
        
        # Wrap with a call to the demand function.
        node = self.add_demand_function_call(query_sym, node)
        
        # Update cache.
        self.rewrite_cache[query_sym.name] = node
        
        return node


def analyze_parameters(tree, symtab):
    """Analyze parameter information for all queries and assign the
    information to the symbol attributes.
    """
    ParamAnalyzer.run(tree, symtab)


def transform_demand(tree, symtab):
    """Transform queries to incorporate demand."""
    return DemandTransformer.run(tree, symtab)
