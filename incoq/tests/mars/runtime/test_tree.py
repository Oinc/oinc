"""Unit tests for tree.py."""


import unittest
import pickle

from incoq.mars.runtime.tree import *


class TreeCase(unittest.TestCase):
    
    def test_tree(self):
        t = Tree()
        t[1] = None
        t[2] = None
        t[3] = None
        self.assertEqual(t.__min__(), 1)
        self.assertEqual(t.__max__(), 3)
        
        t = Tree()
        self.assertIsNone(t.__min__())
        self.assertIsNone(t.__max__())


if __name__ == '__main__':
    unittest.main()
