"""Unit tests for filter.py."""


import unittest

from incoq.mars.incast import L
from incoq.mars.comp import CoreClauseVisitor
from incoq.mars.obj import ObjClauseVisitor
from incoq.mars.demand.filter import *


class ClauseVisitor(CoreClauseVisitor, ObjClauseVisitor):
    pass


class FilterCase(unittest.TestCase):
    
    def test_make_structs(self):
        generator = StructureGenerator(
            ClauseVisitor(),
            L.Parser.pe('''
            {(o_f,) for (s, t) in REL(U) for (s, o) in M()
                    for (t, o) in M () for (o, o_f) in F(f)}
            '''), 'Q')
        
        generator.make_structs()
        exp_structs = [
            Tag(0, 'Q_T_s_1', 's', L.RelMember(['s', 't'], 'U')),
            Tag(0, 'Q_T_t_1', 't', L.RelMember(['s', 't'], 'U')),
            Filter(1, 'Q_d_M_1', L.MMember('s', 'o'), ['Q_T_s_1']),
            Tag(1, 'Q_T_o_1', 'o', L.RelMember(['s', 'o'], 'Q_d_M_1')),
            Filter(2, 'Q_d_M_2', L.MMember('t', 'o'), ['Q_T_t_1']),
            Tag(2, 'Q_T_o_2', 'o', L.RelMember(['t', 'o'], 'Q_d_M_2')),
            Filter(3, 'Q_d_F_f_1', L.FMember('o', 'o_f', 'f'),
                   ['Q_T_o_1', 'Q_T_o_2']),
            Tag(3, 'Q_T_o_f_1', 'o_f',
                L.RelMember(['o', 'o_f'], 'Q_d_F_f_1')),
        ]
        self.assertEqual(generator.structs, exp_structs)
    
    def test_simplify_names(self):
        generator = StructureGenerator(
            ClauseVisitor(),
            L.Parser.pe('''
            {(o_f,) for (s, t) in REL(U) for (s, o) in M()
                    for (t, o) in M () for (o, o_f) in F(f)}
            '''), 'Q')
        generator.make_structs()
        
        generator.simplify_names()
        exp_structs = [
            Tag(0, 'Q_T_s', 's', L.RelMember(['s', 't'], 'U')),
            Tag(0, 'Q_T_t', 't', L.RelMember(['s', 't'], 'U')),
            Filter(1, 'Q_d_M_1', L.MMember('s', 'o'), ['Q_T_s']),
            Tag(1, 'Q_T_o_1', 'o', L.RelMember(['s', 'o'], 'Q_d_M_1')),
            Filter(2, 'Q_d_M_2', L.MMember('t', 'o'), ['Q_T_t']),
            Tag(2, 'Q_T_o_2', 'o', L.RelMember(['t', 'o'], 'Q_d_M_2')),
            Filter(3, 'Q_d_F_f', L.FMember('o', 'o_f', 'f'),
                   ['Q_T_o_1', 'Q_T_o_2']),
            Tag(3, 'Q_T_o_f', 'o_f', L.RelMember(['o', 'o_f'], 'Q_d_F_f')),
        ]
        self.assertEqual(generator.structs, exp_structs)
    
    def test_make_comp(self):
        generator = StructureGenerator(
            ClauseVisitor(),
            L.Parser.pe('''
            {(o_f,) for (s, t) in REL(U) for (s, x) in M()}
            '''), 'Q')
        generator.make_structs()
        generator.simplify_names()
        
        filter = Filter(1, 'Q_d_M', L.MMember('s', 'x'), ['Q_T_s'])
        comp = generator.make_comp(filter)
        exp_comp = L.Parser.pe('''
            {(s, x) for (s,) in REL(R_Q_T_s) for (s, x) in M()}
            ''')
        self.assertEqual(comp, exp_comp)
        
        tag = Tag(0, 'Q_T_s', 's', L.RelMember(['s', 't'], 'U'))
        comp = generator.make_comp(tag)
        exp_comp = L.Parser.pe('''
            {(s,) for (s, t) in REL(U)}
            ''')
        self.assertEqual(comp, exp_comp)
        
        tag = Tag(1, 'Q_T_x', 'x', L.RelMember(['s', 'x'], 'Q_d_M'))
        comp = generator.make_comp(tag)
        exp_comp = L.Parser.pe('''
            {(x,) for (s, x) in REL(Q_d_M)}
            ''')
        self.assertEqual(comp, exp_comp)
    
    def test_make_filter_list(self):
        generator = StructureGenerator(
            ClauseVisitor(),
            L.Parser.pe('''
            {(o_f,) for (s, t) in REL(U) for (s, x) in M()}
            '''), 'Q')
        generator.make_structs()
        generator.simplify_names()
        
        filters = generator.make_filter_list()
        exp_filters = [
            L.RelMember(['s', 't'], 'U'),
            L.RelMember(['s', 'x'], 'Q_d_M'),
        ]
        self.assertEqual(filters, exp_filters)


if __name__ == '__main__':
    unittest.main()