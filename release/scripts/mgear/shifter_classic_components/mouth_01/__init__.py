"""Component Mouth 01 module"""

import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import attribute, transform, primitive

#############################################
# COMPONENT
#############################################


class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def addObjects(self):
        """Add all the objects needed to create the component."""

        # jaw control
        t = transform.getTransformFromPos(self.guide.pos["jaw"])

        self.ctl_npo = primitive.addTransform(
            self.root, self.getName("ctl_npo"), t)

        self.jaw_ctl = self.addCtl(
            self.ctl_npo,
            "jaw_ctl",
            t,
            self.color_fk,
            "circle",
            w=1 * self.size,
            ro=datatypes.Vector([1.5708, 0, 0]),
            tp=self.parentCtlTag)

        attribute.setKeyableAttributes(self.jaw_ctl, ["tx", "ty", "tz", "rz"])

        # mouth center
        t = transform.getTransformFromPos(self.guide.pos["rotcenter"])
        self.mouthCenter_npo = primitive.addTransform(
            self.root, self.getName("mouthCenter_npo"), t)
        self.mouthCenter = primitive.addTransform(
            self.mouthCenter_npo, self.getName("mouthCenter"), t)

        # jaw "UPPER"
        t = transform.getTransformFromPos(self.guide.pos["root"])
        self.jawUp_npo = primitive.addTransform(
            self.mouthCenter, self.getName("jawUpper_npo"), t)
        self.jawUp_pos = primitive.addTransform(
            self.jawUp_npo, self.getName("jawUpper_pos"), t)
        self.jawUp_rot = primitive.addTransform(
            self.jawUp_pos, self.getName("jawUpper_rot"), t)

        # jaw "LOWER"
        t = transform.getTransformFromPos(self.guide.pos["root"])
        self.jawLow_npo = primitive.addTransform(
            self.mouthCenter, self.getName("jaw_npo"), t)
        self.jawLow_pos = primitive.addTransform(
            self.jawLow_npo, self.getName("jawLow_pos"), t)
        self.jawLow_rot = primitive.addTransform(
            self.jawLow_pos, self.getName("jawLow_rot"), t)

        # lips
        t = transform.getTransformFromPos(self.guide.pos["lipup"])

        self.lipup_npo = primitive.addTransform(
            self.jawUp_rot, self.getName("lipup_npo"), t)

        self.lipup_ctl = self.addCtl(
            self.lipup_npo,
            "lipup_ctl",
            t,
            self.color_fk,
            "square",
            d=.15 * self.size,
            w=1 * self.size,
            ro=datatypes.Vector([1.5708, 0, 0]),
            tp=self.jaw_ctl)

        t = transform.getTransformFromPos(self.guide.pos["liplow"])

        self.liplow_npo = primitive.addTransform(
            self.jawLow_rot, self.getName("liplow_npo"), t)

        self.liplow_ctl = self.addCtl(
            self.liplow_npo,
            "liplow_ctl",
            t, self.color_fk,
            "square",
            d=.15 * self.size,
            w=1 * self.size,
            ro=datatypes.Vector([1.5708, 0, 0]),
            tp=self.jaw_ctl)

        # teeth
        t = transform.getTransformFromPos(self.guide.pos["lipup"])
        self.teethup_npo = primitive.addTransform(
            self.jawUp_rot, self.getName("teethup_npo"), t)

        self.teethup_ctl = self.addCtl(self.teethup_npo,
                                       "teethup_ctl",
                                       t,
                                       self.color_ik,
                                       "square",
                                       d=.1 * self.size,
                                       w=.7 * self.size,
                                       ro=datatypes.Vector([1.5708, 0, 0]),
                                       tp=self.lipup_ctl)

        t = transform.getTransformFromPos(self.guide.pos["liplow"])

        self.teethlow_npo = primitive.addTransform(
            self.jawLow_rot, self.getName("teethlow_npo"), t)

        self.teethlow_ctl = self.addCtl(self.teethlow_npo,
                                        "teethlow_ctl",
                                        t,
                                        self.color_ik,
                                        "square",
                                        d=.1 * self.size,
                                        w=.7 * self.size,
                                        ro=datatypes.Vector([1.5708, 0, 0]),
                                        tp=self.liplow_ctl)

        self.jnt_pos.append(
            [self.jawLow_rot, "jaw", "parent_relative_jnt", False])
        self.jnt_pos.append(
            [self.lipup_ctl, "lipup", "parent_relative_jnt", False])
        # relative 0 is the jaw jnt
        self.jnt_pos.append(
            [self.liplow_ctl, "liplow", "jaw", False])
        self.jnt_pos.append(
            [self.teethup_ctl, "teethup", "parent_relative_jnt", False])
        self.jnt_pos.append(
            [self.teethlow_ctl, "teethlow", "jaw", False])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        self.sideRotation_att = self.addAnimParam(
            "siderot", "Sides Rotation", "double", 20, 0, 100)
        self.vertRotation_att = self.addAnimParam(
            "vertrot", "Vertical Rotation", "double", 40, 0, 100)
        self.frontalTranslation_att = self.addAnimParam(
            "fronttrans", "Frontal Translation", "double", 1, 0, 1)
        self.verticalTranslation_att = self.addAnimParam(
            "verttrans", "Vertical Translation", "double", 0.2, 0, 1)
        self.followLips_att = self.addAnimParam(
            "floowlips", "FollowLips", "double", 0.05, 0, 1)
        self.lipsAlignSpeed_att = self.addAnimParam(
            "lipsAlignSpeed", "Lips Align Speed", "double", 10, 0, 100)

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """

        # mouth center rotation
        pm.connectAttr(self.jaw_ctl + ".rotateZ",
                       self.mouthCenter + ".rotateZ")

        # Node Creation ########

        # Mut Div nodes
        md_node_1 = pm.createNode("multiplyDivide")
        md_node_2 = pm.createNode("multiplyDivide")
        md_node_3 = pm.createNode("multiplyDivide")
        md_node_4 = pm.createNode("multiplyDivide")
        md_node_5 = pm.createNode("multiplyDivide")
        md_node_6 = pm.createNode("multiplyDivide")
        md_node_7 = pm.createNode("multiplyDivide")
        md_node_8 = pm.createNode("multiplyDivide")

        # Clamp o_node
        clamp_node = pm.createNode("clamp")

        # Condition nodes
        cond_node_1 = pm.createNode("condition")
        cond_node_2 = pm.createNode("condition")
        cond_node_3 = pm.createNode("condition")

        # Blend nodes
        blend_node_1 = pm.createNode("blendColors")
        blend_node_2 = pm.createNode("blendColors")

        # Node Conexions ########

        # md_node_1
        pm.connectAttr(self.jaw_ctl + ".translateY", md_node_1 + ".input1X")
        pm.connectAttr(self.vertRotation_att, md_node_1 + ".input2X")

        # md_node_2
        pm.connectAttr(self.jaw_ctl + ".translateX", md_node_2 + ".input1X")
        pm.connectAttr(self.sideRotation_att, md_node_2 + ".input2X")

        # md_node_3
        pm.connectAttr(self.jaw_ctl + ".translateY", md_node_3 + ".input1X")
        pm.connectAttr(self.lipsAlignSpeed_att, md_node_3 + ".input2X")

        # md_node_4
        pm.connectAttr(self.jaw_ctl + ".translateY", md_node_4 + ".input1X")
        pm.connectAttr(self.verticalTranslation_att, md_node_4 + ".input2X")

        # md_node_5
        pm.connectAttr(self.jaw_ctl + ".translateZ", md_node_5 + ".input1X")
        pm.connectAttr(self.frontalTranslation_att, md_node_5 + ".input2X")

        # md_node_6
        pm.connectAttr(md_node_1 + ".outputX", md_node_6 + ".input1X")
        pm.setAttr(md_node_6 + ".input2X", -1.0)

        # md_node_7
        pm.connectAttr(md_node_5 + ".outputX", md_node_7 + ".input1X")
        pm.connectAttr(clamp_node + ".outputR", md_node_7 + ".input2X")

        # md_node_8
        pm.connectAttr(cond_node_2 + ".outColorR", md_node_8 + ".input1X")
        pm.connectAttr(clamp_node + ".outputR", md_node_8 + ".input2X")

        # clamp_node
        pm.connectAttr(md_node_3 + ".outputX", clamp_node + ".inputR")
        pm.setAttr(clamp_node + ".maxR", 1.0)

        # cond_node_1
        pm.connectAttr(md_node_6 + ".outputX", cond_node_1 + ".colorIfTrueR")
        pm.connectAttr(md_node_6 + ".outputX", cond_node_1 + ".firstTerm")
        pm.setAttr(cond_node_1 + ".operation", 4)
        pm.setAttr(cond_node_1 + ".colorIfFalseR", 0)

        # cond_node_2
        pm.connectAttr(md_node_2 + ".outputX", cond_node_2 + ".colorIfFalseR")
        pm.connectAttr(md_node_6 + ".outputX", cond_node_2 + ".firstTerm")
        pm.setAttr(cond_node_2 + ".operation", 2)

        # cond_node_3
        pm.connectAttr(md_node_4 + ".outputX", cond_node_3 + ".colorIfTrueR")
        pm.connectAttr(md_node_4 + ".outputX", cond_node_3 + ".firstTerm")
        pm.setAttr(cond_node_3 + ".operation", 4)
        pm.setAttr(cond_node_3 + ".colorIfFalseR", 0)

        # blend_node_1
        pm.connectAttr(self.followLips_att, blend_node_1 + ".blender")
        pm.connectAttr(md_node_6 + ".outputX", blend_node_1 + ".color1R")
        pm.connectAttr(md_node_2 + ".outputX", blend_node_1 + ".color1G")
        pm.connectAttr(cond_node_1 + ".outColorR", blend_node_1 + ".color2R")
        pm.connectAttr(md_node_8 + ".outputX", blend_node_1 + ".color2G")

        # blend_node_2
        pm.connectAttr(self.followLips_att, blend_node_2 + ".blender")
        pm.connectAttr(cond_node_3 + ".outColorR", blend_node_2 + ".color1R")
        pm.connectAttr(md_node_5 + ".outputX", blend_node_2 + ".color1G")
        pm.connectAttr(md_node_7 + ".outputX", blend_node_2 + ".color2G")

        # inputs to transforms

        pm.connectAttr(md_node_6 + ".outputX", self.jawLow_rot + ".rotateX")
        pm.connectAttr(md_node_2 + ".outputX", self.jawLow_rot + ".rotateY")

        pm.connectAttr(blend_node_1 + ".outputR", self.jawUp_rot + ".rotateX")
        pm.connectAttr(blend_node_1 + ".outputG", self.jawUp_rot + ".rotateY")

        pm.connectAttr(cond_node_3 + ".outColorR",
                       self.jawLow_pos + ".translateY")
        pm.connectAttr(md_node_5 + ".outputX",
                       self.jawLow_pos + ".translateZ")

        pm.connectAttr(blend_node_2 + ".outputR",
                       self.jawUp_pos + ".translateY")
        pm.connectAttr(blend_node_2 + ".outputG",
                       self.jawUp_pos + ".translateZ")

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.root
        self.relatives["jaw"] = self.jawLow_rot
        self.relatives["rotcenter"] = self.jawLow_rot
        self.relatives["lipup"] = self.lipup_ctl
        self.relatives["liplow"] = self.liplow_ctl

        self.controlRelatives["root"] = self.parentCtlTag
        self.controlRelatives["jaw"] = self.jaw_ctl
        self.controlRelatives["rotcenter"] = self.jaw_ctl
        self.controlRelatives["lipup"] = self.lipup_ctl
        self.controlRelatives["liplow"] = self.liplow_ctl

        self.jointRelatives["root"] = 0
        self.jointRelatives["jaw"] = 0
        self.jointRelatives["rotcenter"] = 0
        self.jointRelatives["lipup"] = 1
        self.jointRelatives["liplow"] = 2
