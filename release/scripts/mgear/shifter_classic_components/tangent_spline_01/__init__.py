
import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import node, applyop, curve
from mgear.core import attribute, transform, primitive, icon

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

        self.WIP = self.options["mode"]
        boxMult = .3
        sphereMult = .1
        self.curv_pos = []
        self.upv_curv_lvl = []

        self.normal = self.guide.blades["blade"].z * -1
        self.binormal = self.guide.blades["blade"].x

        t = transform.getTransformLookingAt(
            self.guide.apos[0],
            self.guide.apos[1],
            self.guide.blades["blade"].z * -1,
            "yx",
            self.negate)
        self.root_npo = primitive.addTransform(self.root,
                                               self.getName("root_npo"),
                                               t)
        self.root_ctl = self.addCtl(self.root_npo,
                                    "root_ctl",
                                    t,
                                    self.color_fk,
                                    "cube",
                                    w=self.size * boxMult,
                                    h=self.size * boxMult,
                                    d=self.size * boxMult,
                                    tp=self.parentCtlTag)
        attribute.setKeyableAttributes(self.root_ctl, self.r_params)

        upv_curv_lvl = primitive.addTransform(
            self.root_ctl, self.getName("root_lvl"), t)
        upv_curv_lvl.attr("tx").set(.01)
        self.curv_pos.append(self.root_ctl)
        self.upv_curv_lvl.append(upv_curv_lvl)

        t = transform.getTransformFromPos(self.guide.pos["tan0"])
        self.tan0_npo = primitive.addTransform(self.root_ctl,
                                               self.getName("tan0_npo"),
                                               t)

        self.tan0_ctl = self.addCtl(self.tan0_npo,
                                    "tan0_ctl",
                                    t,
                                    self.color_ik,
                                    "sphere",
                                    w=self.size * sphereMult,
                                    h=self.size * sphereMult,
                                    d=self.size * sphereMult,
                                    tp=self.root_ctl)
        attribute.setKeyableAttributes(self.tan0_ctl, self.t_params)
        upv_curv_lvl = primitive.addTransform(
            self.tan0_ctl, self.getName("tan0_lvl"), t)
        upv_curv_lvl.attr("tx").set(.01)
        self.curv_pos.append(self.tan0_ctl)
        self.upv_curv_lvl.append(upv_curv_lvl)

        t = transform.getTransformFromPos(self.guide.pos["tip"])
        self.tip_npo = primitive.addTransform(self.root_ctl,
                                              self.getName("tip_npo"),
                                              t)
        self.tip_ctl = self.addCtl(self.tip_npo,
                                   "tip_ctl",
                                   t,
                                   self.color_fk,
                                   "cube",
                                   w=self.size * boxMult,
                                   h=self.size * boxMult,
                                   d=self.size * boxMult,
                                   tp=self.root_ctl)

        t = transform.getTransformFromPos(self.guide.pos["tan1"])
        self.tan1_npo = primitive.addTransform(self.tip_ctl,
                                               self.getName("tan1_npo"),
                                               t)
        self.tan1_ctl = self.addCtl(self.tan1_npo,
                                    "tan1_ctl",
                                    t,
                                    self.color_ik,
                                    "sphere",
                                    w=self.size * sphereMult,
                                    h=self.size * sphereMult,
                                    d=self.size * sphereMult,
                                    tp=self.tip_ctl)
        attribute.setKeyableAttributes(self.tan1_ctl, self.t_params)
        upv_curv_lvl = primitive.addTransform(
            self.tan1_ctl, self.getName("tan1_lvl"), t)
        upv_curv_lvl.attr("tx").set(.01)
        self.curv_pos.append(self.tan1_ctl)
        self.upv_curv_lvl.append(upv_curv_lvl)

        # tip after tangent 1
        t = transform.getTransformFromPos(self.guide.pos["tip"])
        upv_curv_lvl = primitive.addTransform(
            self.tip_ctl, self.getName("tip_lvl"), t)
        upv_curv_lvl.attr("tx").set(.01)
        self.curv_pos.append(self.tip_ctl)
        self.upv_curv_lvl.append(upv_curv_lvl)

        t = transform.getTransformFromPos(self.guide.pos["tan2"])
        self.tan2_npo = primitive.addTransform(self.tip_ctl,
                                               self.getName("tan2_npo"),
                                               t)
        self.tan2_ctl = self.addCtl(self.tan2_npo,
                                    "tan2_ctl",
                                    t,
                                    self.color_ik,
                                    "sphere",
                                    w=self.size * sphereMult,
                                    h=self.size * sphereMult,
                                    d=self.size * sphereMult,
                                    tp=self.tip_ctl)
        attribute.setKeyableAttributes(self.tan2_ctl, self.t_params)
        upv_curv_lvl = primitive.addTransform(
            self.tan2_ctl, self.getName("tan2_lvl"), t)
        upv_curv_lvl.attr("tx").set(.01)
        self.curv_pos.append(self.tan2_ctl)
        self.upv_curv_lvl.append(upv_curv_lvl)

        # tiptan
        t = transform.getTransformFromPos(self.guide.pos["tiptan"])
        self.tan2_npo = primitive.addTransform(self.tip_ctl,
                                               self.getName("tiptan_npo"),
                                               t)
        self.tiptan_ctl = self.addCtl(self.tan2_npo,
                                      "tiptan_ctl",
                                      t,
                                      self.color_fk,
                                      "sphere",
                                      w=self.size * sphereMult,
                                      h=self.size * sphereMult,
                                      d=self.size * sphereMult,
                                      tp=self.tip_ctl)
        attribute.setKeyableAttributes(self.tiptan_ctl, self.t_params)

        upv_curv_lvl = primitive.addTransform(
            self.tiptan_ctl, self.getName("tan2_lvl"), t)
        upv_curv_lvl.attr("tx").set(.01)
        self.curv_pos.append(self.tiptan_ctl)
        self.upv_curv_lvl.append(upv_curv_lvl)

        # Curves -------------------------------------------
        self.mst_crv = curve.addCnsCurve(self.root,
                                         self.getName("mst_crv"),
                                         self.curv_pos,
                                         3)

        self.upv_crv = curve.addCnsCurve(self.root,
                                         self.getName("upv_crv"),
                                         self.upv_curv_lvl,
                                         3)

        self.mst_crv.setAttr("visibility", False)
        self.upv_crv.setAttr("visibility", False)

        # Divisions
        self.div_cns = []
        self.upv_cns = []

        tagP = self.parentCtlTag
        self.Extra_tweak_npo = []
        self.Extra_tweak_ctl = []

        self.def_number = self.settings["jntNb"]

        for i in range(self.def_number):
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

            extraTweak_npo = primitive.addTransform(
                div_cns,
                self.getName("extraTweak{}_npo".format(str(i))),
                t)
            self.Extra_tweak_npo.append(extraTweak_npo)
            Extra_tweak_ctl = self.addCtl(extraTweak_npo,
                                          "extraTweak%s_ctl" % i,
                                          t,
                                          self.color_fk,
                                          "circle",
                                          w=self.size * .15,
                                          d=self.size * .15,
                                          ro=datatypes.Vector([0, 0, 1.5708]),
                                          tp=tagP)
            attribute.setKeyableAttributes(Extra_tweak_ctl)
            self.Extra_tweak_ctl.append(Extra_tweak_ctl)
            self.jnt_pos.append([Extra_tweak_ctl, i])

        # add visual reference
        self.line_ref_A = icon.connection_display_curve(
            self.getName("visualRefA"),
            [self.root_ctl, self.tan0_ctl])

        self.line_ref_B = icon.connection_display_curve(
            self.getName("visualRefA"),
            [self.tan1_ctl, self.tip_ctl, self.tan2_ctl, self.tiptan_ctl])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""
        self.lenght_att = self.addAnimParam("lengthMult",
                                            "Length Control",
                                            "double",
                                            1,
                                            0,
                                            1)

        self.tipSize_att = self.addAnimParam("tipSize",
                                             "Tip size",
                                             "double",
                                             1)

        self.baseSize_att = self.addAnimParam("baseSize",
                                              "Base size",
                                              "double",
                                              1)

        self.tweakVis_att = self.addAnimParam(
            "Tweak_vis", "Tweak Vis", "bool", False)

        if self.settings["rootRefArray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["rootRefArray"].split(","))
            if len(ref_names) > 1:
                ref_names.insert(0, "self")
                self.rootref_att = self.addAnimEnumParam(
                    "rootRef", "Root Ref", 0, ref_names)

        if self.settings["tipRefArray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["tipRefArray"].split(","))
            if len(ref_names) > 1:
                ref_names.insert(0, "self")
                self.tipref_att = self.addAnimEnumParam(
                    "tipRef", "Tip Ref", 0, ref_names)

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
        if self.settings["keepLength"]:
            arclen_node = pm.arclen(self.mst_crv, ch=True)
            alAttr = pm.getAttr(arclen_node + ".arcLength")

            pm.addAttr(self.mst_crv, ln="length_ratio", k=True, w=True)
            node.createDivNode(arclen_node.arcLength,
                               alAttr,
                               self.mst_crv.length_ratio)

            div_node_scl = node.createDivNode(self.mst_crv.length_ratio,
                                              dm_node_scl.outputScaleX)

        step = 1.000 / (self.def_number - 1)
        u = 0.000
        for i in range(self.def_number):
            mult_node = node.createMulNode(u, self.lenght_att)
            cnsUpv = applyop.pathCns(self.upv_cns[i],
                                     self.upv_crv,
                                     cnsType=False,
                                     u=u,
                                     tangent=False)
            pm.connectAttr(mult_node.outputX, cnsUpv.uValue)

            cns = applyop.pathCns(
                self.div_cns[i], self.mst_crv, False, u, True)
            pm.connectAttr(mult_node.outputX, cns.uValue)

            # Connectiong the scale for scaling compensation
            for axis, AX in zip("xyz", "XYZ"):
                pm.connectAttr(dm_node_scl.attr("outputScale{}".format(AX)),
                               self.div_cns[i].attr("s{}".format(axis)))

            if self.settings["keepLength"]:

                div_node2 = node.createDivNode(u, div_node_scl.outputX)

                cond_node = node.createConditionNode(div_node2.input1X,
                                                     div_node2.outputX,
                                                     4,
                                                     div_node2.input1X,
                                                     div_node2.outputX)

                # pm.connectAttr(cond_node + ".outColorR",
                #                cnsUpv + ".uValue")
                # pm.connectAttr(cond_node + ".outColorR",
                #                cns + ".uValue")
                pm.connectAttr(cond_node + ".outColorR",
                               mult_node + ".input1X", f=True)

            # Connect the scaling for self.Extra_tweak_npo
            et_npo = self.Extra_tweak_npo[i]

            base_node = node.createMulNode(self.baseSize_att,
                                           1.00000 - u,
                                           output=None)
            tip_node = node.createMulNode(self.tipSize_att,
                                          u,
                                          output=None)
            sum_node = node.createPlusMinusAverage1D(
                [base_node.outputX, tip_node.outputX])
            # print et_npo
            # pm.connectAttr(sum_node.output1D, et_npo.scaleX, f=True)
            pm.connectAttr(sum_node.output1D, et_npo.scaleY, f=True)
            pm.connectAttr(sum_node.output1D, et_npo.scaleZ, f=True)

            cns.setAttr("worldUpType", 1)
            cns.setAttr("frontAxis", 0)
            cns.setAttr("upAxis", 1)

            pm.connectAttr(self.upv_cns[i].attr("worldMatrix[0]"),
                           cns.attr("worldUpMatrix"))
            u += step

        for et in self.Extra_tweak_ctl:
            for shp in et.getShapes():
                pm.connectAttr(self.tweakVis_att, shp.attr("visibility"))

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.root_ctl
        self.relatives["tip"] = self.tip_ctl
        self.relatives["tiptan"] = self.Extra_tweak_ctl[-1]

        self.jointRelatives["root"] = 0
        self.jointRelatives["tip"] = -1
        self.jointRelatives["tiptan"] = -1

        self.controlRelatives["root"] = self.root_ctl
        self.controlRelatives["tip"] = self.tip_ctl
        self.controlRelatives["tiptan"] = self.tiptan_ctl

        self.aliasRelatives["root"] = "root"
        self.aliasRelatives["tip"] = "tip"
        self.aliasRelatives["tiptan"] = "tiptan"

    def connect_standard(self):
        """standard connection definition for the component"""

        if self.settings["rootRefArray"]:
            self.connectRef2(self.settings["rootRefArray"],
                             self.root_npo,
                             self.rootref_att,
                             [self.root],
                             False,
                             ["Self"])
        else:
            self.parent.addChild(self.root)

        if self.settings["tipRefArray"]:
            self.connectRef2(self.settings["tipRefArray"],
                             self.tip_npo,
                             self.tipref_att,
                             [self.root_ctl],
                             False,
                             ["Self"])
