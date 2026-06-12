import unittest
import sys
import os

from maya import standalone
standalone.initialize()
from maya import cmds

mpath = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if mpath not in sys.path:
    sys.path.append(mpath)

import math
import pymaya as pm
import pymaya.attr


class TestCmd(unittest.TestCase):
    def setUp(self):
        cmds.file(new=True, f=True)

    def test_return_pyobject(self):
        n = pm.createNode("transform", n="test1")
        self.assertIsNotNone(n)
        self.assertTrue(isinstance(n, pm.nt.Transform))
        self.assertTrue(isinstance(pm.listAttr("test1")[0], pymaya.attr.Attribute))

    def test_pyobject_arg(self):
        n = pm.createNode("transform", n="test1")
        self.assertEqual(n.name(), "test1")
        pm.rename(n, "test2")
        self.assertEqual(n.name(), "test2")
        n2 = pm.createNode("transform", n="test1")
        pm.parent(n, n2)
        self.assertEqual(n.dagPath().fullPathName(), "|test1|test2")
        self.assertEqual(pm.getAttr(n.tx), 0)
        pm.setAttr(n.tx, 10)
        self.assertEqual(pm.getAttr(n.tx), 10)

        pm.addAttr(n, ln="testtest", dt="string")
        pm.setAttr(n.testtest, "aaa", type="string")
        self.assertEqual(pm.getAttr(n.testtest), "aaa")

    def test_original_commands(self):
        pm.displayInfo("TEST DISPLAY")
        pm.displayWarning("TEST WARNING")
        pm.displayError("TEST ERROR")

        pm.createNode("transform", n="test")
        pm.select("test")
        testma = os.path.join(os.path.dirname(__file__), "exportest.ma")
        pm.exportSelected(testma, f=True, type="mayaAscii")
        self.assertTrue(os.path.isfile(testma))
        os.remove(testma)
        self.assertFalse(os.path.isfile(testma))

        pm.mel.eval("createNode -n \"test2\" \"transform\"")
        self.assertIsNotNone(pm.PyNode("test2"))

        sphere = pm.polySphere()[0]
        self.assertTrue(pm.hasAttr(sphere, "v"))
        self.assertTrue(pm.hasAttr(sphere, "inMesh", checkShape=True))
        self.assertFalse(pm.hasAttr(sphere, "inMesh", checkShape=False))

        pm.select(sphere)
        self.assertEqual(pm.selected(), [sphere])
        pm.select(cl=True)
        self.assertEqual(pm.selected(), [])

        cmds.file(new=True, f=True)
        pm.createNode("transform", n="test")
        pm.select("test")
        testma = os.path.join(os.path.dirname(__file__), "exportest.ma")
        pm.exportSelected(testma, f=True, type="mayaAscii")
        imported = pm.importFile(testma, ns="testfile", rnn=True)
        self.assertEqual([x.name() for x in imported], ["testfile:test"])
        os.remove(testma)

        pm.namespace(add="new_name_space")
        nn = pm.createNode("transform", n="new_name_space:mytransform")
        self.assertNotEqual(pm.NameParser(nn).stripNamespace().__str__(), "new_name_space:mytransform")
        self.assertEqual(pm.NameParser(nn).stripNamespace().__str__(), "mytransform")

        cmds.file(new=True, f=True)
        self.assertEqual(pm.sceneName(), "")
        cmds.file(rename="test")
        self.assertNotEqual(pm.sceneName(), "")

        with self.assertRaises(pm.general.MayaNodeError):
            pm.PyNode("No_Such_Node")

        self.assertEqual(pm.util.degrees(math.pi), 180.0)
