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


class TestCmd(unittest.TestCase):
    def setUp(self):
        cmds.file(new=True, f=True)

    def test_undochunk(self):
        sc = pm.undoInfo(q=1)
        pm.createNode("transform")
        pm.createNode("transform")
        pm.createNode("transform")
        pm.createNode("transform")
        pm.createNode("transform")
        self.assertEqual(pm.undoInfo(q=1) - sc, 5)

        sc = pm.undoInfo(q=1)
        with pm.UndoChunk():
            pm.createNode("transform")
            pm.createNode("transform")
            pm.createNode("transform")
            pm.createNode("transform")
            pm.createNode("transform")
        self.assertEqual(pm.undoInfo(q=1) - sc, 1)
