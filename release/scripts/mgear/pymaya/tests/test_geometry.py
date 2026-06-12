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
import pymaya.geometry


class TestNode(unittest.TestCase):
    def setUp(self):
        cmds.file(new=True, f=True)

    def test_init(self):
        cmds.polySphere()
        self.assertIsNotNone(pymaya.geometry.BindGeometry("pSphere1.vtx[0]"))
        self.assertIsNotNone(pymaya.geometry.BindGeometry("pSphereShape1.vtx[0]"))
        self.assertIsNotNone(pymaya.geometry.BindGeometry("pSphereShape1.vtx[0:10]"))
        self.assertIsNotNone(pymaya.geometry.BindGeometry("pSphere1.f[1]"))
        self.assertIsNotNone(pymaya.geometry.BindGeometry("pSphereShape1.f[0:10]"))
        self.assertIsNone(pymaya.geometry.BindGeometry("pSphere1"))
        self.assertIsNone(pymaya.geometry.BindGeometry("pSphereShape1"))

        self.assertTrue(isinstance(pm.PyNode("pSphereShape1.vtx[0]"), pm.MeshVertex))
        self.assertTrue(isinstance(pm.PyNode("pSphereShape1.f[0]"), pm.MeshFace))
        self.assertTrue(isinstance(pm.PyNode("pSphere1.f"), pm.MeshFace))
        self.assertTrue(isinstance(pm.PyNode("pSphere1").f, pm.MeshFace))
