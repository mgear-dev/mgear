"""Rigbits lips rigger tool"""

import json
from functools import partial
from mgear.core.six import string_types

import mgear.core.pyqt as gqt
import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from mgear.vendor.Qt import QtCore, QtWidgets
from mgear.pymaya import datatypes

from mgear import rigbits
from mgear.core import meshNavigation, curve, applyop, primitive, icon
from mgear.core import transform, attribute, skin, vector

from . import lib

##########################################################
# Lips rig constructor
##########################################################


def rig(edge_loop="",
        up_vertex="",
        low_vertex="",
        name_prefix="",
        thickness=0.3,
        do_skin=True,
        rigid_loops=5,
        falloff_loops=8,
        head_joint=None,
        jaw_joint=None,
        parent_node=None,
        control_name="ctl",
        upper_lip_ctl=None,
        lower_lip_ctl=None):

    ######
    # Var
    ######

    FRONT_OFFSET = .02
    NB_ROPE = 15

    ##################
    # Helper functions
    ##################
    def setName(name, side="C", idx=None):
        namesList = [name_prefix, side, name]
        if idx is not None:
            namesList[1] = side + str(idx)
        name = "_".join(namesList)
        return name

    ###############
    # Checkers
    ##############

    # Loop
    if edge_loop:
        try:
            edge_loop = [pm.PyNode(e) for e in edge_loop.split(",")]
        except RuntimeError:
            pm.displayWarning(
                "Some of the edges listed in edge loop can not be found")
            return
    else:
        pm.displayWarning("Please set the edge loop first")
        return

    # Vertex
    if up_vertex:
        try:
            up_vertex = pm.PyNode(up_vertex)
        except RuntimeError:
            pm.displayWarning("%s can not be found" % up_vertex)
            return
    else:
        pm.displayWarning("Please set the upper lip central vertex")
        return

    if low_vertex:
        try:
            low_vertex = pm.PyNode(low_vertex)
        except RuntimeError:
            pm.displayWarning("%s can not be found" % low_vertex)
            return
    else:
        pm.displayWarning("Please set the lower lip central vertex")
        return

    # skinnign data
    if do_skin:
        if not head_joint:
            pm.displayWarning("Please set the Head Jnt or unCheck Compute "
                              "Topological Autoskin")
            return
        else:
            try:
                head_joint = pm.PyNode(head_joint)
            except RuntimeError:
                pm.displayWarning(
                    "Head Joint: %s can not be found" % head_joint
                )
                return
        if not jaw_joint:
            pm.displayWarning("Please set the Jaw Jnt or unCheck Compute "
                              "Topological Autoskin")
            return
        else:
            try:
                jaw_joint = pm.PyNode(jaw_joint)
            except RuntimeError:
                pm.displayWarning("Jaw Joint: %s can not be found" % jaw_joint)
                return
    # check if the rig already exist in the current scene
    if pm.ls(setName("root")):
        pm.displayWarning("The object %s already exist in the scene. Please "
                          "choose another name prefix" % setName("root"))
        return

    #####################
    # Root creation
    #####################
    lips_root = primitive.addTransform(None, setName("root"))
    lipsCrv_root = primitive.addTransform(lips_root, setName("crvs"))
    lipsRope_root = primitive.addTransform(lips_root, setName("rope"))

    #####################
    # Geometry
    #####################
    geo = pm.listRelatives(edge_loop[0], parent=True)[0]

    #####################
    # Groups
    #####################
    try:
        ctlSet = pm.PyNode("rig_controllers_grp")
    except RuntimeError:
        pm.sets(n="rig_controllers_grp", em=True)
        ctlSet = pm.PyNode("rig_controllers_grp")
    try:
        defset = pm.PyNode("rig_deformers_grp")
    except RuntimeError:
        pm.sets(n="rig_deformers_grp", em=True)
        defset = pm.PyNode("rig_deformers_grp")

    #####################
    # Curves creation
    #####################

    # get extreme position using the outer loop
    extr_v = meshNavigation.getExtremeVertexFromLoop(edge_loop)
    upPos = extr_v[0]
    lowPos = extr_v[1]
    inPos = extr_v[2]
    outPos = extr_v[3]
    edgeList = extr_v[4]
    vertexList = extr_v[5]
    upPos = up_vertex
    lowPos = low_vertex

    # upper crv
    upLip_edgeRange = meshNavigation.edgeRangeInLoopFromMid(edgeList,
                                                            upPos,
                                                            inPos,
                                                            outPos)
    upCrv = curve.createCuveFromEdges(upLip_edgeRange,
                                      setName("upperLip"),
                                      parent=lipsCrv_root)
    # store the closest vertex by curv cv index. To be use fo the auto skining
    upLip_closestVtxList = []
    # offset upper lip Curve
    cvs = upCrv.getCVs(space="world")
    for i, cv in enumerate(cvs):

        closestVtx = meshNavigation.getClosestVertexFromTransform(geo, cv)
        upLip_closestVtxList.append(closestVtx)
        if i == 0:
            # we know the curv starts from right to left
            offset = [cv[0] - thickness, cv[1], cv[2] - thickness]
        elif i == len(cvs) - 1:
            offset = [cv[0] + thickness, cv[1], cv[2] - thickness]
        else:
            offset = [cv[0], cv[1] + thickness, cv[2]]
        upCrv.setCV(i, offset, space='world')

    # lower crv
    lowLip_edgeRange = meshNavigation.edgeRangeInLoopFromMid(edgeList,
                                                             lowPos,
                                                             inPos,
                                                             outPos)
    lowCrv = curve.createCuveFromEdges(lowLip_edgeRange,
                                       setName("lowerLip"),
                                       parent=lipsCrv_root)
    lowLip_closestVtxList = []
    # offset lower lip Curve
    cvs = lowCrv.getCVs(space="world")
    for i, cv in enumerate(cvs):
        closestVtx = meshNavigation.getClosestVertexFromTransform(geo, cv)
        lowLip_closestVtxList.append(closestVtx)
        if i == 0:
            # we know the curv starts from right to left
            offset = [cv[0] - thickness, cv[1], cv[2] - thickness]
        elif i == len(cvs) - 1:
            offset = [cv[0] + thickness, cv[1], cv[2] - thickness]
        else:
            # we populate the closest vertext list here to skipt the first
            # and latest point
            offset = [cv[0], cv[1] - thickness, cv[2]]
        lowCrv.setCV(i, offset, space='world')

    upCrv_ctl = curve.createCurveFromCurve(upCrv,
                                           setName("upCtl_crv"),
                                           nbPoints=7,
                                           parent=lipsCrv_root)
    lowCrv_ctl = curve.createCurveFromCurve(lowCrv,
                                            setName("lowCtl_crv"),
                                            nbPoints=7,
                                            parent=lipsCrv_root)

    upRope = curve.createCurveFromCurve(upCrv,
                                        setName("upRope_crv"),
                                        nbPoints=NB_ROPE,
                                        parent=lipsCrv_root)
    lowRope = curve.createCurveFromCurve(lowCrv,
                                         setName("lowRope_crv"),
                                         nbPoints=NB_ROPE,
                                         parent=lipsCrv_root)

    upCrv_upv = curve.createCurveFromCurve(upCrv,
                                           setName("upCrv_upv"),
                                           nbPoints=7,
                                           parent=lipsCrv_root)
    lowCrv_upv = curve.createCurveFromCurve(lowCrv,
                                            setName("lowCrv_upv"),
                                            nbPoints=7,
                                            parent=lipsCrv_root)

    upRope_upv = curve.createCurveFromCurve(upCrv,
                                            setName("upRope_upv"),
                                            nbPoints=NB_ROPE,
                                            parent=lipsCrv_root)
    lowRope_upv = curve.createCurveFromCurve(lowCrv,
                                             setName("lowRope_upv"),
                                             nbPoints=NB_ROPE,
                                             parent=lipsCrv_root)

    # offset upv curves

    for crv in [upCrv_upv, lowCrv_upv, upRope_upv, lowRope_upv]:
        cvs = crv.getCVs(space="world")
        for i, cv in enumerate(cvs):

            # we populate the closest vertext list here to skipt the first
            # and latest point
            offset = [cv[0], cv[1], cv[2] + FRONT_OFFSET]
            crv.setCV(i, offset, space='world')

    rigCrvs = [upCrv,
               lowCrv,
               upCrv_ctl,
               lowCrv_ctl,
               upRope,
               lowRope,
               upCrv_upv,
               lowCrv_upv,
               upRope_upv,
               lowRope_upv]

    for crv in rigCrvs:
        crv.attr("visibility").set(False)

    ##################
    # Joints
    ##################

    lvlType = "transform"

    # upper joints
    upperJoints = []
    cvs = upCrv.getCVs(space="world")
    pm.progressWindow(title='Creating Upper Joints', progress=0, max=len(cvs))

    for i, cv in enumerate(cvs):
        pm.progressWindow(e=True,
                          step=1,
                          status='\nCreating Joint for  %s' % cv)
        oTransUpV = pm.PyNode(pm.createNode(
            lvlType,
            n=setName("upLipRopeUpv", idx=str(i).zfill(3)),
            p=lipsRope_root,
            ss=True))
        oTrans = pm.PyNode(
            pm.createNode(lvlType,
                          n=setName("upLipRope", idx=str(i).zfill(3)),
                          p=lipsRope_root, ss=True))

        oParam, oLength = curve.getCurveParamAtPosition(upRope, cv)
        uLength = curve.findLenghtFromParam(upRope, oParam)
        u = uLength / oLength

        applyop.pathCns(
            oTransUpV, upRope_upv, cnsType=False, u=u, tangent=False)

        cns = applyop.pathCns(
            oTrans, upRope, cnsType=False, u=u, tangent=False)

        cns.setAttr("worldUpType", 1)
        cns.setAttr("frontAxis", 0)
        cns.setAttr("upAxis", 1)

        pm.connectAttr(oTransUpV.attr("worldMatrix[0]"),
                       cns.attr("worldUpMatrix"))

        # getting joint parent
        if head_joint and isinstance(head_joint, (str, string_types)):
            try:
                j_parent = pm.PyNode(head_joint)
            except RuntimeError:
                j_parent = False
        elif head_joint and isinstance(head_joint, pm.nodetypes.Joint):
            j_parent = head_joint
        else:
            j_parent = False

        jnt = rigbits.addJnt(oTrans, noReplace=True, parent=j_parent)
        upperJoints.append(jnt)
        pm.sets(defset, add=jnt)
    pm.progressWindow(e=True, endProgress=True)

    # lower joints
    lowerJoints = []
    cvs = lowCrv.getCVs(space="world")
    pm.progressWindow(title='Creating Lower Joints', progress=0, max=len(cvs))

    for i, cv in enumerate(cvs):
        pm.progressWindow(e=True,
                          step=1,
                          status='\nCreating Joint for  %s' % cv)
        oTransUpV = pm.PyNode(pm.createNode(
            lvlType,
            n=setName("lowLipRopeUpv", idx=str(i).zfill(3)),
            p=lipsRope_root,
            ss=True))

        oTrans = pm.PyNode(pm.createNode(
            lvlType,
            n=setName("lowLipRope", idx=str(i).zfill(3)),
            p=lipsRope_root,
            ss=True))

        oParam, oLength = curve.getCurveParamAtPosition(lowRope, cv)
        uLength = curve.findLenghtFromParam(lowRope, oParam)
        u = uLength / oLength

        applyop.pathCns(oTransUpV,
                        lowRope_upv,
                        cnsType=False,
                        u=u,
                        tangent=False)
        cns = applyop.pathCns(oTrans,
                              lowRope,
                              cnsType=False,
                              u=u,
                              tangent=False)

        cns.setAttr("worldUpType", 1)
        cns.setAttr("frontAxis", 0)
        cns.setAttr("upAxis", 1)

        pm.connectAttr(oTransUpV.attr("worldMatrix[0]"),
                       cns.attr("worldUpMatrix"))

        # getting joint parent
        if jaw_joint and isinstance(jaw_joint, (str, string_types)):
            try:
                j_parent = pm.PyNode(jaw_joint)
            except RuntimeError:
                pass
        elif jaw_joint and isinstance(jaw_joint,  pm.nodetypes.Joint):
            j_parent = jaw_joint
        else:
            j_parent = False
        jnt = rigbits.addJnt(oTrans, noReplace=True, parent=j_parent)
        lowerJoints.append(jnt)
        pm.sets(defset, add=jnt)
    pm.progressWindow(e=True, endProgress=True)

    ##################
    # Controls
    ##################

    # Controls lists
    upControls = []
    upVec = []
    upNpo = []
    lowControls = []
    lowVec = []
    lowNpo = []
    # controls options
    axis_list = ["sx", "sy", "sz", "ro"]
    upCtlOptions = [["corner", "R", "square", 4, .05, axis_list],
                    ["upOuter", "R", "circle", 14, .03, []],
                    ["upInner", "R", "circle", 14, .03, []],
                    ["upper", "C", "square", 4, .05, axis_list],
                    ["upInner", "L", "circle", 14, .03, []],
                    ["upOuter", "L", "circle", 14, .03, []],
                    ["corner", "L", "square", 4, .05, axis_list]]

    lowCtlOptions = [["lowOuter", "R", "circle", 14, .03, []],
                     ["lowInner", "R", "circle", 14, .03, []],
                     ["lower", "C", "square", 4, .05, axis_list],
                     ["lowInner", "L", "circle", 14, .03, []],
                     ["lowOuter", "L", "circle", 14, .03, []]]

    params = ["tx", "ty", "tz", "rx", "ry", "rz"]

    # upper controls
    cvs = upCrv_ctl.getCVs(space="world")
    pm.progressWindow(title='Upper controls', progress=0, max=len(cvs))

    # v0 = transform.getTransformFromPos(cvs[0])
    # v1 = transform.getTransformFromPos(cvs[-1])
    distSize = vector.getDistance(cvs[0], cvs[-1]) * 3

    for i, cv in enumerate(cvs):
        pm.progressWindow(e=True,
                          step=1,
                          status='\nCreating control for%s' % cv)
        t = transform.getTransformFromPos(cv)

        # Get nearest joint for orientation of controls
        joints = upperJoints + lowerJoints
        nearest_joint = None
        nearest_distance = None
        for joint in joints:
            distance = vector.getDistance(
                transform.getTranslation(joint),
                cv
            )
            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest_joint = joint

        if nearest_joint:
            t = transform.setMatrixPosition(
                transform.getTransform(nearest_joint), cv
            )
            temp = primitive.addTransform(
                lips_root, setName("temp"), t
            )
            temp.rx.set(0)
            t = transform.getTransform(temp)
            pm.delete(temp)

        oName = upCtlOptions[i][0]
        oSide = upCtlOptions[i][1]
        o_icon = upCtlOptions[i][2]
        color = upCtlOptions[i][3]
        wd = upCtlOptions[i][4]
        oPar = upCtlOptions[i][5]
        npo = primitive.addTransform(lips_root,
                                     setName("%s_npo" % oName, oSide),
                                     t)
        upNpo.append(npo)
        ctl = icon.create(npo,
                          setName("%s_%s" % (oName, control_name), oSide),
                          t,
                          icon=o_icon,
                          w=wd * distSize,
                          d=wd * distSize,
                          ro=datatypes.Vector(1.57079633, 0, 0),
                          po=datatypes.Vector(0, 0, .07 * distSize),
                          color=color)

        upControls.append(ctl)
        name_split = control_name.split("_")
        if len(name_split) == 2 and name_split[-1] == "ghost":
            pass
        else:
            pm.sets(ctlSet, add=ctl)
        attribute.addAttribute(ctl, "isCtl", "bool", keyable=False)
        attribute.setKeyableAttributes(ctl, params + oPar)

        upv = primitive.addTransform(ctl, setName("%s_upv" % oName, oSide), t)
        upv.attr("tz").set(FRONT_OFFSET)
        upVec.append(upv)
        if oSide == "R":
            npo.attr("sx").set(-1)
    pm.progressWindow(e=True, endProgress=True)

    # lower controls
    cvs = lowCrv_ctl.getCVs(space="world")
    pm.progressWindow(title='Lower controls', progress=0, max=len(cvs))

    for i, cv in enumerate(cvs[1:-1]):
        pm.progressWindow(e=True,
                          step=1,
                          status='\nCreating control for%s' % cv)

        t = transform.getTransformFromPos(cv)

        # Get nearest joint for orientation of controls
        joints = upperJoints + lowerJoints
        nearest_joint = None
        nearest_distance = None
        for joint in joints:
            distance = vector.getDistance(
                transform.getTranslation(joint),
                cv
            )
            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest_joint = joint

        if nearest_joint:
            t = transform.setMatrixPosition(
                transform.getTransform(nearest_joint), cv
            )
            temp = primitive.addTransform(
                lips_root, setName("temp"), t
            )
            temp.rx.set(0)
            t = transform.getTransform(temp)
            pm.delete(temp)

        oName = lowCtlOptions[i][0]
        oSide = lowCtlOptions[i][1]
        o_icon = lowCtlOptions[i][2]
        color = lowCtlOptions[i][3]
        wd = lowCtlOptions[i][4]
        oPar = lowCtlOptions[i][5]
        npo = primitive.addTransform(lips_root,
                                     setName("%s_npo" % oName, oSide),
                                     t)
        lowNpo.append(npo)
        ctl = icon.create(npo,
                          setName("%s_%s" % (oName, control_name), oSide),
                          t,
                          icon=o_icon,
                          w=wd * distSize,
                          d=wd * distSize,
                          ro=datatypes.Vector(1.57079633, 0, 0),
                          po=datatypes.Vector(0, 0, .07 * distSize),
                          color=color)
        lowControls.append(ctl)
        name_split = control_name.split("_")
        if len(name_split) == 2 and control_name.split("_")[-1] == "ghost":
            pass
        else:
            pm.sets(ctlSet, add=ctl)
        attribute.addAttribute(ctl, "isCtl", "bool", keyable=False)
        attribute.setKeyableAttributes(ctl, params + oPar)

        upv = primitive.addTransform(ctl, setName("%s_upv" % oName, oSide), t)
        upv.attr("tz").set(FRONT_OFFSET)
        lowVec.append(upv)
        if oSide == "R":
            npo.attr("sx").set(-1)
    pm.progressWindow(e=True, endProgress=True)

    # reparentig controls
    pm.parent(upNpo[1], lowNpo[0], upControls[0])
    pm.parent(upNpo[2], upNpo[4], upControls[3])
    pm.parent(upNpo[-2], lowNpo[-1], upControls[-1])
    pm.parent(lowNpo[1], lowNpo[3], lowControls[2])

    # Connecting control crvs with controls
    applyop.gear_curvecns_op(upCrv_ctl, upControls)
    applyop.gear_curvecns_op(lowCrv_ctl,
                             [upControls[0]] + lowControls + [upControls[-1]])

    applyop.gear_curvecns_op(upCrv_upv, upVec)
    applyop.gear_curvecns_op(lowCrv_upv, [upVec[0]] + lowVec + [upVec[-1]])

    # adding wires
    pm.wire(upCrv, w=upCrv_ctl, dropoffDistance=[0, 1000])
    pm.wire(lowCrv, w=lowCrv_ctl, dropoffDistance=[0, 1000])
    pm.wire(upRope, w=upCrv_ctl, dropoffDistance=[0, 1000])
    pm.wire(lowRope, w=lowCrv_ctl, dropoffDistance=[0, 1000])

    pm.wire(upRope_upv, w=upCrv_upv, dropoffDistance=[0, 1000])
    pm.wire(lowRope_upv, w=lowCrv_upv, dropoffDistance=[0, 1000])

    # setting constrains
    # up
    cns_node = pm.parentConstraint(upControls[0],
                                   upControls[3],
                                   upControls[1].getParent(),
                                   mo=True,
                                   skipRotate=["x", "y", "z"])
    cns_node.attr(upControls[0].name() + "W0").set(.75)
    cns_node.attr(upControls[3].name() + "W1").set(.25)
    cns_node.interpType.set(0)  # noFlip

    cns_node = pm.parentConstraint(upControls[0],
                                   upControls[3],
                                   upControls[2].getParent(),
                                   mo=True,
                                   skipRotate=["x", "y", "z"])
    cns_node.attr(upControls[0].name() + "W0").set(.25)
    cns_node.attr(upControls[3].name() + "W1").set(.75)
    cns_node.interpType.set(0)  # noFlip

    cns_node = pm.parentConstraint(upControls[3],
                                   upControls[6],
                                   upControls[4].getParent(),
                                   mo=True,
                                   skipRotate=["x", "y", "z"])
    cns_node.attr(upControls[3].name() + "W0").set(.75)
    cns_node.attr(upControls[6].name() + "W1").set(.25)
    cns_node.interpType.set(0)  # noFlip

    cns_node = pm.parentConstraint(upControls[3],
                                   upControls[6],
                                   upControls[5].getParent(),
                                   mo=True,
                                   skipRotate=["x", "y", "z"])
    cns_node.attr(upControls[3].name() + "W0").set(.25)
    cns_node.attr(upControls[6].name() + "W1").set(.75)
    cns_node.interpType.set(0)  # noFlip

    # low
    cns_node = pm.parentConstraint(upControls[0],
                                   lowControls[2],
                                   lowControls[0].getParent(),
                                   mo=True,
                                   skipRotate=["x", "y", "z"])
    cns_node.attr(upControls[0].name() + "W0").set(.75)
    cns_node.attr(lowControls[2].name() + "W1").set(.25)
    cns_node.interpType.set(0)  # noFlip

    cns_node = pm.parentConstraint(upControls[0],
                                   lowControls[2],
                                   lowControls[1].getParent(),
                                   mo=True,
                                   skipRotate=["x", "y", "z"])
    cns_node.attr(upControls[0].name() + "W0").set(.25)
    cns_node.attr(lowControls[2].name() + "W1").set(.75)
    cns_node.interpType.set(0)  # noFlip

    cns_node = pm.parentConstraint(lowControls[2],
                                   upControls[6],
                                   lowControls[3].getParent(),
                                   mo=True,
                                   skipRotate=["x", "y", "z"])
    cns_node.attr(lowControls[2].name() + "W0").set(.75)
    cns_node.attr(upControls[6].name() + "W1").set(.25)
    cns_node.interpType.set(0)  # noFlip

    cns_node = pm.parentConstraint(lowControls[2],
                                   upControls[6],
                                   lowControls[4].getParent(),
                                   mo=True,
                                   skipRotate=["x", "y", "z"])
    cns_node.attr(lowControls[2].name() + "W0").set(.25)
    cns_node.attr(upControls[6].name() + "W1").set(.75)
    cns_node.interpType.set(0)  # noFlip

    ###########################################
    # Connecting rig
    ###########################################
    if parent_node:
        try:
            if isinstance(parent_node, string_types):
                parent_node = pm.PyNode(parent_node)
            parent_node.addChild(lips_root)
        except RuntimeError:
            pm.displayWarning("The Lips rig can not be parent to: %s. Maybe "
                              "this object doesn't exist." % parent_node)
    if head_joint and jaw_joint:
        try:
            if isinstance(head_joint, string_types):
                head_joint = pm.PyNode(head_joint)
        except RuntimeError:
            pm.displayWarning("Head Joint or Upper Lip Joint %s. Can not be "
                              "fount in the scene" % head_joint)
            return
        try:
            if isinstance(jaw_joint, string_types):
                jaw_joint = pm.PyNode(jaw_joint)
        except RuntimeError:
            pm.displayWarning("Jaw Joint or Lower Lip Joint %s. Can not be "
                              "fount in the scene" % jaw_joint)
            return

        ref_ctls = [head_joint, jaw_joint]

        if upper_lip_ctl and lower_lip_ctl:
            try:
                if isinstance(upper_lip_ctl, string_types):
                    upper_lip_ctl = pm.PyNode(upper_lip_ctl)
            except RuntimeError:
                pm.displayWarning("Upper Lip Ctl %s. Can not be "
                                  "fount in the scene" % upper_lip_ctl)
                return
            try:
                if isinstance(lower_lip_ctl, string_types):
                    lower_lip_ctl = pm.PyNode(lower_lip_ctl)
            except RuntimeError:
                pm.displayWarning("Lower Lip Ctl %s. Can not be "
                                  "fount in the scene" % lower_lip_ctl)
                return
            ref_ctls = [upper_lip_ctl, lower_lip_ctl]

        # in order to avoid flips lets create a reference transform
        # also to avoid flips, set any multi target parentConstraint to noFlip
        ref_cns_list = []
        for cns_ref in ref_ctls:

            t = transform.getTransformFromPos(
                cns_ref.getTranslation(space='world'))
            ref = pm.createNode("transform",
                                n=cns_ref.name() + "_cns",
                                p=cns_ref,
                                ss=True)
            ref.setMatrix(t, worldSpace=True)
            ref_cns_list.append(ref)
        # right corner connection
        cns_node = pm.parentConstraint(ref_cns_list[0],
                                       ref_cns_list[1],
                                       upControls[0].getParent(),
                                       mo=True)
        cns_node.interpType.set(0)  # noFlip
        # left corner connection
        cns_node = pm.parentConstraint(ref_cns_list[0],
                                       ref_cns_list[1],
                                       upControls[-1].getParent(),
                                       mo=True)
        cns_node.interpType.set(0)  # noFlip
        # up control connection
        cns_node = pm.parentConstraint(ref_cns_list[0],
                                       upControls[3].getParent(),
                                       mo=True)
        # low control connection
        cns_node = pm.parentConstraint(ref_cns_list[1],
                                       lowControls[2].getParent(),
                                       mo=True)

    ###########################################
    # Auto Skinning
    ###########################################
    if do_skin:
        # eyelid vertex rows
        totalLoops = rigid_loops + falloff_loops
        vertexLoopList = meshNavigation.getConcentricVertexLoop(vertexList,
                                                                totalLoops)
        vertexRowList = meshNavigation.getVertexRowsFromLoops(vertexLoopList)

        # we set the first value 100% for the first initial loop
        skinPercList = [1.0]
        # we expect to have a regular grid topology
        for r in range(rigid_loops):
            for rr in range(2):
                skinPercList.append(1.0)
        increment = 1.0 / float(falloff_loops)
        # we invert to smooth out from 100 to 0
        inv = 1.0 - increment
        for r in range(falloff_loops):
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
        if head_joint:
            try:
                head_joint = pm.PyNode(head_joint)
            except RuntimeError:
                pm.displayWarning(
                    "Auto skin aborted can not find %s " % head_joint)
                return

        # Check if the object has a skinCluster
        objName = pm.listRelatives(geo, parent=True)[0]

        skinCluster = skin.getSkinCluster(objName)
        if not skinCluster:
            [skinCluster] = pm.skinCluster(head_joint,
                                         geo,
                                         tsb=True,
                                         nw=2,
                                         n='skinClsEyelid')

        lipsJoints = upperJoints + lowerJoints
        closestVtxList = upLip_closestVtxList + lowLip_closestVtxList
        pm.progressWindow(title='Auto skinning process',
                          progress=0,
                          max=len(lipsJoints))

        for i, jnt in enumerate(lipsJoints):
            pm.progressWindow(e=True, step=1, status='\nSkinning %s' % jnt)
            skinCluster.addInfluence(jnt, weight=0)
            v = closestVtxList[i]
            for row in vertexRowList:
                if v in row:
                    for i, rv in enumerate(row):
                        # find the deformer with max value for each vertex
                        w = pm.skinPercent(skinCluster,
                                           rv,
                                           query=True,
                                           value=True)
                        transJoint = pm.skinPercent(skinCluster,
                                                    rv,
                                                    query=True,
                                                    t=None)
                        max_value = max(w)
                        max_index = w.index(max_value)

                        perc = skinPercList[i]
                        t_value = [(jnt, perc),
                                   (transJoint[max_index], 1.0 - perc)]
                        pm.skinPercent(skinCluster,
                                       rv,
                                       transformValue=t_value)
        pm.progressWindow(e=True, endProgress=True)


##########################################################
# Lips Rig UI
##########################################################

class ui(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(ui, self).__init__(parent)

        self.filter = "Lips Rigger Configuration .lips (*.lips)"

        self.create()

    def create(self):

        self.setWindowTitle("Lips Rigger")
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)

        self.create_controls()
        self.create_layout()
        self.create_connections()

    def create_controls(self):

        # Geometry input controls
        self.geometryInput_group = QtWidgets.QGroupBox("Geometry Input")
        self.edgedge_loop_label = QtWidgets.QLabel("Edge Loop:")
        self.edge_loop = QtWidgets.QLineEdit()
        self.edge_loop_button = QtWidgets.QPushButton("<<")
        self.up_vertex_label = QtWidgets.QLabel("Upper Vertex:")
        self.up_vertex = QtWidgets.QLineEdit()
        self.up_vertex_button = QtWidgets.QPushButton("<<")
        self.low_vertex_label = QtWidgets.QLabel("Lower Vertex:")
        self.low_vertex = QtWidgets.QLineEdit()
        self.low_vertex_button = QtWidgets.QPushButton("<<")

        # Name prefix
        self.prefix_group = QtWidgets.QGroupBox("Name Prefix")
        self.name_prefix = QtWidgets.QLineEdit()
        self.name_prefix.setText("lips")

        # control extension
        self.control_group = QtWidgets.QGroupBox("Control Name Extension")
        self.control_name = QtWidgets.QLineEdit()
        self.control_name.setText("ctl")

        # joints
        self.joints_group = QtWidgets.QGroupBox("Joints")
        self.head_joint_label = QtWidgets.QLabel("Head or Upper Lip Joint:")
        self.head_joint = QtWidgets.QLineEdit()
        self.head_joint_button = QtWidgets.QPushButton("<<")
        self.jaw_joint_label = QtWidgets.QLabel("Jaw or Lower Lip Joint:")
        self.jaw_joint = QtWidgets.QLineEdit()
        self.jaw_joint_button = QtWidgets.QPushButton("<<")

        # Lips Controls
        self.control_ref_group = QtWidgets.QGroupBox(
            "Lips Base Controls (Optional. Required for Shifter Game tools)")
        self.upper_lip_ctl_label = QtWidgets.QLabel("Upper Lip Control:")
        self.upper_lip_ctl = QtWidgets.QLineEdit()
        self.upper_lip_ctl_button = QtWidgets.QPushButton("<<")
        self.lower_lip_ctl_label = QtWidgets.QLabel("Lower Lip Control:")
        self.lower_lip_ctl = QtWidgets.QLineEdit()
        self.lower_lip_ctl_button = QtWidgets.QPushButton("<<")

        # Topological Autoskin
        self.topoSkin_group = QtWidgets.QGroupBox("Skin")
        self.rigid_loops_label = QtWidgets.QLabel("Rigid Loops:")
        self.rigid_loops = QtWidgets.QSpinBox()
        self.rigid_loops.setRange(0, 30)
        self.rigid_loops.setSingleStep(1)
        self.rigid_loops.setValue(5)
        self.falloff_loops_label = QtWidgets.QLabel("Falloff Loops:")
        self.falloff_loops = QtWidgets.QSpinBox()
        self.falloff_loops.setRange(0, 30)
        self.falloff_loops.setSingleStep(1)
        self.falloff_loops.setValue(8)

        self.do_skin = QtWidgets.QCheckBox(
            'Compute Topological Autoskin')
        self.do_skin.setChecked(True)

        # Options
        self.options_group = QtWidgets.QGroupBox("Options")
        self.thickness_label = QtWidgets.QLabel("Lips Thickness:")
        self.thickness = QtWidgets.QDoubleSpinBox()
        self.thickness.setRange(0, 10)
        self.thickness.setSingleStep(.01)
        self.thickness.setValue(.03)
        self.parent_label = QtWidgets.QLabel("Static Rig Parent:")
        self.parent_node = QtWidgets.QLineEdit()
        self.parent_button = QtWidgets.QPushButton("<<")
        # Build button
        self.build_button = QtWidgets.QPushButton("Build Lips Rig")
        self.import_button = QtWidgets.QPushButton("Import Config from json")
        self.export_button = QtWidgets.QPushButton("Export Config to json")

    def create_layout(self):

        # Edge Loop Layout
        edgedge_loop_layout = QtWidgets.QHBoxLayout()
        edgedge_loop_layout.setContentsMargins(1, 1, 1, 1)
        edgedge_loop_layout.addWidget(self.edgedge_loop_label)
        edgedge_loop_layout.addWidget(self.edge_loop)
        edgedge_loop_layout.addWidget(self.edge_loop_button)

        # Outer Edge Loop Layout
        up_vertex_layout = QtWidgets.QHBoxLayout()
        up_vertex_layout.setContentsMargins(1, 1, 1, 1)
        up_vertex_layout.addWidget(self.up_vertex_label)
        up_vertex_layout.addWidget(self.up_vertex)
        up_vertex_layout.addWidget(self.up_vertex_button)

        # inner Edge Loop Layout
        low_vertex_layout = QtWidgets.QHBoxLayout()
        low_vertex_layout.setContentsMargins(1, 1, 1, 1)
        low_vertex_layout.addWidget(self.low_vertex_label)
        low_vertex_layout.addWidget(self.low_vertex)
        low_vertex_layout.addWidget(self.low_vertex_button)

        # Geometry Input Layout
        geometryInput_layout = QtWidgets.QVBoxLayout()
        geometryInput_layout.setContentsMargins(6, 1, 6, 2)
        geometryInput_layout.addLayout(edgedge_loop_layout)
        geometryInput_layout.addLayout(up_vertex_layout)
        geometryInput_layout.addLayout(low_vertex_layout)
        self.geometryInput_group.setLayout(geometryInput_layout)

        # joints Layout
        head_joint_layout = QtWidgets.QHBoxLayout()
        head_joint_layout.addWidget(self.head_joint_label)
        head_joint_layout.addWidget(self.head_joint)
        head_joint_layout.addWidget(self.head_joint_button)

        jaw_joint_layout = QtWidgets.QHBoxLayout()
        jaw_joint_layout.addWidget(self.jaw_joint_label)
        jaw_joint_layout.addWidget(self.jaw_joint)
        jaw_joint_layout.addWidget(self.jaw_joint_button)

        joints_layout = QtWidgets.QVBoxLayout()
        joints_layout.setContentsMargins(6, 4, 6, 4)
        joints_layout.addLayout(head_joint_layout)
        joints_layout.addLayout(jaw_joint_layout)
        self.joints_group.setLayout(joints_layout)

        # control Layout
        upper_lip_ctl_layout = QtWidgets.QHBoxLayout()
        upper_lip_ctl_layout.addWidget(self.upper_lip_ctl_label)
        upper_lip_ctl_layout.addWidget(self.upper_lip_ctl)
        upper_lip_ctl_layout.addWidget(self.upper_lip_ctl_button)

        lower_lip_ctl_layout = QtWidgets.QHBoxLayout()
        lower_lip_ctl_layout.addWidget(self.lower_lip_ctl_label)
        lower_lip_ctl_layout.addWidget(self.lower_lip_ctl)
        lower_lip_ctl_layout.addWidget(self.lower_lip_ctl_button)

        control_ref_layout = QtWidgets.QVBoxLayout()
        control_ref_layout.setContentsMargins(6, 4, 6, 4)
        control_ref_layout.addLayout(upper_lip_ctl_layout)
        control_ref_layout.addLayout(lower_lip_ctl_layout)
        self.control_ref_group.setLayout(control_ref_layout)

        # topological autoskin Layout
        skinLoops_layout = QtWidgets.QGridLayout()
        skinLoops_layout.addWidget(self.rigid_loops_label, 0, 0)
        skinLoops_layout.addWidget(self.falloff_loops_label, 0, 1)
        skinLoops_layout.addWidget(self.rigid_loops, 1, 0)
        skinLoops_layout.addWidget(self.falloff_loops, 1, 1)

        topoSkin_layout = QtWidgets.QVBoxLayout()
        topoSkin_layout.setContentsMargins(6, 4, 6, 4)
        topoSkin_layout.addWidget(self.do_skin,
                                  alignment=QtCore.Qt.Alignment())
        topoSkin_layout.addLayout(skinLoops_layout)
        topoSkin_layout.addLayout(head_joint_layout)
        topoSkin_layout.addLayout(jaw_joint_layout)
        self.topoSkin_group.setLayout(topoSkin_layout)

        # Options Layout
        lipThickness_layout = QtWidgets.QHBoxLayout()
        lipThickness_layout.addWidget(self.thickness_label)
        lipThickness_layout.addWidget(self.thickness)
        parent_layout = QtWidgets.QHBoxLayout()
        parent_layout.addWidget(self.parent_label)
        parent_layout.addWidget(self.parent_node)
        parent_layout.addWidget(self.parent_button)
        options_layout = QtWidgets.QVBoxLayout()
        options_layout.setContentsMargins(6, 1, 6, 2)
        options_layout.addLayout(lipThickness_layout)
        # options_layout.addLayout(offset_layout)
        options_layout.addLayout(parent_layout)
        self.options_group.setLayout(options_layout)

        # Name prefix
        name_prefix_layout = QtWidgets.QHBoxLayout()
        name_prefix_layout.setContentsMargins(1, 1, 1, 1)
        name_prefix_layout.addWidget(self.name_prefix)
        self.prefix_group.setLayout(name_prefix_layout)

        # Control Name Extension
        controlExtension_layout = QtWidgets.QHBoxLayout()
        controlExtension_layout.setContentsMargins(1, 1, 1, 1)
        controlExtension_layout.addWidget(self.control_name)
        self.control_group.setLayout(controlExtension_layout)

        # Main Layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.addWidget(self.prefix_group)
        main_layout.addWidget(self.control_group)
        main_layout.addWidget(self.geometryInput_group)
        main_layout.addWidget(self.options_group)
        main_layout.addWidget(self.joints_group)
        main_layout.addWidget(self.control_ref_group)
        main_layout.addWidget(self.topoSkin_group)
        main_layout.addWidget(self.build_button)
        main_layout.addWidget(self.import_button)
        main_layout.addWidget(self.export_button)

        self.setLayout(main_layout)

    def create_connections(self):
        self.edge_loop_button.clicked.connect(
            partial(self.populate_edge_loop, self.edge_loop)
        )
        self.up_vertex_button.clicked.connect(
            partial(self.populate_element, self.up_vertex, "vertex")
        )
        self.low_vertex_button.clicked.connect(
            partial(self.populate_element, self.low_vertex, "vertex")
        )
        self.parent_button.clicked.connect(
            partial(self.populate_element, self.parent_node)
        )
        self.head_joint_button.clicked.connect(
            partial(self.populate_element, self.head_joint, "joint")
        )
        self.jaw_joint_button.clicked.connect(
            partial(self.populate_element, self.jaw_joint, "joint")
        )
        self.upper_lip_ctl_button.clicked.connect(
            partial(self.populate_element, self.upper_lip_ctl)
        )
        self.lower_lip_ctl_button.clicked.connect(
            partial(self.populate_element, self.lower_lip_ctl)
        )
        self.build_button.clicked.connect(self.build_rig)
        self.import_button.clicked.connect(self.import_settings)
        self.export_button.clicked.connect(self.export_settings)

    # SLOTS ##########################################################

    # TODO: create a checker to ensure that the vertex selected are part of
    # the main edgelopp
    def populate_element(self, lEdit, oType="transform"):
        if oType == "joint":
            oTypeInst = pm.nodetypes.Joint
        elif oType == "vertex":
            oTypeInst = pm.MeshVertex
        else:
            oTypeInst = pm.nodetypes.Transform

        oSel = pm.selected()
        if oSel:
            if isinstance(oSel[0], oTypeInst):
                lEdit.setText(oSel[0].name())
            else:
                pm.displayWarning(
                    "The selected element is not a valid %s" % oType)
        else:
            pm.displayWarning("Please select first one %s." % oType)

    def populate_edge_loop(self, lineEdit):
        lineEdit.setText(lib.get_edge_loop_from_selection())

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
