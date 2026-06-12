
from mgear.shifter import component

import mgear.pymaya as pm
from mgear.pymaya import datatypes
from mgear.core import attribute, transform, primitive, applyop
from mgear.core import node, curve


##########################################################
# COMPONENT
##########################################################


class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def addObjects(self):
        """Add all the objects needed to create the component."""

        if self.negate:
            self.normal = self.guide.blades["blade"].z
            axis = "yx"
        else:
            axis = "yx"
            self.normal = self.guide.blades["blade"].z * -1
        self.binormal = self.guide.blades["blade"].x

        t = transform.getTransformLookingAt(self.guide.apos[0],
                                            self.guide.apos[1],
                                            self.normal,
                                            axis=axis,
                                            negate=self.negate)

        self.ctl_npo = primitive.addTransform(
            self.root, self.getName("ctl_npo"), t)
        self.base_ctl = self.addCtl(self.ctl_npo,
                                    "base_ctl",
                                    t,
                                    self.color_ik,
                                    "square",
                                    w=.3,
                                    tp=self.parentCtlTag)

        attribute.setKeyableAttributes(self.base_ctl, self.tr_params)

        self.base_upv = primitive.addTransform(
            self.base_ctl, self.getName("base_upv"), t)
        self.base_upv.attr("tz").set(.01)

        # tangent 0
        vec_pos = self.guide.pos["tan0"]
        t = transform.setMatrixPosition(t, vec_pos)

        self.tan0_npo = primitive.addTransform(
            self.base_ctl, self.getName("tan0_npo"), t)

        self.tan0_ctl = self.addCtl(
            self.tan0_npo,
            "tan0_ctl",
            t,
            self.color_ik,
            "sphere",
            w=.4,
            tp=self.base_ctl
        )

        attribute.setKeyableAttributes(self.tan0_ctl, self.t_params)

        self.tan0_upv = primitive.addTransform(
            self.tan0_ctl, self.getName("tan0_upv"), t)
        self.tan0_upv.attr("tz").set(.01)

        t = transform.getTransformLookingAt(self.guide.apos[-2],
                                            self.guide.apos[-1],
                                            self.normal,
                                            axis=axis,
                                            negate=self.negate)
        t = transform.setMatrixPosition(t, self.guide.apos[-1])
        self.ik_cns = primitive.addTransform(
            self.root, self.getName("ik_cns"), t)
        self.tip_npo = primitive.addTransform(
            self.ik_cns, self.getName("tip_npo"), t)

        self.tip_ctl = self.addCtl(self.tip_npo,
                                   "tip_ctl",
                                   t,
                                   self.color_ik,
                                   "square",
                                   w=.3,
                                   tp=self.base_ctl)

        attribute.setKeyableAttributes(self.tip_ctl, self.tr_params)

        self.tip_upv = primitive.addTransform(
            self.tip_ctl, self.getName("tip_upv"), t)
        self.tip_upv.attr("tz").set(.01)

        # tangent 1

        vec_pos = self.guide.pos["tan1"]
        t = transform.setMatrixPosition(t, vec_pos)

        self.tan1_npo = primitive.addTransform(
            self.tip_ctl, self.getName("tan1_npo"), t)

        self.tan1_ctl = self.addCtl(
            self.tan1_npo,
            "tan1_ctl",
            t,
            self.color_ik,
            "sphere",
            w=.4,
            tp=self.tip_ctl
        )

        attribute.setKeyableAttributes(self.tan1_ctl, self.t_params)

        self.tan1_upv = primitive.addTransform(
            self.tan1_ctl, self.getName("tan1_upv"), t)
        self.tan1_upv.attr("tz").set(.01)

        attribute.setInvertMirror(self.base_ctl, ["ty"])
        attribute.setInvertMirror(self.tip_ctl, ["ty"])
        attribute.setInvertMirror(self.tan0_ctl, ["ty"])
        attribute.setInvertMirror(self.tan1_ctl, ["ty"])

        # Curves -------------------------------------------
        self.mst_crv = curve.addCnsCurve(
            self.root,
            self.getName("mst_crv"),
            [self.base_ctl, self.tan0_ctl, self.tan1_ctl, self.tip_ctl],
            3)
        self.upv_crv = curve.addCnsCurve(
            self.root,
            self.getName("upv_crv"),
            [self.base_upv, self.tan0_upv, self.tan1_upv, self.tip_upv],
            3)

        self.mst_crv.setAttr("visibility", False)
        self.upv_crv.setAttr("visibility", False)

        # Divisions
        self.div_cns = []
        self.upv_cns = []

        tagP = self.parentCtlTag
        self.extratweak_ctl = []

        for i in range(self.settings["div"]):
            # References
            div_cns = primitive.addTransform(self.root,
                                             self.getName("%s_cns" % i))

            pm.setAttr(div_cns + ".inheritsTransform", False)
            self.div_cns.append(div_cns)

            upv_cns = primitive.addTransform(self.root,
                                             self.getName("%s_upv" % i))

            pm.setAttr(upv_cns + ".inheritsTransform", False)
            self.upv_cns.append(upv_cns)

            t = transform.getTransform(div_cns)
            tweak_ctl = self.addCtl(div_cns,
                                    "extraTweak%s_ctl" % i,
                                    t,
                                    self.color_fk,
                                    "square",
                                    w=self.size * .08,
                                    d=self.size * .08,
                                    ro=datatypes.Vector([0, 0, 1.5708]),
                                    tp=tagP)
            attribute.setKeyableAttributes(tweak_ctl)

            tagP = tweak_ctl
            self.extratweak_ctl.append(tweak_ctl)
            self.jnt_pos.append([tweak_ctl, i, None, False])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        self.ctlVis_att = self.addAnimParam("ctl_vis",
                                            "ctl vis",
                                            "bool",
                                            True)

        self.tweakVis_att = self.addAnimParam(
            "Tweak_vis", "Tweak Vis", "bool", False)

        # Ref
        if self.settings["ikrefarray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["ikrefarray"].split(","))
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam(
                    "ikref",
                    "Ik Ref",
                    0,
                    ref_names)

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        dm_node_scl = node.createDecomposeMatrixNode(self.root.worldMatrix)

        step = 1.000 / (self.settings["div"] - 1)
        u = 0.000
        for i in range(self.settings["div"]):
            applyop.pathCns(self.upv_cns[i],
                            self.upv_crv,
                            cnsType=False,
                            u=u,
                            tangent=False)

            cns = applyop.pathCns(
                self.div_cns[i], self.mst_crv, False, u, True)

            # Connectiong the scale for scaling compensation
            for axis, AX in zip("xyz", "XYZ"):
                pm.connectAttr(dm_node_scl.attr("outputScale{}".format(AX)),
                               self.div_cns[i].attr("s{}".format(axis)))

            cns.setAttr("worldUpType", 1)
            cns.setAttr("frontAxis", 0)
            cns.setAttr("upAxis", 1)

            pm.connectAttr(self.upv_cns[i].attr("worldMatrix[0]"),
                           cns.attr("worldUpMatrix"))
            u += step

        for ctl in [self.base_ctl, self.tan0_ctl, self.tan1_ctl, self.tip_ctl]:
            for shp in ctl.getShapes():
                pm.connectAttr(self.ctlVis_att, shp.attr("visibility"))

        for tweak_ctl in self.extratweak_ctl:
            for shp in tweak_ctl.getShapes():
                pm.connectAttr(self.tweakVis_att, shp.attr("visibility"))

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.base_ctl
        self.relatives["tip"] = self.tip_ctl

        self.controlRelatives["root"] = self.base_ctl
        self.controlRelatives["tip"] = self.tip_ctl

        for i in range(0, len(self.div_cns) - 1):
            self.relatives["%s_loc" % i] = self.div_cns[i + 1]
            self.jointRelatives["%s_loc" % i] = i + 1

        self.relatives["%s_loc" % (len(self.div_cns) - 1)] = self.div_cns[-1]

        dlen = len(self.div_cns) - 1
        self.jointRelatives["%s_loc" % (len(self.div_cns) - 1)] = dlen

    def connect_standard(self):
        """standard connection definition for the component"""
        self.connect_standardWithSimpleIkRef()
