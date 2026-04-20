"""Rigbits eye rigger tool"""

import json
import traceback
from functools import partial
string_types = str
from maya import cmds
import mgear
import mgear.core.pyqt as gqt
import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from mgear.core import meshNavigation, curve, applyop, node, primitive, icon
from mgear.core import transform, utils, attribute, skin, string
from mgear.vendor.Qt import QtCore, QtWidgets
from mgear.pymaya import datatypes

from mgear import rigbits
from . import lib

# TODO: change deformers_group to static_rig_parent
# for the moment we keep this for backwards compativility with
# old configuration files
##########################################################
# Eye rig constructor
##########################################################


def rig(
    eyeMesh=None,
    edgeLoop="",
    blinkH=20,
    namePrefix="eye",
    offset=0.05,
    rigidLoops=2,
    falloffLoops=4,
    headJnt=None,
    doSkin=True,
    parent_node=None,
    ctlName="ctl",
    sideRange=False,
    customCorner=False,
    intCorner=None,
    extCorner=None,
    ctlSet=None,
    defSet=None,
    upperVTrack=0.02,
    upperHTrack=0.01,
    lowerVTrack=0.02,
    lowerHTrack=0.01,
    aim_controller="",
    deformers_group="",
):
    """Create eyelid and eye rig

    Args:
        eyeMesh (TYPE): Description
        edgeLoop (TYPE): Description
        blinkH (TYPE): Description
        namePrefix (TYPE): Description
        offset (TYPE): Description
        rigidLoops (TYPE): Description
        falloffLoops (TYPE): Description
        headJnt (TYPE): Description
        doSkin (TYPE): Description
        parent_node (None, optional): Description
        ctlName (str, optional): Description
        sideRange (bool, optional): Description
        customCorner (bool, optional): Description
        intCorner (None, optional): Description
        extCorner (None, optional): Description
        ctlSet (None, optional): Description
        defSet (None, optional): Description
        upperVTrack (None, optional): Description
        upperHTrack (None, optional): Description
        lowerVTrack (None, optional): Description
        lowerHTrack (None, optional): Description
        aim_controller (None, optional): Description
        deformers_group (None, optional): Description

    Returns:
        TYPE: Description
    """
    # Checkers
    if edgeLoop:
        edgeLoopList = [pm.PyNode(e) for e in edgeLoop.split(",")]
    else:
        pm.displayWarning("Please set the edge loop first")
        return

    if eyeMesh:
        try:
            eyeMesh = pm.PyNode(eyeMesh)
        except RuntimeError:
            pm.displayWarning(
                "The object %s can not be found in the " "scene" % (eyeMesh)
            )
            return
    else:
        pm.displayWarning("Please set the eye mesh first")

    if doSkin:
        if not headJnt:
            pm.displayWarning(
                "Please set the Head Jnt or unCheck "
                "Compute Topological Autoskin"
            )
            return

    # Convert data
    blinkH = blinkH / 100.0

    # Initial Data
    bboxCenter = meshNavigation.bboxCenter(eyeMesh)

    extr_v = meshNavigation.getExtremeVertexFromLoop(edgeLoopList, sideRange)
    upPos = extr_v[0]
    lowPos = extr_v[1]
    inPos = extr_v[2]
    outPos = extr_v[3]
    edgeList = extr_v[4]
    vertexList = extr_v[5]

    # Detect the side L or R from the x value
    if inPos.getPosition(space="world")[0] < 0.0:
        side = "R"
        inPos = extr_v[3]
        outPos = extr_v[2]
        normalPos = outPos
        npw = normalPos.getPosition(space="world")
        normalVec = npw - bboxCenter
    else:
        side = "L"
        normalPos = outPos
        npw = normalPos.getPosition(space="world")
        normalVec = bboxCenter - npw
    # Manual Vertex corners
    if customCorner:
        if intCorner:
            try:
                if side == "R":
                    inPos = pm.PyNode(extCorner)
                else:
                    inPos = pm.PyNode(intCorner)
            except RuntimeError:
                pm.displayWarning("%s can not be found" % intCorner)
                return
        else:
            pm.displayWarning("Please set the internal eyelid corner")
            return

        if extCorner:
            try:
                normalPos = pm.PyNode(extCorner)
                npw = normalPos.getPosition(space="world")
                if side == "R":
                    outPos = pm.PyNode(intCorner)
                    normalVec = npw - bboxCenter
                else:
                    outPos = pm.PyNode(extCorner)
                    normalVec = bboxCenter - npw
            except RuntimeError:
                pm.displayWarning("%s can not be found" % extCorner)
                return
        else:
            pm.displayWarning("Please set the external eyelid corner")
            return

    # Check if we have prefix:
    if namePrefix:
        namePrefix = string.removeInvalidCharacter(namePrefix)
    else:
        pm.displayWarning("Prefix is needed")
        return

    def setName(name, ind=None):
        namesList = [namePrefix, side, name]
        if ind is not None:
            namesList[1] = side + str(ind)
        name = "_".join(namesList)
        return name

    if pm.ls(setName("root")):
        pm.displayWarning(
            "The object %s already exist in the scene. Please "
            "choose another name prefix" % setName("root")
        )
        return

    # Eye root
    eye_root = primitive.addTransform(None, setName("root"))
    eyeCrv_root = primitive.addTransform(eye_root, setName("crvs"))

    # Eyelid Main crvs
    try:
        upEyelid = meshNavigation.edgeRangeInLoopFromMid(
            edgeList, upPos, inPos, outPos
        )
        upCrv = curve.createCurveFromOrderedEdges(
            upEyelid, inPos, setName("upperEyelid"), parent=eyeCrv_root
        )
        upCrv_ctl = curve.createCurveFromOrderedEdges(
            upEyelid, inPos, setName("upCtl_crv"), parent=eyeCrv_root
        )
        pm.rebuildCurve(upCrv_ctl, s=2, rt=0, rpo=True, ch=False)

        lowEyelid = meshNavigation.edgeRangeInLoopFromMid(
            edgeList, lowPos, inPos, outPos
        )
        lowCrv = curve.createCurveFromOrderedEdges(
            lowEyelid, inPos, setName("lowerEyelid"), parent=eyeCrv_root
        )
        lowCrv_ctl = curve.createCurveFromOrderedEdges(
            lowEyelid, inPos, setName("lowCtl_crv"), parent=eyeCrv_root
        )

        pm.rebuildCurve(lowCrv_ctl, s=2, rt=0, rpo=True, ch=False)

    except UnboundLocalError:
        if customCorner:
            pm.displayWarning(
                "This error is maybe caused because the custom "
                "Corner vertex is not part of the edge loop"
            )
        pm.displayError(traceback.format_exc())
        return

    upBlink = curve.createCurveFromCurve(
        upCrv, setName("upblink_crv"), nbPoints=30, parent=eyeCrv_root
    )
    lowBlink = curve.createCurveFromCurve(
        lowCrv, setName("lowBlink_crv"), nbPoints=30, parent=eyeCrv_root
    )

    upTarget = curve.createCurveFromCurve(
        upCrv, setName("upblink_target"), nbPoints=30, parent=eyeCrv_root
    )
    lowTarget = curve.createCurveFromCurve(
        lowCrv, setName("lowBlink_target"), nbPoints=30, parent=eyeCrv_root
    )
    midTarget = curve.createCurveFromCurve(
        lowCrv, setName("midBlink_target"), nbPoints=30, parent=eyeCrv_root
    )
    midTargetLower = curve.createCurveFromCurve(
        lowCrv,
        setName("midBlinkLower_target"),
        nbPoints=30,
        parent=eyeCrv_root,
    )

    rigCrvs = [
        upCrv,
        lowCrv,
        upCrv_ctl,
        lowCrv_ctl,
        upBlink,
        lowBlink,
        upTarget,
        lowTarget,
        midTarget,
        midTargetLower,
    ]

    for crv in rigCrvs:
        crv.attr("visibility").set(False)

    # localBBOX
    localBBox = eyeMesh.getBoundingBox(invisible=True, space="world")
    wRadius = abs((localBBox[0][0] - localBBox[1][0]))
    dRadius = abs((localBBox[0][1] - localBBox[1][1]) / 1.7)

    # Groups
    if not ctlSet:
        ctlSet = "rig_controllers_grp"
    try:
        ctlSet = pm.PyNode(ctlSet)
    except RuntimeError:
        pm.sets(n=ctlSet, em=True)
        ctlSet = pm.PyNode(ctlSet)
    if not defSet:
        defSet = "rig_deformers_grp"
    try:
        defset = pm.PyNode(defSet)
    except RuntimeError:
        pm.sets(n=defSet, em=True)
        defset = pm.PyNode(defSet)

    # Calculate center looking at
    averagePosition = (
        upPos.getPosition(space="world")
        + lowPos.getPosition(space="world")
        + inPos.getPosition(space="world")
        + outPos.getPosition(space="world")
    ) / 4
    if side == "R":
        negate = False
        offset = offset
        over_offset = dRadius
    else:
        negate = False
        over_offset = dRadius

    if side == "R" and sideRange or side == "R" and customCorner:
        axis = "z-x"
        # axis = "zx"
    else:
        axis = "z-x"

    t = transform.getTransformLookingAt(
        bboxCenter, averagePosition, normalVec, axis=axis, negate=negate
    )

    over_npo = primitive.addTransform(
        eye_root, setName("center_lookatRoot"), t
    )

    over_ctl = icon.create(
        over_npo,
        setName("over_%s" % ctlName),
        t,
        icon="square",
        w=wRadius,
        d=dRadius,
        ro=datatypes.Vector(1.57079633, 0, 0),
        po=datatypes.Vector(0, 0, over_offset),
        color=4,
    )
    node.add_controller_tag(over_ctl)
    attribute.addAttribute(over_ctl, "isCtl", "bool", keyable=False)
    attribute.add_mirror_config_channels(over_ctl)
    attribute.setKeyableAttributes(
        over_ctl,
        params=["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"],
    )

    if side == "R":
        over_npo.attr("rx").set(over_npo.attr("rx").get() * -1)
        over_npo.attr("ry").set(over_npo.attr("ry").get() + 180)
        over_npo.attr("sz").set(-1)

    if len(ctlName.split("_")) == 2 and ctlName.split("_")[-1] == "ghost":
        pass
    else:
        pm.sets(ctlSet, add=over_ctl)

    center_lookat = primitive.addTransform(
        over_ctl, setName("center_lookat"), t
    )

    # Tracking
    # Eye aim control
    t_arrow = transform.getTransformLookingAt(
        bboxCenter,
        averagePosition,
        upPos.getPosition(space="world"),
        axis="zy",
        negate=False,
    )

    radius = abs((localBBox[0][0] - localBBox[1][0]) / 1.7)

    arrow_ctl = None
    arrow_npo = None
    if aim_controller:
        arrow_ctl = pm.PyNode(aim_controller)
    else:
        arrow_npo = primitive.addTransform(
            eye_root, setName("aim_npo"), t_arrow
        )
        arrow_ctl = icon.create(
            arrow_npo,
            setName("aim_%s" % ctlName),
            t_arrow,
            icon="arrow",
            w=1,
            po=datatypes.Vector(0, 0, radius),
            color=4,
        )
    if len(ctlName.split("_")) == 2 and ctlName.split("_")[-1] == "ghost":
        pass
    else:
        pm.sets(ctlSet, add=arrow_ctl)
    attribute.setKeyableAttributes(arrow_ctl, params=["rx", "ry", "rz"])
    attribute.addAttribute(arrow_ctl, "isCtl", "bool", keyable=False)

    # tracking custom trigger
    if side == "R":
        tt = t_arrow
    else:
        tt = t
    aimTrigger_root = primitive.addTransform(
        center_lookat, setName("aimTrigger_root"), tt
    )
    # For some unknown reason the right side gets scewed rotation values
    mgear.core.transform.resetTransform(aimTrigger_root)
    aimTrigger_lvl = primitive.addTransform(
        aimTrigger_root, setName("aimTrigger_lvl"), tt
    )
    # For some unknown reason the right side gets scewed rotation values
    mgear.core.transform.resetTransform(aimTrigger_lvl)
    aimTrigger_lvl.attr("tz").set(1.0)
    aimTrigger_ref = primitive.addTransform(
        aimTrigger_lvl, setName("aimTrigger_ref"), tt
    )
    # For some unknown reason the right side gets scewed rotation values
    mgear.core.transform.resetTransform(aimTrigger_ref)
    aimTrigger_ref.attr("tz").set(0.0)
    # connect  trigger with arrow_ctl
    pm.parentConstraint(arrow_ctl, aimTrigger_ref, mo=True)

    # Controls lists
    upControls = []
    trackLvl = []

    # upper eyelid controls
    upperCtlNames = ["inCorner", "upInMid", "upMid", "upOutMid", "outCorner"]
    cvs = upCrv_ctl.getCVs(space="world")
    if side == "R" and not sideRange:
        # if side == "R":
        cvs = [cv for cv in reversed(cvs)]
    for i, cv in enumerate(cvs):
        if utils.is_odd(i):
            color = 14
            wd = 0.5
            icon_shape = "circle"
            params = ["tx", "ty", "tz"]
        else:
            color = 4
            wd = 0.7
            icon_shape = "square"
            params = [
                "tx",
                "ty",
                "tz",
                "ro",
                "rx",
                "ry",
                "rz",
                "sx",
                "sy",
                "sz",
            ]

        t = transform.setMatrixPosition(t, cvs[i])
        npo = primitive.addTransform(
            center_lookat, setName("%s_npo" % upperCtlNames[i]), t
        )
        npoBase = npo
        if i == 2:
            # we add an extra level to input the tracking ofset values
            npo = primitive.addTransform(
                npo, setName("%s_trk" % upperCtlNames[i]), t
            )
            trackLvl.append(npo)

        ctl = icon.create(
            npo,
            setName("%s_%s" % (upperCtlNames[i], ctlName)),
            t,
            icon=icon_shape,
            w=wd,
            d=wd,
            ro=datatypes.Vector(1.57079633, 0, 0),
            po=datatypes.Vector(0, 0, offset),
            color=color,
        )
        attribute.addAttribute(ctl, "isCtl", "bool", keyable=False)
        attribute.add_mirror_config_channels(ctl)
        node.add_controller_tag(ctl, over_ctl)
        upControls.append(ctl)
        if len(ctlName.split("_")) == 2 and ctlName.split("_")[-1] == "ghost":
            pass
        else:
            pm.sets(ctlSet, add=ctl)
        attribute.setKeyableAttributes(ctl, params)
        if side == "R":
            npoBase.attr("ry").set(180)
            npoBase.attr("sz").set(-1)

    # adding parent constraints to odd controls
    for i, ctl in enumerate(upControls):
        if utils.is_odd(i):
            cns_node = pm.parentConstraint(
                upControls[i - 1], upControls[i + 1], ctl.getParent(), mo=True
            )
            # Make the constraint "noFlip"
            cns_node.interpType.set(0)

    # lower eyelid controls
    lowControls = [upControls[0]]
    lowerCtlNames = [
        "inCorner",
        "lowInMid",
        "lowMid",
        "lowOutMid",
        "outCorner",
    ]

    cvs = lowCrv_ctl.getCVs(space="world")
    if side == "R" and not sideRange:
        cvs = [cv for cv in reversed(cvs)]
    for i, cv in enumerate(cvs):
        # we skip the first and last point since is already in the uper eyelid
        if i in [0, 4]:
            continue
        if utils.is_odd(i):
            color = 14
            wd = 0.5
            icon_shape = "circle"
            params = ["tx", "ty", "tz"]
        else:
            color = 4
            wd = 0.7
            icon_shape = "square"
            params = [
                "tx",
                "ty",
                "tz",
                "ro",
                "rx",
                "ry",
                "rz",
                "sx",
                "sy",
                "sz",
            ]

        t = transform.setMatrixPosition(t, cvs[i])
        npo = primitive.addTransform(
            center_lookat, setName("%s_npo" % lowerCtlNames[i]), t
        )
        npoBase = npo
        if i == 2:
            # we add an extra level to input the tracking ofset values
            npo = primitive.addTransform(
                npo, setName("%s_trk" % lowerCtlNames[i]), t
            )
            trackLvl.append(npo)
        ctl = icon.create(
            npo,
            setName("%s_%s" % (lowerCtlNames[i], ctlName)),
            t,
            icon=icon_shape,
            w=wd,
            d=wd,
            ro=datatypes.Vector(1.57079633, 0, 0),
            po=datatypes.Vector(0, 0, offset),
            color=color,
        )
        attribute.addAttribute(ctl, "isCtl", "bool", keyable=False)
        attribute.add_mirror_config_channels(ctl)

        lowControls.append(ctl)
        if len(ctlName.split("_")) == 2 and ctlName.split("_")[-1] == "ghost":
            pass
        else:
            pm.sets(ctlSet, add=ctl)
        attribute.setKeyableAttributes(ctl, params)
        # mirror behaviout on R side controls
        if side == "R":
            npoBase.attr("ry").set(180)
            npoBase.attr("sz").set(-1)
    for lctl in reversed(lowControls[1:]):
        node.add_controller_tag(lctl, over_ctl)
    lowControls.append(upControls[-1])

    # adding parent constraints to odd controls
    for i, ctl in enumerate(lowControls):
        if utils.is_odd(i):
            cns_node = pm.parentConstraint(
                lowControls[i - 1],
                lowControls[i + 1],
                ctl.getParent(),
                mo=True,
            )
            # Make the constraint "noFlip"
            cns_node.interpType.set(0)

    # Connecting control crvs with controls
    applyop.gear_curvecns_op(upCrv_ctl, upControls)
    applyop.gear_curvecns_op(lowCrv_ctl, lowControls)

    # adding wires
    w1 = pm.wire(upCrv, w=upBlink)[0]
    w2 = pm.wire(lowCrv, w=lowBlink)[0]

    w3 = pm.wire(upTarget, w=upCrv_ctl)[0]
    w4 = pm.wire(lowTarget, w=lowCrv_ctl)[0]

    # adding blendshapes
    bs_upBlink = pm.blendShape(
        upTarget, midTarget, upBlink, n="blendShapeUpBlink"
    )
    bs_lowBlink = pm.blendShape(
        lowTarget, midTargetLower, lowBlink, n="blendShapeLowBlink"
    )
    bs_mid = pm.blendShape(
        lowTarget, upTarget, midTarget, n="blendShapeMidBlink"
    )
    bs_midLower = pm.blendShape(
        lowTarget, upTarget, midTargetLower, n="blendShapeMidLowerBlink"
    )

    # setting blendshape reverse connections
    rev_node = cmds.createNode("reverse")

    # Connect attributes using cmds.connectAttr()
    cmds.connectAttr(
        "{}.{}".format(bs_upBlink[0], midTarget.name()),
        "{}.inputX".format(rev_node),
    )
    cmds.connectAttr(
        "{}.outputX".format(rev_node),
        "{}.{}".format(bs_upBlink[0], upTarget.name()),
    )

    # Create reverse nodes
    rev_node = cmds.createNode("reverse")
    rev_nodeLower = cmds.createNode("reverse")

    cmds.connectAttr(
        "{}.{}".format(bs_lowBlink[0], midTargetLower.name()),
        "{}.inputX".format(rev_node),
    )
    cmds.connectAttr(
        "{}.outputX".format(rev_node),
        "{}.{}".format(bs_lowBlink[0], lowTarget.name()),
    )

    # Create another reverse node
    rev_node = cmds.createNode("reverse")

    cmds.connectAttr(
        "{}.{}".format(bs_mid[0], upTarget.name()),
        "{}.inputX".format(rev_node),
    )
    cmds.connectAttr(
        "{}.{}".format(bs_midLower[0], upTarget.name()),
        "{}.inputX".format(rev_nodeLower),
    )

    cmds.connectAttr(
        "{}.outputX".format(rev_node),
        "{}.{}".format(bs_mid[0], lowTarget.name()),
    )
    cmds.connectAttr(
        "{}.outputX".format(rev_nodeLower),
        "{}.{}".format(bs_midLower[0], lowTarget.name()),
    )

    # Setting default values
    cmds.setAttr("{}.{}".format(bs_mid[0], upTarget.name()), blinkH)
    cmds.setAttr("{}.{}".format(bs_midLower[0], upTarget.name()), blinkH)

    # joints root
    jnt_root = primitive.addTransformFromPos(
        eye_root, setName("joints"), pos=bboxCenter
    )
    if deformers_group:
        deformers_group = pm.PyNode(deformers_group)
        pm.parentConstraint(eye_root, jnt_root, mo=True)
        pm.scaleConstraint(eye_root, jnt_root, mo=True)
        deformers_group.addChild(jnt_root)

    # head joint
    if headJnt:
        try:
            headJnt = pm.PyNode(headJnt)
            jnt_base = headJnt
        except RuntimeError:
            pm.displayWarning("Aborted can not find %s " % headJnt)
            return
    else:
        # Eye root
        jnt_base = jnt_root

    eyeTargets_root = primitive.addTransform(eye_root, setName("targets"))

    eyeCenter_jnt = rigbits.addJnt(
        arrow_ctl, jnt_base, grp=defset, jntName=setName("center_jnt")
    )

    # Upper Eyelid joints ##################################################

    cvs = upCrv.getCVs(space="world")
    upCrv_info = node.createCurveInfoNode(upCrv)

    # aim constrain targets and joints
    upperEyelid_aimTargets = []
    upperEyelid_jnt = []
    upperEyelid_jntRoot = []

    for i, cv in enumerate(cvs):

        # aim targets
        trn = primitive.addTransformFromPos(
            eyeTargets_root, setName("upEyelid_aimTarget", i), pos=cv
        )
        upperEyelid_aimTargets.append(trn)
        # connecting positions with crv
        pm.connectAttr(
            upCrv_info + ".controlPoints[%s]" % str(i), trn.attr("translate")
        )

        # joints
        jntRoot = primitive.addJointFromPos(
            jnt_root, setName("upEyelid_jnt_base", i), pos=bboxCenter
        )
        jntRoot.attr("radius").set(0.08)
        jntRoot.attr("visibility").set(False)
        upperEyelid_jntRoot.append(jntRoot)
        applyop.aimCns(jntRoot, trn, axis="zy", wupObject=jnt_root)

        jnt_ref = primitive.addJointFromPos(
            jntRoot, setName("upEyelid_jnt_ref", i), pos=cv
        )
        jnt_ref.attr("radius").set(0.08)
        jnt_ref.attr("visibility").set(False)

        jnt = rigbits.addJnt(
            jnt_ref, jnt_base, grp=defset, jntName=setName("upEyelid_jnt", i)
        )
        upperEyelid_jnt.append(jnt)

    # Lower Eyelid joints ##################################################

    cvs = lowCrv.getCVs(space="world")
    lowCrv_info = node.createCurveInfoNode(lowCrv)

    # aim constrain targets and joints
    lowerEyelid_aimTargets = []
    lowerEyelid_jnt = []
    lowerEyelid_jntRoot = []

    for i, cv in enumerate(cvs):
        if i in [0, len(cvs) - 1]:
            continue

        # aim targets
        trn = primitive.addTransformFromPos(
            eyeTargets_root, setName("lowEyelid_aimTarget", i), pos=cv
        )
        lowerEyelid_aimTargets.append(trn)
        # connecting positions with crv
        pm.connectAttr(
            lowCrv_info + ".controlPoints[%s]" % str(i), trn.attr("translate")
        )

        # joints
        jntRoot = primitive.addJointFromPos(
            jnt_root, setName("lowEyelid_base", i), pos=bboxCenter
        )
        jntRoot.attr("radius").set(0.08)
        jntRoot.attr("visibility").set(False)
        lowerEyelid_jntRoot.append(jntRoot)
        applyop.aimCns(jntRoot, trn, axis="zy", wupObject=jnt_root)

        jnt_ref = primitive.addJointFromPos(
            jntRoot, setName("lowEyelid_jnt_ref", i), pos=cv
        )
        jnt_ref.attr("radius").set(0.08)
        jnt_ref.attr("visibility").set(False)

        jnt = rigbits.addJnt(
            jnt_ref, jnt_base, grp=defset, jntName=setName("lowEyelid_jnt", i)
        )
        lowerEyelid_jnt.append(jnt)

    # Channels
    # Adding and connecting attributes for the blinks
    up_ctl = upControls[2]
    blink_att = attribute.addAttribute(
        over_ctl, "blink", "float", 0, minValue=0, maxValue=1
    )
    blinkUpper_att = attribute.addAttribute(
        over_ctl, "upperBlink", "float", 0, minValue=0, maxValue=1
    )
    blinkLower_att = attribute.addAttribute(
        over_ctl, "lowerBlink", "float", 0, minValue=0, maxValue=1
    )
    blinkMult_att = attribute.addAttribute(
        over_ctl, "blinkMult", "float", 1, minValue=1, maxValue=2
    )
    midBlinkH_att = attribute.addAttribute(
        over_ctl, "blinkHeight", "float", blinkH, minValue=0, maxValue=1
    )

    # Add blink + upper and blink + lower so animator can use both.
    # But also clamp them so using both doesn't exceed 1.0
    blinkAdd = pm.createNode("plusMinusAverage")
    blinkClamp = pm.createNode("clamp")
    blinkClamp.maxR.set(1.0)
    blinkClamp.maxG.set(1.0)
    blink_att.connect(blinkAdd.input2D[0].input2Dx)
    blink_att.connect(blinkAdd.input2D[0].input2Dy)
    blinkUpper_att.connect(blinkAdd.input2D[1].input2Dx)
    blinkLower_att.connect(blinkAdd.input2D[1].input2Dy)
    addOutput = blinkAdd.output2D
    addOutput.output2Dx.connect(blinkClamp.inputR)
    addOutput.output2Dy.connect(blinkClamp.inputG)
    # Drive the clamped blinks through blinkMult, then to the blendshapes

    # mult_node = node.createMulNode(blinkClamp.outputR, blinkMult_att)
    # mult_nodeLower = node.createMulNode(blinkClamp.outputG, blinkMult_att)
    # pm.connectAttr(
    #     mult_node + ".outputX", bs_upBlink[0].attr(midTarget.name())
    # )
    # pm.connectAttr(
    #     mult_nodeLower + ".outputX", bs_lowBlink[0].attr(midTargetLower.name())
    # )
    # pm.connectAttr(midBlinkH_att, bs_mid[0].attr(upTarget.name()))
    # pm.connectAttr(midBlinkH_att, bs_midLower[0].attr(upTarget.name()))

    mult_node = node.createMulNode(blinkClamp.outputR, blinkMult_att)
    mult_nodeLower = node.createMulNode(blinkClamp.outputG, blinkMult_att)

    # Connect attributes using cmds.connectAttr()
    cmds.connectAttr(
        "{}.outputX".format(mult_node),
        "{}.{}".format(bs_upBlink[0], midTarget.name()),
    )

    cmds.connectAttr(
        "{}.outputX".format(mult_nodeLower),
        "{}.{}".format(bs_lowBlink[0], midTargetLower.name()),
    )
    pm.connectAttr(midBlinkH_att, "{}.{}".format(bs_mid[0], upTarget.name()))

    pm.connectAttr(
        midBlinkH_att, "{}.{}".format(bs_midLower[0], upTarget.name())
    )

    low_ctl = lowControls[2]

    # Adding channels for eye tracking
    upVTracking_att = attribute.addAttribute(
        up_ctl,
        "vTracking",
        "float",
        upperVTrack,
        minValue=0,
        keyable=False,
        channelBox=True,
    )
    upHTracking_att = attribute.addAttribute(
        up_ctl,
        "hTracking",
        "float",
        upperHTrack,
        minValue=0,
        keyable=False,
        channelBox=True,
    )

    lowVTracking_att = attribute.addAttribute(
        low_ctl,
        "vTracking",
        "float",
        lowerVTrack,
        minValue=0,
        keyable=False,
        channelBox=True,
    )
    lowHTracking_att = attribute.addAttribute(
        low_ctl,
        "hTracking",
        "float",
        lowerHTrack,
        minValue=0,
        keyable=False,
        channelBox=True,
    )

    mult_node = node.createMulNode(upVTracking_att, aimTrigger_ref.attr("ty"))
    pm.connectAttr(mult_node + ".outputX", trackLvl[0].attr("ty"))
    mult_node = node.createMulNode(upHTracking_att, aimTrigger_ref.attr("tx"))
    # Correct right side horizontal tracking
    if side == "R":
        mult_node = node.createMulNode(mult_node.attr("outputX"), -1)
    pm.connectAttr(mult_node + ".outputX", trackLvl[0].attr("tx"))

    mult_node = node.createMulNode(lowVTracking_att, aimTrigger_ref.attr("ty"))
    pm.connectAttr(mult_node + ".outputX", trackLvl[1].attr("ty"))
    mult_node = node.createMulNode(lowHTracking_att, aimTrigger_ref.attr("tx"))
    # Correct right side horizontal tracking
    if side == "R":
        mult_node = node.createMulNode(mult_node.attr("outputX"), -1)
    pm.connectAttr(mult_node + ".outputX", trackLvl[1].attr("tx"))

    # Tension on blink
    # Drive the clamped blinks through to the blink tension wire deformers
    # Add blink + upper and blink + lower so animator can use both.
    # But also clamp them so using both doesn't exceed 1.0
    blinkAdd = pm.createNode("plusMinusAverage")
    blinkClamp = pm.createNode("clamp")
    blinkClamp.maxR.set(1.0)
    blinkClamp.maxG.set(1.0)
    blink_att.connect(blinkAdd.input2D[0].input2Dx)
    blink_att.connect(blinkAdd.input2D[0].input2Dy)
    blinkUpper_att.connect(blinkAdd.input2D[1].input2Dx)
    blinkLower_att.connect(blinkAdd.input2D[1].input2Dy)
    addOutput = blinkAdd.output2D
    addOutput.output2Dx.connect(blinkClamp.inputR)
    addOutput.output2Dy.connect(blinkClamp.inputG)
    # 1 and 3 are upper. 2 and 4 are lower.
    node.createReverseNode(blinkClamp.outputR, w1.scale[0])
    node.createReverseNode(blinkClamp.outputR, w3.scale[0])
    node.createReverseNode(blinkClamp.outputG, w2.scale[0])
    node.createReverseNode(blinkClamp.outputG, w4.scale[0])

    ###########################################
    # Reparenting
    ###########################################
    if parent_node:
        try:
            if isinstance(parent_node, string_types):
                parent_node = pm.PyNode(parent_node)
            parent_node.addChild(eye_root)
        except RuntimeError:
            pm.displayWarning(
                "The eye rig can not be parent to: %s. Maybe "
                "this object doesn't exist." % parent_node
            )

    ###########################################
    # Auto Skinning
    ###########################################
    if doSkin:
        # eyelid vertex rows
        totalLoops = rigidLoops + falloffLoops
        vertexLoopList = meshNavigation.getConcentricVertexLoop(
            vertexList, totalLoops
        )
        vertexRowList = meshNavigation.getVertexRowsFromLoops(vertexLoopList)

        # we set the first value 100% for the first initial loop
        skinPercList = [1.0]
        # we expect to have a regular grid topology
        for r in range(rigidLoops):
            for rr in range(2):
                skinPercList.append(1.0)
        increment = 1.0 / float(falloffLoops)
        # we invert to smooth out from 100 to 0
        inv = 1.0 - increment
        for r in range(falloffLoops):
            for rr in range(2):
                if inv < 0.0:
                    inv = 0.0
                skinPercList.append(inv)
            inv -= increment

        # this loop add an extra 0.0 indices to avoid errors
        for r in range(10):
            for rr in range(2):
                skinPercList.append(0.0)

        # base skin
        geo = pm.listRelatives(edgeLoopList[0], parent=True)[0]
        # Check if the object has a skinCluster
        objName = pm.listRelatives(geo, parent=True)[0]

        skinCluster = skin.getSkinCluster(objName)
        if not skinCluster:
            skinCluster = pm.skinCluster(
                headJnt, geo, tsb=True, nw=2, n="skinClsEyelid"
            )

        eyelidJoints = upperEyelid_jnt + lowerEyelid_jnt
        pm.progressWindow(
            title="Auto skinning process", progress=0, max=len(eyelidJoints)
        )
        firstBoundary = False
        for jnt in eyelidJoints:
            pm.progressWindow(e=True, step=1, status="\nSkinning %s" % jnt)
            skinCluster.addInfluence(jnt, weight=0)
            v = meshNavigation.getClosestVertexFromTransform(geo, jnt)

            for row in vertexRowList:

                if v in row:
                    it = 0  # iterator
                    inc = 1  # increment
                    for i, rv in enumerate(row):
                        try:
                            perc = skinPercList[it]
                            t_val = [(jnt, perc), (headJnt, 1.0 - perc)]
                            pm.skinPercent(
                                skinCluster, rv, transformValue=t_val
                            )
                            if rv.isOnBoundary():
                                # we need to compare with the first boundary
                                # to check if the row have inverted direction
                                # and offset the value
                                if not firstBoundary:
                                    firstBoundary = True
                                    firstBoundaryValue = it

                                else:
                                    if it < firstBoundaryValue:
                                        it -= 1
                                    elif it > firstBoundaryValue:
                                        it += 1
                                inc = 2
                        except IndexError:
                            continue

                        it = it + inc
        pm.progressWindow(e=True, endProgress=True)

        # Eye Mesh skinning
        skinCluster = skin.getSkinCluster(eyeMesh)
        if not skinCluster:
            skinCluster = pm.skinCluster(
                eyeCenter_jnt, eyeMesh, tsb=True, nw=1, n="skinClsEye"
            )


##########################################################
# Eye Rig UI
##########################################################


class ui(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(ui, self).__init__(parent)

        # File type filter for settings.
        self.filter = "Eyes Rigger Configuration .eyes (*.eyes)"

        self.create()

    def create(self):

        self.setWindowTitle("Eye Rigger")
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)

        self.create_controls()
        self.create_layout()
        self.create_connections()

    def create_controls(self):

        # Geometry input controls
        self.geometryInput_group = QtWidgets.QGroupBox("Geometry Input")
        self.eyeball_label = QtWidgets.QLabel("Eyeball:")
        self.eyeMesh = QtWidgets.QLineEdit()
        self.eyeball_button = QtWidgets.QPushButton("<<")
        self.edgeloop_label = QtWidgets.QLabel("Edge Loop:")
        self.edgeLoop = QtWidgets.QLineEdit()
        self.edgeloop_button = QtWidgets.QPushButton("<<")

        # Manual corners
        self.manualCorners_group = QtWidgets.QGroupBox("Custom Eye Corners")
        self.customCorner = QtWidgets.QCheckBox("Set Manual Vertex Corners")
        self.customCorner.setChecked(False)
        self.intCorner_label = QtWidgets.QLabel("Internal Corner")
        self.intCorner = QtWidgets.QLineEdit()
        self.intCorner_button = QtWidgets.QPushButton("<<")
        self.extCorner_label = QtWidgets.QLabel("External Corner")
        self.extCorner = QtWidgets.QLineEdit()
        self.extCorner_button = QtWidgets.QPushButton("<<")

        # Blink heigh slider
        self.blinkHeight_group = QtWidgets.QGroupBox("Blink Height")
        self.blinkH = QtWidgets.QSpinBox()
        self.blinkH.setRange(0, 100)
        self.blinkH.setSingleStep(10)
        self.blinkH.setValue(20)
        self.blinkHeight_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.blinkHeight_slider.setRange(0, 100)
        self.blinkHeight_slider.setSingleStep(
            self.blinkHeight_slider.maximum() / 10.0
        )
        self.blinkHeight_slider.setValue(20)

        # vTrack and hTrack
        self.tracking_group = QtWidgets.QGroupBox("Tracking")
        self.upperVTrack = QtWidgets.QDoubleSpinBox()
        self.upperVTrack.setValue(0.02)
        self.upperHTrack = QtWidgets.QDoubleSpinBox()
        self.upperHTrack.setValue(0.01)
        self.lowerVTrack = QtWidgets.QDoubleSpinBox()
        self.lowerVTrack.setValue(0.02)
        self.lowerHTrack = QtWidgets.QDoubleSpinBox()
        self.lowerHTrack.setValue(0.01)

        # Name prefix
        self.prefix_group = QtWidgets.QGroupBox("Name Prefix")
        self.namePrefix = QtWidgets.QLineEdit()
        self.namePrefix.setText("eye")
        self.control_group = QtWidgets.QGroupBox("Control Name Extension")
        self.ctlName = QtWidgets.QLineEdit()
        self.ctlName.setText("ctl")

        # joints
        self.joints_group = QtWidgets.QGroupBox("Joints")
        self.headJnt_label = QtWidgets.QLabel("Head or Eye area Joint:")
        self.headJnt = QtWidgets.QLineEdit()
        self.headJnt_button = QtWidgets.QPushButton("<<")

        # Topological Autoskin
        self.topoSkin_group = QtWidgets.QGroupBox("蒙皮")
        self.rigidLoops_label = QtWidgets.QLabel("Rigid Loops:")
        self.rigidLoops = QtWidgets.QSpinBox()
        self.rigidLoops.setRange(0, 30)
        self.rigidLoops.setSingleStep(1)
        self.rigidLoops.setValue(2)
        self.falloffLoops_label = QtWidgets.QLabel("Falloff Loops:")
        self.falloffLoops = QtWidgets.QSpinBox()
        self.falloffLoops.setRange(0, 30)
        self.falloffLoops.setSingleStep(1)
        self.falloffLoops.setValue(4)

        self.doSkin = QtWidgets.QCheckBox("Compute Topological Autoskin")
        self.doSkin.setChecked(True)

        # Options
        self.options_group = QtWidgets.QGroupBox("选项")
        self.parent_label = QtWidgets.QLabel("Rig Parent:")
        self.parent_node = QtWidgets.QLineEdit()
        self.parent_button = QtWidgets.QPushButton("<<")
        self.aim_controller_label = QtWidgets.QLabel("Aim Controller:")
        self.aim_controller = QtWidgets.QLineEdit()
        self.aim_controller_button = QtWidgets.QPushButton("<<")
        self.ctlShapeOffset_label = QtWidgets.QLabel("Controls Offset:")
        self.offset = QtWidgets.QDoubleSpinBox()
        self.offset.setRange(0, 10)
        self.offset.setSingleStep(0.05)
        self.offset.setValue(0.05)
        self.sideRange = QtWidgets.QCheckBox(
            "Use Z axis for wide calculation (i.e: Horse and fish side eyes)"
        )
        self.sideRange.setChecked(False)

        self.ctlSet_label = QtWidgets.QLabel("Controls Set:")
        self.ctlSet = QtWidgets.QLineEdit()
        self.ctlSet_button = QtWidgets.QPushButton("<<")

        self.deformersSet_label = QtWidgets.QLabel("Deformers Set:")
        self.defSet = QtWidgets.QLineEdit()
        self.deformersSet_button = QtWidgets.QPushButton("<<")

        self.deformers_group_label = QtWidgets.QLabel("Static Rig Parent:")
        self.deformers_group = QtWidgets.QLineEdit()
        self.deformers_group_button = QtWidgets.QPushButton("<<")

        # Main buttons
        self.build_button = QtWidgets.QPushButton("Build Eye Rig")
        self.import_button = QtWidgets.QPushButton("Import Config from json")
        self.export_button = QtWidgets.QPushButton("Export Config to json")

    def create_layout(self):

        # Eyeball Layout
        eyeball_layout = QtWidgets.QHBoxLayout()
        eyeball_layout.setContentsMargins(1, 1, 1, 1)
        eyeball_layout.addWidget(self.eyeball_label)
        eyeball_layout.addWidget(self.eyeMesh)
        eyeball_layout.addWidget(self.eyeball_button)

        # Edge Loop Layout
        edgeloop_layout = QtWidgets.QHBoxLayout()
        edgeloop_layout.setContentsMargins(1, 1, 1, 1)
        edgeloop_layout.addWidget(self.edgeloop_label)
        edgeloop_layout.addWidget(self.edgeLoop)
        edgeloop_layout.addWidget(self.edgeloop_button)

        # Geometry Input Layout
        geometryInput_layout = QtWidgets.QVBoxLayout()
        geometryInput_layout.setContentsMargins(6, 1, 6, 2)
        geometryInput_layout.addLayout(eyeball_layout)
        geometryInput_layout.addLayout(edgeloop_layout)
        self.geometryInput_group.setLayout(geometryInput_layout)

        # Blink Height Layout
        blinkHeight_layout = QtWidgets.QHBoxLayout()
        blinkHeight_layout.setContentsMargins(1, 1, 1, 1)
        blinkHeight_layout.addWidget(self.blinkH)
        blinkHeight_layout.addWidget(self.blinkHeight_slider)
        self.blinkHeight_group.setLayout(blinkHeight_layout)

        # Tracking Layout
        tracking_layout = QtWidgets.QVBoxLayout()
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Upper Vertical"))
        layout.addWidget(self.upperVTrack)
        layout.addWidget(QtWidgets.QLabel("Upper Horizontal"))
        layout.addWidget(self.upperHTrack)
        tracking_layout.addLayout(layout)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Lower Vertical"))
        layout.addWidget(self.lowerVTrack)
        layout.addWidget(QtWidgets.QLabel("Lower Horizontal"))
        layout.addWidget(self.lowerHTrack)
        tracking_layout.addLayout(layout)
        self.tracking_group.setLayout(tracking_layout)

        # joints Layout
        headJnt_layout = QtWidgets.QHBoxLayout()
        headJnt_layout.addWidget(self.headJnt_label)
        headJnt_layout.addWidget(self.headJnt)
        headJnt_layout.addWidget(self.headJnt_button)

        joints_layout = QtWidgets.QVBoxLayout()
        joints_layout.setContentsMargins(6, 4, 6, 4)
        joints_layout.addLayout(headJnt_layout)
        self.joints_group.setLayout(joints_layout)

        # topological autoskin Layout
        skinLoops_layout = QtWidgets.QGridLayout()
        skinLoops_layout.addWidget(self.rigidLoops_label, 0, 0)
        skinLoops_layout.addWidget(self.falloffLoops_label, 0, 1)
        skinLoops_layout.addWidget(self.rigidLoops, 1, 0)
        skinLoops_layout.addWidget(self.falloffLoops, 1, 1)

        topoSkin_layout = QtWidgets.QVBoxLayout()
        topoSkin_layout.setContentsMargins(6, 4, 6, 4)
        topoSkin_layout.addWidget(self.doSkin, alignment=QtCore.Qt.Alignment())
        topoSkin_layout.addLayout(skinLoops_layout)
        self.topoSkin_group.setLayout(topoSkin_layout)

        # Manual Corners Layout
        intCorner_layout = QtWidgets.QHBoxLayout()
        intCorner_layout.addWidget(self.intCorner_label)
        intCorner_layout.addWidget(self.intCorner)
        intCorner_layout.addWidget(self.intCorner_button)

        extCorner_layout = QtWidgets.QHBoxLayout()
        extCorner_layout.addWidget(self.extCorner_label)
        extCorner_layout.addWidget(self.extCorner)
        extCorner_layout.addWidget(self.extCorner_button)

        manualCorners_layout = QtWidgets.QVBoxLayout()
        manualCorners_layout.setContentsMargins(6, 4, 6, 4)
        manualCorners_layout.addWidget(
            self.customCorner, alignment=QtCore.Qt.Alignment()
        )
        manualCorners_layout.addLayout(intCorner_layout)
        manualCorners_layout.addLayout(extCorner_layout)
        self.manualCorners_group.setLayout(manualCorners_layout)

        # Options Layout
        parent_layout = QtWidgets.QHBoxLayout()
        parent_layout.addWidget(self.parent_label)
        parent_layout.addWidget(self.parent_node)
        parent_layout.addWidget(self.parent_button)
        parent_layout.addWidget(self.aim_controller_label)
        parent_layout.addWidget(self.aim_controller)
        parent_layout.addWidget(self.aim_controller_button)
        offset_layout = QtWidgets.QHBoxLayout()
        offset_layout.addWidget(self.ctlShapeOffset_label)
        offset_layout.addWidget(self.offset)
        ctlSet_layout = QtWidgets.QHBoxLayout()
        ctlSet_layout.addWidget(self.ctlSet_label)
        ctlSet_layout.addWidget(self.ctlSet)
        ctlSet_layout.addWidget(self.ctlSet_button)
        deformersGrp_layout = QtWidgets.QHBoxLayout()
        deformersGrp_layout.addWidget(self.deformersSet_label)
        deformersGrp_layout.addWidget(self.defSet)
        deformersGrp_layout.addWidget(self.deformersSet_button)
        deformersGrp_layout.addWidget(self.deformers_group_label)
        deformersGrp_layout.addWidget(self.deformers_group)
        deformersGrp_layout.addWidget(self.deformers_group_button)

        options_layout = QtWidgets.QVBoxLayout()
        options_layout.setContentsMargins(6, 1, 6, 2)
        options_layout.addLayout(parent_layout)
        options_layout.addLayout(offset_layout)
        options_layout.addWidget(self.blinkHeight_group)
        options_layout.addWidget(self.tracking_group)
        options_layout.addWidget(self.sideRange)
        options_layout.addLayout(ctlSet_layout)
        options_layout.addLayout(deformersGrp_layout)
        self.options_group.setLayout(options_layout)

        # Name prefix
        namePrefix_layout = QtWidgets.QVBoxLayout()
        namePrefix_layout.setContentsMargins(1, 1, 1, 1)
        namePrefix_layout.addWidget(self.namePrefix)
        self.prefix_group.setLayout(namePrefix_layout)

        # Name prefix
        controlExtension_layout = QtWidgets.QVBoxLayout()
        controlExtension_layout.setContentsMargins(1, 1, 1, 1)
        controlExtension_layout.addWidget(self.ctlName)
        self.control_group.setLayout(controlExtension_layout)

        # Main Layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.addWidget(self.prefix_group)
        main_layout.addWidget(self.control_group)
        main_layout.addWidget(self.geometryInput_group)
        main_layout.addWidget(self.manualCorners_group)
        main_layout.addWidget(self.options_group)
        main_layout.addWidget(self.joints_group)
        main_layout.addWidget(self.topoSkin_group)
        main_layout.addWidget(self.build_button)
        main_layout.addWidget(self.import_button)
        main_layout.addWidget(self.export_button)

        self.setLayout(main_layout)

    def create_connections(self):
        self.blinkH.valueChanged[int].connect(self.blinkHeight_slider.setValue)
        self.blinkHeight_slider.valueChanged[int].connect(self.blinkH.setValue)

        self.eyeball_button.clicked.connect(
            partial(self.populate_object, self.eyeMesh)
        )
        self.parent_button.clicked.connect(
            partial(self.populate_object, self.parent_node)
        )
        self.aim_controller_button.clicked.connect(
            partial(self.populate_object, self.aim_controller)
        )
        self.headJnt_button.clicked.connect(
            partial(self.populate_object, self.headJnt, 1)
        )

        self.edgeloop_button.clicked.connect(self.populate_edgeloop)

        self.build_button.clicked.connect(self.build_rig)
        self.import_button.clicked.connect(self.import_settings)
        self.export_button.clicked.connect(self.export_settings)

        self.intCorner_button.clicked.connect(
            partial(self.populate_element, self.intCorner, "vertex")
        )
        self.extCorner_button.clicked.connect(
            partial(self.populate_element, self.extCorner, "vertex")
        )

        self.ctlSet_button.clicked.connect(
            partial(self.populate_element, self.ctlSet, "objectSet")
        )
        self.deformersSet_button.clicked.connect(
            partial(self.populate_element, self.defSet, "objectSet")
        )
        self.deformers_group_button.clicked.connect(
            partial(self.populate_element, self.deformers_group)
        )

    # SLOTS ##########################################################
    def populate_element(self, lEdit, oType="transform"):
        if oType == "joint":
            oTypeInst = pm.nodetypes.Joint
        elif oType == "vertex":
            oTypeInst = pm.MeshVertex
        elif oType == "objectSet":
            oTypeInst = pm.nodetypes.ObjectSet
        else:
            oTypeInst = pm.nodetypes.Transform

        oSel = pm.selected()
        if oSel:
            if isinstance(oSel[0], oTypeInst):
                lEdit.setText(oSel[0].name())
            else:
                pm.displayWarning(
                    "The selected element is not a valid %s" % oType
                )
        else:
            pm.displayWarning("Please select first one %s." % oType)

    def populate_object(self, lEdit, oType=None):
        if oType == 1:
            oType = pm.nodetypes.Joint
        else:
            oType = pm.nodetypes.Transform

        oSel = pm.selected()
        if oSel:
            if isinstance(oSel[0], oType):
                lEdit.setText(oSel[0].name())
            else:
                pm.displayWarning("The selected element is not a valid object")
        else:
            pm.displayWarning("Please select first the  object.")

    def populate_edgeloop(self):
        self.edgeLoop.setText(lib.get_edge_loop_from_selection())

    def build_rig(self):
        rig(**lib.get_settings_from_widget(self))

    def export_settings(self):
        data_string = json.dumps(
            lib.get_settings_from_widget(self), indent=4, sort_keys=True
        )

        file_path = lib.get_file_path(self.filter, "save")
        if not file_path:
            return

        with open(file_path, "w") as f:
            f.write(data_string)

    def import_settings(self):
        file_path = lib.get_file_path(self.filter, "open")
        if not file_path:
            return

        lib.import_settings_from_file(file_path, self)


# Build from json file.
def rig_from_file(path):
    rig(**json.load(open(path)))


def show(*args):
    gqt.showDialog(ui)


if __name__ == "__main__":
    show()

    # path = r"C:\Users\admin\Desktop\temp.eyes"
    # rig_from_file(path)

    # path = "C:\\Users\\miquel\\Desktop\\eye_R.eyes"
    # rig_from_file(path)
