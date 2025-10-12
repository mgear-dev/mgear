import os

import mgear.pymaya as pm

import mgear.core.attribute as att
import mgear.core.transform as tra
import mgear.shifter.component as comp

skelFK = [
    u"mGear_Mocap_interface_" + joint
    for joint in (
        u"Hips",
        u"LeftUpLeg",
        u"LeftLeg",
        u"LeftFoot",
        u"LeftToeBase",
        u"RightUpLeg",
        u"RightLeg",
        u"RightFoot",
        u"RightToeBase",
        u"Spine",
        u"Spine1",
        u"Spine2",
        u"Spine3",
        u"Spine4",
        u"LeftShoulder",
        u"LeftArm",
        u"LeftForeArm",
        u"LeftHand",
        u"LeftHandThumb1",
        u"LeftHandThumb2",
        u"LeftHandThumb3",
        u"LeftHandIndex1",
        u"LeftHandIndex2",
        u"LeftHandIndex3",
        u"LeftHandMiddle1",
        u"LeftHandMiddle2",
        u"LeftHandMiddle3",
        u"LeftHandRing1",
        u"LeftHandRing2",
        u"LeftHandRing3",
        u"LeftHandPinky1",
        u"LeftHandPinky2",
        u"LeftHandPinky3",
        u"RightShoulder",
        u"RightArm",
        u"RightForeArm",
        u"RightHand",
        u"RightHandThumb1",
        u"RightHandThumb2",
        u"RightHandThumb3",
        u"RightHandIndex1",
        u"RightHandIndex2",
        u"RightHandIndex3",
        u"RightHandMiddle1",
        u"RightHandMiddle2",
        u"RightHandMiddle3",
        u"RightHandRing1",
        u"RightHandRing2",
        u"RightHandRing3",
        u"RightHandPinky1",
        u"RightHandPinky2",
        u"RightHandPinky3",
        u"Neck",
        u"Neck1",
        u"Neck2",
        u"Neck3",
        u"Head"
    )
]

gearFK = [
    u"body_C0_ctl",
    u"leg_L0_fk0_ctl",
    u"leg_L0_fk1_ctl",
    u"leg_L0_fk2_ctl",
    u"foot_L0_fk0_ctl",
    u"leg_R0_fk0_ctl",
    u"leg_R0_fk1_ctl",
    u"leg_R0_fk2_ctl",
    u"foot_R0_fk0_ctl",
    u"spine_C0_fk0_ctl",
    u"spine_C0_fk1_ctl",
    u"spine_C0_fk2_ctl",
    u"shoulder_L0_ctl",
    u"arm_L0_fk0_ctl",
    u"arm_L0_fk1_ctl",
    u"arm_L0_fk2_ctl",
    u"thumb_L0_fk0_ctl",
    u"thumb_L0_fk1_ctl",
    u"thumb_L0_fk2_ctl",
    u"finger_L0_fk0_ctl",
    u"finger_L0_fk1_ctl",
    u"finger_L0_fk2_ctl",
    u"finger_L1_fk0_ctl",
    u"finger_L1_fk1_ctl",
    u"finger_L1_fk2_ctl",
    u"finger_L2_fk0_ctl",
    u"finger_L2_fk1_ctl",
    u"finger_L2_fk2_ctl",
    u"finger_L3_fk0_ctl",
    u"finger_L3_fk1_ctl",
    u"finger_L3_fk2_ctl",
    u"shoulder_R0_ctl",
    u"arm_R0_fk0_ctl",
    u"arm_R0_fk1_ctl",
    u"arm_R0_fk2_ctl",
    u"thumb_R0_fk0_ctl",
    u"thumb_R0_fk1_ctl",
    u"thumb_R0_fk2_ctl",
    u"finger_R0_fk0_ctl",
    u"finger_R0_fk1_ctl",
    u"finger_R0_fk2_ctl",
    u"finger_R1_fk0_ctl",
    u"finger_R1_fk1_ctl",
    u"finger_R1_fk2_ctl",
    u"finger_R2_fk0_ctl",
    u"finger_R2_fk1_ctl",
    u"finger_R2_fk2_ctl",
    u"finger_R3_fk0_ctl",
    u"finger_R3_fk1_ctl",
    u"finger_R3_fk2_ctl",
    u"neck_C0_fk0_ctl",
    u"neck_C0_fk1_ctl",
    u"neck_C0_head_ctl"
]

alignFK = [
    u"arm_L0_fk2_ctl",
    u"arm_L0_ikcns_ctl",
    u"arm_L0_fk1_ctl",
    u"arm_R0_fk2_ctl",
    u"arm_R0_ikcns_ctl",
    u"arm_R0_fk1_ctl"]

alignIK = [
    u"arm_L0_ikcns_ctl",
    u"arm_L0_ik_ctl",
    u"arm_L0_upv_ctl",
    u"arm_R0_ikcns_ctl",
    u"arm_R0_ik_ctl",
    u"arm_R0_upv_ctl"
]

skelIK = [
    u"mGear_Mocap_interface_LeftFoot",
    u"mGear_Mocap_interface_RightFoot",
    u"mGear_Mocap_interface_LeftUpLeg",
    u"mGear_Mocap_interface_RightUpLeg",
    u"mGear_Mocap_interface_LeftHand",

    u"mGear_Mocap_interface_LeftForeArm",
    u"mGear_Mocap_interface_RightHand",
    u"mGear_Mocap_interface_RightForeArm",
    u"mGear_Mocap_interface_LeftLeg",
    u"mGear_Mocap_interface_RightLeg",

    u"mGear_Mocap_interface_LeftForeArm",
    u"mGear_Mocap_interface_RightForeArm"
]

gearIK = [
    u"leg_L0_ik_ctl",
    u"leg_R0_ik_ctl",
    u"leg_L0_upv_ctl",
    u"leg_R0_upv_ctl",
    u"arm_L0_ik_ctl",
    u"arm_L0_upv_ctl",
    u"arm_R0_ik_ctl",
    u"arm_R0_upv_ctl",
    u"leg_L0_mid_ctl",
    u"leg_R0_mid_ctl",
    u"arm_L0_mid_ctl",
    u"arm_R0_mid_ctl"
]


def importSkeletonBiped(*args):
    path = os.path.dirname(comp.__file__)
    pm.importFile(os.path.join(path, "_templates", "MOCAP_interface_01.ma"))


def characterizeBiped(*args):
    try:
        gCtl = pm.PyNode("global_C0_ctl")
        mocapAttach = att.addAttribute(
            gCtl,
            "mocapAttach",
            "float",
            1.0,
            minValue=0.0,
            maxValue=1.0
        )
    except Exception:
        pm.displayWarning("global_C0_ctl: Is not in the scene")
        return

    # Align skeleton
    for a, b in zip(skelFK, gearFK):
        try:
            oA = pm.PyNode(a)
        except Exception:
            pm.displayWarning(a + ": Is not in the scene")
        try:
            oB = pm.PyNode(b)
        except Exception:
            pm.displayWarning(b + ": Is not in the scene")
        if a and b:
            tra.matchWorldTransform(oB, oA)

    # Constrain FK controls
    for a, b in zip(skelFK, gearFK):
        oA = pm.PyNode(a)
        oB = pm.PyNode(b)
        cns = pm.parentConstraint(oA, oB, mo=True)

        pb_node = pm.createNode("pairBlend")

        pm.connectAttr(cns + ".constraintRotateX", pb_node + ".inRotateX2")
        pm.connectAttr(cns + ".constraintRotateY", pb_node + ".inRotateY2")
        pm.connectAttr(cns + ".constraintRotateZ", pb_node + ".inRotateZ2")
        pm.connectAttr(pb_node + ".outRotateX", oB + ".rotateX", f=True)
        pm.connectAttr(pb_node + ".outRotateY", oB + ".rotateY", f=True)
        pm.connectAttr(pb_node + ".outRotateZ", oB + ".rotateZ", f=True)
        pm.setKeyframe(oB, at="rotateX")
        pm.setKeyframe(oB, at="rotateY")
        pm.setKeyframe(oB, at="rotateZ")

        pm.connectAttr(cns + ".constraintTranslateX",
                       pb_node + ".inTranslateX2")
        pm.connectAttr(cns + ".constraintTranslateY",
                       pb_node + ".inTranslateY2")
        pm.connectAttr(cns + ".constraintTranslateZ",
                       pb_node + ".inTranslateZ2")
        pm.connectAttr(pb_node + ".outTranslateX", oB + ".translateX", f=True)
        pm.connectAttr(pb_node + ".outTranslateY", oB + ".translateY", f=True)
        pm.connectAttr(pb_node + ".outTranslateZ", oB + ".translateZ", f=True)
        pm.setKeyframe(oB, at="translateX")
        pm.setKeyframe(oB, at="translateY")
        pm.setKeyframe(oB, at="translateZ")

        pm.connectAttr(mocapAttach, pb_node.attr("weight"))

    # Align IK controls with FK controls
    for a, b in zip(alignIK, alignFK):
        oA = pm.PyNode(a)
        oB = pm.PyNode(b)
        tra.matchWorldTransform(oB, oA)
        if a in [u"arm_L0_upv_ctl", u"arm_R0_upv_ctl"]:
            oA.attr("tz").set(-3)
        if a == u"arm_L0_ikcns_ctl":
            oA.attr("rx").set((oA.attr("rx").get() + 90))
        if a == u"arm_R0_ikcns_ctl":
            oA.attr("rx").set((oA.attr("rx").get() - 90))

    # constrain IK controls
    for a, b in zip(skelIK, gearIK):
        oA = pm.PyNode(a)
        oB = pm.PyNode(b)
        print(b)
        pb_node = pm.createNode("pairBlend")
        try:
            if b in (u"leg_L0_upv_ctl", u"leg_R0_upv_ctl"):
                att.lockAttribute(pm.PyNode(b), lock=False, keyable=True)
            if b in (u"leg_L0_mid_ctl",
                     u"leg_R0_mid_ctl",
                     u"arm_L0_mid_ctl",
                     u"arm_R0_mid_ctl"):
                cns = pm.pointConstraint(oA, oB, mo=True)
            else:
                cns = pm.parentConstraint(oA, oB, mo=True)
            pm.connectAttr(cns + ".constraintRotateX", pb_node + ".inRotateX2")
            pm.connectAttr(cns + ".constraintRotateY", pb_node + ".inRotateY2")
            pm.connectAttr(cns + ".constraintRotateZ", pb_node + ".inRotateZ2")
            pm.connectAttr(pb_node + ".outRotateX", oB + ".rotateX", f=True)
            pm.connectAttr(pb_node + ".outRotateY", oB + ".rotateY", f=True)
            pm.connectAttr(pb_node + ".outRotateZ", oB + ".rotateZ", f=True)
            pm.setKeyframe(oB, at="rotateX")
            pm.setKeyframe(oB, at="rotateY")
            pm.setKeyframe(oB, at="rotateZ")
        except Exception:
            cns = pm.pointConstraint(oA, oB, mo=True)

        pm.connectAttr(cns + ".constraintTranslateX",
                       pb_node + ".inTranslateX2")
        pm.connectAttr(cns + ".constraintTranslateY",
                       pb_node + ".inTranslateY2")
        pm.connectAttr(cns + ".constraintTranslateZ",
                       pb_node + ".inTranslateZ2")
        pm.connectAttr(pb_node + ".outTranslateX", oB + ".translateX", f=True)
        pm.connectAttr(pb_node + ".outTranslateY", oB + ".translateY", f=True)
        pm.connectAttr(pb_node + ".outTranslateZ", oB + ".translateZ", f=True)
        pm.setKeyframe(oB, at="translateX")
        pm.setKeyframe(oB, at="translateY")
        pm.setKeyframe(oB, at="translateZ")

        pm.connectAttr(mocapAttach, pb_node.attr("weight"))


def bakeMocap(*args):
    start = pm.playbackOptions(query=True, min=True)
    end = pm.playbackOptions(query=True, max=True)

    if pm.selected() and pm.selected()[0].name()[-3:] == "ctl":
        controls = gearFK + gearIK

        if len(pm.selected()[0].name().split(":")) == 2:
            for i, x in enumerate(controls):
                controls[i] = pm.selected()[0].name().split(":")[0] + ":" + x
        # Using a custom bake system because bakeResults is
        # slow with pairblend nodes.
        for x in range(int(start), int(end + 1)):
            pm.currentTime(x)
            pm.setKeyframe(controls)
    else:
        pm.displayWarning("Please select on control of the rig to "
                          "determine wich character will be baked")
