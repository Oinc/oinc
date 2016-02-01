"""Unit tests for trans.py."""


import unittest

from incoq.mars.incast import L
from incoq.mars.type import T
from incoq.mars.symbol import S, N
from incoq.mars.aggr.trans import *
from incoq.mars.aggr.trans import make_aggr_maint_func, aggrinv_from_query


class TransCase(unittest.TestCase):
    
    def test_aggr_maint_func_add(self):
        aggrinv = AggrInvariant('A', L.Count(), 'R', L.mask('bu'), ['x'])
        func = make_aggr_maint_func(N.fresh_name_generator(),
                                    aggrinv, L.SetAdd())
        exp_func = L.Parser.ps('''
            def _maint_A_for_R_add(_elem):
                (_elem_v1, _elem_v2) = _elem
                _v1_key = (_elem_v1,)
                _v1_value = (_elem_v2,)
                _v1_state = A.get(_v1_key, 0)
                _v1_state = (_v1_state + 1)
                if (_v1_key in A):
                    A.mapdelete(_v1_key)
                A.mapassign(_v1_key, _v1_state)
            ''')
        self.assertEqual(func, exp_func)
    
    def test_aggr_maint_func_remove(self):
        aggrinv = AggrInvariant('A', L.Count(), 'R', L.mask('bu'), ['x'])
        func = make_aggr_maint_func(N.fresh_name_generator(),
                                    aggrinv, L.SetRemove())
        exp_func = L.Parser.ps('''
            def _maint_A_for_R_remove(_elem):
                (_elem_v1, _elem_v2) = _elem
                _v1_key = (_elem_v1,)
                _v1_value = (_elem_v2,)
                _v1_state = A[_v1_key]
                _v1_state = (_v1_state - 1)
                A.mapdelete(_v1_key)
                if (not (_v1_state == 0)):
                    A.mapassign(_v1_key, _v1_state)
            ''')
        self.assertEqual(func, exp_func)
    
    def test_aggrmaintainer(self):
        aggrinv = AggrInvariant('A', L.Count(), 'R',
                                L.mask('u'), ())
        tree = L.Parser.p('''
            def main():
                R.reladd(x)
                R.relremove(x)
            ''')
        tree = AggrMaintainer.run(tree, N.fresh_name_generator(), aggrinv)
        self.assertEqual(tree.decls[0].name, '_maint_A_for_R_add')
        self.assertEqual(tree.decls[1].name, '_maint_A_for_R_remove')
        main = tree.decls[2]
        exp_main = L.Parser.ps('''
            def main():
                R.reladd(x)
                _maint_A_for_R_add(x)
                _maint_A_for_R_remove(x)
                R.relremove(x)
            ''')
        self.assertEqual(main, exp_main)
    
    def test_aggrinv_from_query(self):
        # Relation operand.
        symtab = S.SymbolTable()
        aggr = L.Parser.pe('count(R)')
        symtab.define_relation('R', type=T.Set(T.Tuple([T.Number, T.Number])))
        query = symtab.define_query('Q', node=aggr)
        aggrinv = aggrinv_from_query(symtab, query, 'A')
        exp_aggrinv = AggrInvariant('A', L.Count(), 'R',
                                    L.mask('uu'), ())
        self.assertEqual(aggrinv, exp_aggrinv)
        
        # ImgLookup operand.
        symtab = S.SymbolTable()
        aggr = L.Parser.pe("count(R.imglookup('bu', (x,)))")
        symtab.define_relation('R', type=T.Set(T.Tuple([T.Number, T.Number])))
        query = symtab.define_query('Q', node=aggr)
        aggrinv = aggrinv_from_query(symtab, query, 'A')
        exp_aggrinv = AggrInvariant('A', L.Count(), 'R',
                                    L.mask('bu'), ('x',))
        self.assertEqual(aggrinv, exp_aggrinv)
    
    def test_incrementalize_aggr(self):
        symtab = S.SymbolTable()
        aggr = L.Parser.pe("count(R.imglookup('bu', (x,)))")
        symtab.define_relation('R', type=T.Set(T.Tuple([T.Number, T.Number])))
        query = symtab.define_query('Q', node=aggr)
        tree = L.Parser.p('''
            def main():
                R.add(x)
                print(QUERY('Q', count(R.imglookup('bu', (x,)))))
            ''')
        
        tree = incrementalize_aggr(tree, symtab, query, 'A')
        main = tree.decls[2]
        exp_main = L.Parser.ps('''
            def main():
                R.add(x)
                print(A.get((x,), 0))
            ''')
        self.assertEqual(main, exp_main)
        
        sym = symtab.get_maps()['A']
        self.assertEqual(sym.type, T.Map(T.Tuple([T.Number]), T.Number))


if __name__ == '__main__':
    unittest.main()
