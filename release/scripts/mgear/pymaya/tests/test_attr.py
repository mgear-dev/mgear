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


class TestAttr(unittest.TestCase):
    def setUp(self):
        cmds.file(new=True, f=True)

    def test_init(self):
        test_node_name = cmds.createNode("transform", n="test")
        v = pm.PyNode(f"{test_node_name}.v")
        self.assertIsNotNone(v)
        self.assertEqual(v.name(), "test.visibility")

        plug = v.plug()
        self.assertIsNotNone(plug)
        self.assertEqual(plug.partialName(False, False, False, False, False, True), "visibility")
        self.assertEqual(plug.partialName(False, False, False, False, False, False), "v")

    def test_connect(self):
        test1_node_name = cmds.createNode("transform", n="test1")
        test2_node_name = cmds.createNode("transform", n="test2")
        t1 = pm.PyNode(f"{test1_node_name}.tx")
        t2 = pm.PyNode(f"{test2_node_name}.tx")
        self.assertIsNone(cmds.listConnections(f"{test1_node_name}.tx"))
        t1.connect(t2)
        self.assertIsNotNone(cmds.listConnections(f"{test1_node_name}.tx"))
        t1.disconnect(t2)
        self.assertIsNone(cmds.listConnections(f"{test1_node_name}.tx"))
        t1 >> t2
        self.assertIsNotNone(cmds.listConnections(f"{test1_node_name}.tx"))
        t1 // t2
        self.assertIsNone(cmds.listConnections(f"{test1_node_name}.tx"))

    def test_delete(self):
        test1_node_name = cmds.createNode("transform", n="test1")
        cmds.addAttr(test1_node_name, ln="test_attr_x", at="float")
        self.assertTrue(cmds.objExists(f"{test1_node_name}.test_attr_x"))
        tattr = pm.PyNode(f"{test1_node_name}.test_attr_x")
        tattr.delete()
        self.assertFalse(cmds.objExists(f"{test1_node_name}.test_attr_x"))

    def test_partial_name(self):
        child_name = cmds.createNode("transform", n="child")
        parent_name = cmds.createNode("transform", n="parent")
        child = pm.PyNode(child_name)
        cmds.parent(child_name, parent_name)
        self.assertEqual(child.v.name(), f"{child_name}.visibility")
        cmds.duplicate(parent_name)
        self.assertNotEqual(child.v.name(), f"{child_name}.visibility")
        self.assertEqual(child.v.name(), f"{parent_name}|{child_name}.visibility")

    def test_array_compound(self):
        sp = cmds.polySphere()[0]
        sps = cmds.listRelatives(sp, s=True)[0]
        vrts = pm.PyNode(f"{sps}.vrts")
        self.assertEqual(vrts[0].name(), f"{sps}.vrts[0]")
        self.assertIsNotNone(vrts[0].vrtx)
        self.assertIsNotNone(vrts[0].vrty)
        self.assertIsNotNone(vrts[0].vrtz)
        self.assertIsNotNone(vrts[0].attr("vrtz"))
        self.assertEqual(vrts[0].vrtz.name(), f"{sps}.vrts[0].vrtz")
        self.assertIsNotNone(pm.PyNode(f"{sps}.vrts[0].vrtz"))

        circ = cmds.circle(d=1, s=5, ch=False)[0]
        circs = cmds.listRelatives(circ, s=True)[0]
        self.assertIsNotNone(pm.PyNode(circ).controlPoints[1])
        self.assertIsNotNone(pm.PyNode(circ).getShape().controlPoints[1])
        self.assertIsNotNone(pm.PyNode(f"{circs}.controlPoints[1]"))

        crv = cmds.curve(p=[[0, 0, 0], [1, 1, 1]], d=1)
        crvs = cmds.listRelatives(crv, s=True)[0]
        self.assertIsNotNone(pm.PyNode(crv).selectHandle)
        self.assertIsNotNone(pm.PyNode(f"{crv}.selectHandle"))
