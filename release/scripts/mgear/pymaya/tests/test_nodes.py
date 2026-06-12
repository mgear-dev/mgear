import unittest
import sys
import os
from maya import standalone
standalone.initialize()

from maya import cmds

mpath = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if mpath not in sys.path:
    sys.path.append(mpath)

import pymaya as pm


class TestNode(unittest.TestCase):
    def setUp(self):
        cmds.file(new=True, f=True)

    def test_init(self):
        node_name = cmds.createNode("transform", n="test")
        node = pm.PyNode(node_name)
        self.assertIsNotNone(node)
        with self.assertRaises(pm.MayaNodeError):
            pm.PyNode("no_such_node")

        self.assertEqual(node_name, node.name())

    def test_holding_object(self):
        node_name = cmds.createNode("transform", n="test")
        node = pm.PyNode(node_name)
        new_name = cmds.rename(node_name, "test2")
        self.assertEqual(new_name, node.name())

    def test_partial_name(self):
        child_name = cmds.createNode("transform", n="child")
        parent_name = cmds.createNode("transform", n="parent")
        child = pm.PyNode(child_name)
        parent = pm.PyNode(parent_name)

        self.assertEqual(child_name, child.name())
        self.assertEqual(parent_name, parent.name())

        cmds.parent(child_name, parent_name)
        self.assertEqual(child_name, child.name())
        self.assertEqual(parent_name, parent.name())

        cmds.duplicate(parent_name)
        self.assertNotEqual(child_name, child.name())
        self.assertEqual(f"{parent_name}|{child_name}", child.name())

    def test_dag_or_dg(self):
        sphere_dag_name, sphere_name = cmds.polySphere()
        sphere_dag = pm.PyNode(sphere_dag_name)
        sphere = pm.PyNode(sphere_name)

        self.assertTrue(sphere_dag.isDag())
        self.assertFalse(sphere.isDag())
        self.assertIsNotNone(sphere_dag.dgFn())
        self.assertIsNotNone(sphere.dgFn())
        self.assertIsNotNone(sphere_dag.dagFn())
        self.assertIsNone(sphere.dagFn())

    def test_eq(self):
        child_name = cmds.createNode("transform", n="child")
        parent_name = cmds.createNode("transform", n="parent")
        child = pm.PyNode(child_name)
        parent = pm.PyNode(parent_name)
        cmds.parent(child_name, parent_name)

        a = pm.PyNode(child_name)
        b = pm.PyNode(f"|{parent_name}|{child_name}")

        self.assertEqual(child, a)
        self.assertEqual(child, b)
        self.assertNotEqual(child, parent)
        self.assertTrue(b in [child, parent])

    def test_attr(self):
        child_name = cmds.createNode("transform", n="test")
        node = pm.PyNode("test")
        self.assertIsNotNone(node.attr("v"))
        self.assertIsNotNone(node.v)
        with self.assertRaises(pm.MayaAttributeError):
            node.attr("testtest")
