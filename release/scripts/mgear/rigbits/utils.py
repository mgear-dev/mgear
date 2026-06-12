"""Rigbits utilitie tools"""

import mgear.pymaya as pm


def createRunTimeCommand(name, rCmd, ann=""):
    """Create run time commands from raw string.

    This function is used to create the mGear hotkeys.
    """
    if pm.runTimeCommand(name, ex=True):
        pm.runTimeCommand(name, e=True, delete=True)
        pm.displayWarning("Old hotkey: " + name + " Deleted")

    pm.runTimeCommand(name, ann=ann, c=rCmd, cat="mGear")
    pm.displayInfo("Hotkey: " + name + " created")


def createHotkeys(*args):
    """Create  mGear custom hotkey functions ready to be use.

    This command doesn't set the hotkey binding. Only create the functions.

    Args:
        *args: Maya's dummy
    """
    # smart export
    rCmd = '''
from mgear.core import skin
from mgear.shifter import io
from mgear.shifter import guide_manager
import mgear.pymaya as pm

sel = pm.selected()
if sel:
    sel = sel[0]
    if sel.hasAttr("ismodel") or sel.hasAttr("isGearGuide"):
        pm.displayInfo("Export Guide Template")
        io.export_guide_template(None, None)
    elif sel.hasAttr("isCtl"):
        pm.displayInfo("Extract Controls")
        guide_manager.extract_controls()
    else:
        shapes = sel.getShapes()
        if shapes and shapes[0].type() in ["nurbsCurve", "mesh", "nurbsSurface"] and skin.getSkinCluster(sel):
            pm.displayInfo("Export Json Skin Pack")
            skin.exportJsonSkinPack()
        else:
            pm.displayInfo("Export Selected")
            multipleFilters = "Maya ASCII (*.ma);;Maya Binary (*.mb);;FBX (*.fbx);;All Files (*.*)"
            filePath = pm.fileDialog2(fileFilter=multipleFilters)
            if filePath:
                if isinstance(filePath, list):
                    filePath = filePath[0]
                pm.exportSelected(filePath)

'''
    createRunTimeCommand("mGear_smartExport", rCmd, ann="")

    # duplicate sym
    rCmd = '''
import mgear.pymaya as pm
from mgear.shifter import guide_manager
import mgear.rigbits as rigbits
if isinstance(pm.selected()[0], pm.MeshFace):
    pm.polyExtrudeFacet(constructionHistory=True,keepFacesTogether=True )
else:
    root = pm.selected()[0]
    if not pm.attributeQuery("comp_type", node=root, ex=True):
        rigbits.duplicateSym()
    else:
        guide_manager.duplicate(True)

'''
    createRunTimeCommand("mGear_duplicateSym", rCmd, ann="")

    # duplicate
    rCmd = '''
import mgear.pymaya as pm
from mgear.shifter import guide_manager
import mgear.rigbits as rigbits
if isinstance(pm.selected()[0], pm.MeshFace):
    pm.polyExtrudeFacet(constructionHistory=True,keepFacesTogether=True )
else:
    root = pm.selected()[0]
    if not pm.attributeQuery("comp_type", node=root, ex=True):
        pm.duplicate()
    else:
        guide_manager.duplicate(False)

'''
    createRunTimeCommand("mGear_duplicate", rCmd, ann="")

    # frame in center
    rCmd = '''
import mgear.pymaya as pm
import maya.mel as mel

def frameSelectedCenter():
    oSel = pm.selected()[0]

    oTra = pm.spaceLocator()
    oTra.setTransformation(oSel.getMatrix(worldSpace=True))
    mel.eval("fitPanel -selected;")
    pm.delete(oTra)
    pm.select(oSel, r=True)

frameSelectedCenter()

'''
    createRunTimeCommand("mGear_frameCenter", rCmd, ann="")

    # reset SRT
    rCmd = '''
from mgear.core import attribute
attribute.smart_reset()

'''
    createRunTimeCommand("mGear_resetSRT", rCmd, ann="")

    # maximize Maya window
    rCmd = '''
import core.cmds as cmds
import maya.mel as mel
gMainWindow = mel.eval('$temp1=$gMainWindow')
acti = cmds.window( gMainWindow, q=True, titleBar=True)
if acti:
    cmds.window( gMainWindow, e=True, titleBar=False)
else:
    cmds.window( gMainWindow, e=True, titleBar=True)

'''
    createRunTimeCommand("mGear_maximizeMaya", rCmd, ann="")

    # toggle visibility Softimage style
    rCmd = '''
import mgear.pymaya as pm
for obj in pm.selected():
    if pm.selected()[0].nodeType() == "transform":

        if pm.getAttr(obj + ".visibility"):
            pm.setAttr(obj + ".visibility", False)
        else:
            pm.setAttr(obj + ".visibility", True)

'''
    createRunTimeCommand("mGear_toggleVisibility", rCmd, ann="")

    # toggle wireframe on top
    rCmd = '''
import mgear.pymaya as pm
import maya.mel as mel

panel = pm.getPanel(wf=True)

shaded = pm.modelEditor(panel, q=True, wos=True)
if shaded:
    pm.modelEditor(panel, e=True, wos=False)
else:
    pm.modelEditor(panel, e=True, wos=True)

'''
    createRunTimeCommand("mGear_toggleWireframeOnTop", rCmd, ann="")

    # toggle shaded wireframe
    rCmd = '''
import mgear.pymaya as pm
import maya.mel as mel

panel = pm.getPanel(wf=True)

shaded = pm.modelEditor(panel, q=True, da=True)
if shaded == "smoothShaded":
    pm.modelEditor(panel, e=True, da='wireframe')
else:
    pm.modelEditor(panel, e=True, da='smoothShaded')

'''
    createRunTimeCommand("mGear_toggleShadedWireframe", rCmd, ann="")

    # align 2 transforms
    rCmd = '''
import mgear.pymaya as pm

if len(pm.selected()) !=2:
    print("2 objects must be selected")
else:
    source, target = pm.selected()

    sWM = source.getMatrix(worldSpace=True)
    target.setMatrix(sWM, worldSpace=True)

'''
    createRunTimeCommand("mGear_align2Transforms", rCmd, ann="")

    #  inspect property
    rCmd = '''
from mgear.shifter import guide_manager
guide_manager.inspect_settings()

'''
    createRunTimeCommand("mGear_inspectProperty", rCmd, ann="")

    rCmd = '''
from mgear.shifter import guide_manager
guide_manager.inspect_settings(1)

'''
    createRunTimeCommand("mGear_inspectPropertyTab2", rCmd, ann="")

    #  build from selection
    rCmd = '''
from mgear.shifter import guide_manager
guide_manager.build_from_selection()

'''
    createRunTimeCommand("mGear_buildFromSelection", rCmd, ann="")

    # walk transform child
    rCmd = '''
import mgear.pymaya as pm
import mgear.core.pickWalk as pw

pw.walkDown(pm.selected())



'''
    createRunTimeCommand("mGear_walkTransformChild", rCmd, ann="")

    # walk transform Parent
    rCmd = '''
import mgear.pymaya as pm
import mgear.core.pickWalk as pw

pw.walkUp(pm.selected())

'''

    createRunTimeCommand("mGear_walkTransformParent", rCmd, ann="")

    # walk transform Left
    rCmd = '''
import mgear.pymaya as pm
import mgear.core.pickWalk as pw

pw.walkLeft(pm.selected())

'''
    createRunTimeCommand("mGear_walkTransformLeft", rCmd, ann="")

    # walk transform Right
    rCmd = '''
import mgear.pymaya as pm
import mgear.core.pickWalk as pw

pw.walkRight(pm.selected())

'''
    createRunTimeCommand("mGear_walkTransformRight", rCmd, ann="")

    # walk mirror
    rCmd = '''
import mgear.pymaya as pm
import mgear.core.pickWalk as pw

pw.walkMirror(pm.selected())

'''
    createRunTimeCommand("mGear_walkMirror", rCmd, ann="")

    # reset camera persp
    rCmd = '''
import mgear.pymaya as pm

pm.viewSet(p=True, fit=True)

'''
    createRunTimeCommand("mGear_resetCameraPersp", rCmd, ann="")

    pm.displayInfo("mGear Hotkeys creation finish.")

    # walk transform child add
    rCmd = '''
import mgear.pymaya as pm
import mgear.core.pickWalk as pw

pw.walkDown(pm.selected(), True)



'''
    createRunTimeCommand("mGear_walkTransformChildAdd", rCmd, ann="")

    # walk transform Parent
    rCmd = '''
import mgear.pymaya as pm
import mgear.core.pickWalk as pw

pw.walkUp(pm.selected(), True)

'''

    createRunTimeCommand("mGear_walkTransformParentAdd", rCmd, ann="")

    # walk transform Left
    rCmd = '''
import mgear.pymaya as pm
import mgear.core.pickWalk as pw

pw.walkLeft(pm.selected(), True)

'''
    createRunTimeCommand("mGear_walkTransformLeftAdd", rCmd, ann="")

    # walk transform Right
    rCmd = '''
import mgear.pymaya as pm
import mgear.core.pickWalk as pw

pw.walkRight(pm.selected(), True)

'''
    createRunTimeCommand("mGear_walkTransformRightAdd", rCmd, ann="")

    # walk mirror
    rCmd = '''
import mgear.pymaya as pm
import mgear.core.pickWalk as pw

pw.walkMirror(pm.selected(), True)

'''
    createRunTimeCommand("mGear_walkMirrorAdd", rCmd, ann="")


# OPEN FBX Exporter
    rCmd = '''
from mgear.shifter.game_tools_fbx import fbx_exporter
fbx_exporter.openFBXExporter()

'''
    createRunTimeCommand("mGear_fbxExporter", rCmd, ann="")
