"""Pre- and post-processings applied at the IncAST level."""


__all__ = [
    'VarsFinder',
    
    # Preprocessings are paired with their postprocessings,
    # and listed in order of their application, outermost-first.
    
    'SetMapImporter',
    'SetMapExporter',
    
    'AttributeDisallower',
    'GeneralCallDisallower',
    
    # Main exports.
    'incast_preprocess',
    'incast_postprocess',
]


from incoq.util.collections import OrderedSet
from incoq.mars.incast import L


class VarsFinder(L.NodeVisitor):
    
    """Return normal variables (e.g., not relations or maps) that are
    defined by the program.
    """  
    
    def process(self, tree):
        self.names = OrderedSet()
        super().process(tree)
        return self.names
    
    def visit_For(self, node):
        self.generic_visit(node)
        self.names.add(node.target)
    
    def visit_Assign(self, node):
        self.generic_visit(node)
        self.names.add(node.target)
    
    def visit_DecompAssign(self, node):
        self.generic_visit(node)
        self.names.update(node.vars)
    
    def visit_Name(self, node):
        self.names.add(node.id)
    
    def visit_Member(self, node):
        self.generic_visit(node)
        self.names.update(node.vars)


class SetMapImporter(L.NodeTransformer):
    
    """Rewrite nodes for sets and dicts as nodes for relations and maps,
    where possible.
    """
    
    def __init__(self, rels, maps):
        super().__init__()
        self.rels = rels
        self.maps = maps
    
    def visit_SetUpdate(self, node):
        if (isinstance(node.target, L.Name) and
            node.target.id in self.rels):
            return L.RelUpdate(node.target.id, node.op, node.value)
        return node
    
    def visit_DictAssign(self, node):
        if (isinstance(node.target, L.Name) and
            node.target.id in self.maps):
            return L.MapAssign(node.target.id, node.key, node.value)
        return node
    
    def visit_DictDelete(self, node):
        if (isinstance(node.target, L.Name) and
            node.target.id in self.maps):
            return L.MapDelete(node.target.id, node.key)
        return node
    
    def visit_DictLookup(self, node):
        if (isinstance(node.value, L.Name) and
            node.value.id in self.maps):
            return L.MapLookup(node.value.id, node.key, node.default)
        return node


class SetMapExporter(L.NodeTransformer):
    
    """Rewrite nodes for relations and maps as nodes for sets and dicts."""
    
    def visit_RelUpdate(self, node):
        return L.SetUpdate(L.Name(node.rel), node.op, node.value)
    
    def visit_MapAssign(self, node):
        return L.DictAssign(L.Name(node.map), node.key, node.value)
    
    def visit_MapDelete(self, node):
        return L.DictDelete(L.Name(node.map), node.key)
    
    def visit_MapLookup(self, node):
        return L.DictLookup(L.Name(node.map), node.key, node.default)


class AttributeDisallower(L.NodeVisitor):
    
    """Fail if there are any Attribute nodes in the tree."""
    
    def visit_Attribute(self, node):
        raise TypeError('IncAST does not allow attributes')


class GeneralCallDisallower(L.NodeVisitor):
    
    """Fail if there are any GeneralCall nodes in the tree."""
    
    def visit_GeneralCall(self, node):
        raise TypeError('IncAST function calls must be directly '
                        'by function name')


def incast_preprocess(tree, symtab):
    rels = list(symtab.get_relations().keys())
    maps = list(symtab.get_maps().keys())
    # Recognize relation updates.
    tree = SetMapImporter.run(tree, rels, maps)
    # Check to make sure certain general-case IncAST nodes
    # aren't used.
    AttributeDisallower.run(tree)
    GeneralCallDisallower.run(tree)
    # Make symbols for non-relation, non-map variables.
    names = VarsFinder.run(tree)
    names.difference_update(rels, maps)
    for name in names:
        symtab.define_var(name)
    return tree


def incast_postprocess(tree):
    # Turn relation updates back into set updates.
    tree = SetMapExporter.run(tree)
    return tree