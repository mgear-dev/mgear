"""Component chain FK spline 01 module"""

import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import transform, primitive, vector, curve, applyop
from mgear.core import attribute, node, icon

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

        self.normal = self.guide.blades["blade"].z * -1
        self.binormal = self.guide.blades["blade"].x

        self.WIP = self.options["mode"]

        if self.negate and self.settings["overrideNegate"]:
            self.negate = False
            self.n_factor = 1

        # FK controllers ------------------------------------
        self.fk_npo = []
        self.fk_ctl = []
        self.tweak_npo = []
        self.tweak_ctl = []
        self.curv_pos = []
        self.upv_curv_pos = []
        self.upv_curv_lvl = []
        self.tangentsCtl = []
        t = self.guide.tra["root"]

        parent = self.root
        tOld = False
        fk_ctl = None
        self.previusTag = self.parentCtlTag
        for i, t in enumerate(transform.getChainTransform(self.guide.apos,
                                                          self.normal,
                                                          self.negate)):
            self.dist = vector.getDistance(self.guide.apos[i],
                                           self.guide.apos[i + 1])
            if self.settings["neutralpose"] or not tOld:
                tnpo = t
            else:
                tnpo = transform.setMatrixPosition(
                    tOld,
                    transform.getPositionFromMatrix(t))

            fk_npo = primitive.addTransform(
                parent, self.getName("fk%s_npo" % i), tnpo)

            fk_ctl = self.addCtl(
                fk_npo,
                "fk%s_ctl" % i,
                t,
                self.color_fk,
                "cube",
                w=self.dist,
                h=self.size * .1,
                d=self.size * .1,
                po=datatypes.Vector(self.dist * .5 * self.n_factor, 0, 0),
                tp=self.previusTag)

            tweak_npo = primitive.addTransform(
                parent, self.getName("tweak%s_npo" % i), tnpo)

            self.tweak_npo.append(tweak_npo)

            tweak_ctl = self.addCtl(
                tweak_npo,
                "tweak%s_ctl" % i,
                t,
                self.color_ik,
                "cube",
                w=self.size * .15,
                h=self.size * .05,
                d=self.size * .15,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=self.previusTag)

            upv_curv_lvl = primitive.addTransform(
                tweak_ctl, self.getName("upv%s_lvl" % i), t)
            upv_curv_lvl.attr("tz").set(.01)

            self.fk_npo.append(fk_npo)
            self.fk_ctl.append(fk_ctl)
            self.tweak_ctl.append(tweak_ctl)
            self.upv_curv_lvl.append(upv_curv_lvl)
            tOld = t
            self.previusTag = fk_ctl
            parent = fk_ctl

            # TANGENTS
            tangents = []
            tangents_npo = []
            tangents_upv = []

            if not i:
                letters = "A"
            else:
                letters = "AB"

            for tang in letters:
                tang_npo = primitive.addTransform(
                    tweak_ctl,
                    self.getName("tng{}{}_npo".format(tang, str(i))),
                    t)

                tangents_npo.append(tang_npo)

                tang_ctl = self.addCtl(
                    tang_npo,
                    "tng{}{}_ctl".format(tang, str(i)),
                    t,
                    self.color_ik,
                    "square",
                    w=self.size * .07,
                    h=self.size * .07,
                    d=self.size * .07,
                    ro=datatypes.Vector([0, 0, 1.5708]),
                    tp=self.previusTag)

                upv_tang_curv_lvl = primitive.addTransform(
                    tang_ctl,
                    self.getName("tngUpv{}{}_lvl".format(tang, str(i))),
                    t)
                upv_tang_curv_lvl.attr("tz").set(.01)
                tangents_upv.append(upv_tang_curv_lvl)

                tangents.append(tang_ctl)

            tangents_npo[0].attr("tx").set(self.dist * .3333 * self.n_factor)

            # delete the first B tangent
            if not i:
                self.curv_pos.append(tweak_ctl)
                self.curv_pos.append(tangents[0])
                self.upv_curv_pos.append(upv_curv_lvl)
                self.upv_curv_pos.append(tangents_upv[0])
            else:
                self.curv_pos.append(tangents[1])
                self.curv_pos.append(tweak_ctl)
                self.curv_pos.append(tangents[0])
                self.upv_curv_pos.append(tangents_upv[1])
                self.upv_curv_pos.append(upv_curv_lvl)
                self.upv_curv_pos.append(tangents_upv[0])
                tangents_npo[1].attr("tx").set(self.dist * -.3333 * self.n_factor)

            self.tangentsCtl.extend(tangents)

            # ==========

            # self.jnt_pos.append([fk_ctl, i, None, False])

        # add end control
        tweak_npo = primitive.addTransform(
            fk_ctl, self.getName("tweakEnd_npo"), t)
        tweak_ctl = self.addCtl(
            tweak_npo,
            "tweakEnd_ctl",
            t,
            self.color_ik,
            "cube",
            w=self.size * .15,
            h=self.size * .05,
            d=self.size * .15,
            ro=datatypes.Vector([0, 0, 1.5708]),
            tp=self.previusTag)

        upv_curv_lvl = primitive.addTransform(
            tweak_ctl, self.getName("upvEnd_lvl"), t)
        upv_curv_lvl.attr("tz").set(.01)

        if self.negate:
            self.off_dist = self.dist * -1
        else:
            self.off_dist = self.dist
        tweak_npo.attr("tx").set(self.off_dist)

        self.tweak_ctl.append(tweak_ctl)
        self.upv_curv_lvl.append(upv_curv_lvl)

        # tangent END
        tang_npo = primitive.addTransform(
            tweak_ctl,
            self.getName("tngEnd{}_npo".format(tang, str(i))),
            t)

        tang_ctl = self.addCtl(
            tang_npo,
            "tngEnd{}_ctl".format(tang, str(i)),
            t,
            self.color_ik,
            "square",
            w=self.size * .07,
            h=self.size * .07,
            d=self.size * .07,
            ro=datatypes.Vector([0, 0, 1.5708]),
            tp=self.previusTag)

        upv_tang_curv_lvl = primitive.addTransform(
            tang_ctl,
            self.getName("tngUpv{}{}_lvl".format(tang, str(i))),
            t)
        upv_tang_curv_lvl.attr("tz").set(.01)
        tangents_upv.append(upv_tang_curv_lvl)

        tang_npo.attr("tx").set(self.dist * -.3333)

        self.curv_pos.append(tang_ctl)
        self.curv_pos.append(tweak_ctl)
        self.upv_curv_pos.append(tang_ctl)
        self.upv_curv_pos.append(upv_curv_lvl)

        self.tangentsCtl.append(tang_ctl)

        # add length offset control if keep length
        # This option will be added only if keep length is active
        if self.settings["keepLength"]:
            self.tweakTip_npo = primitive.addTransform(
                tweak_ctl, self.getName("tweakTip_npo"), t)
            tweak_ctl = self.addCtl(
                self.tweakTip_npo,
                "tweakTip_ctl",
                t,
                self.color_fk,
                "square",
                w=self.size * .1,
                h=self.size * .1,
                d=self.size * .1,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=self.previusTag)

            upv_curv_lvl = primitive.addTransform(
                tweak_ctl, self.getName("upvTip_lvl"), t)
            upv_curv_lvl.attr("tz").set(.01)

            # move to align with the parent
            self.tweakTip_npo.attr("tx").set(0)

            self.tweak_ctl.append(tweak_ctl)
            self.upv_curv_lvl.append(upv_curv_lvl)

            # add visual reference
            self.line_ref = icon.connection_display_curve(
                self.getName("visualRef"),
                [self.tweakTip_npo.getParent(), tweak_ctl])

        # Curves -------------------------------------------
        self.mst_crv = curve.addCnsCurve(self.root,
                                         self.getName("mst_crv"),
                                         self.curv_pos,
                                         3)

        self.slv_crv = curve.addCurve(self.root, self.getName("slv_crv"),
                                      [datatypes.Vector()] * 32,
                                      False,
                                      3)

        self.upv_crv = curve.addCnsCurve(self.root,
                                         self.getName("upv_crv"),
                                         self.upv_curv_pos,
                                         3)

        self.slv_upv_crv = curve.addCurve(self.root,
                                          self.getName("slv_upv_crv"),
                                          [datatypes.Vector()] * 32,
                                          False,
                                          3)

        self.mst_crv.setAttr("template", True)
        self.slv_crv.setAttr("visibility", False)
        self.upv_crv.setAttr("visibility", False)
        self.slv_upv_crv.setAttr("visibility", False)

        # Divisions
        self.div_cns = []
        self.upv_cns = []

        tagP = self.parentCtlTag
        self.Extra_tweak_npo = []
        self.Extra_tweak_ctl = []

        if self.settings["overrideJntNb"]:
            self.def_number = self.settings["jntNb"]
        else:
            self.def_number = len(self.guide.apos)

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
                self.getName("extraTweak{}_npo".format(tang, str(i))),
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

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""
        self.position_att = self.addAnimParam(
            "position", "Position", "double", 0, 0, 1)
        self.lenght_att = self.addAnimParam("lengthMult",
                                            "Length Control",
                                            "double",
                                            1,
                                            0,
                                            5)
        self.ikVis_att = self.addAnimParam("IK_vis",
                                           "IK vis",
                                           "bool",
                                           True)

        self.fkVis_att = self.addAnimParam("FK_vis",
                                           "FK vis",
                                           "bool",
                                           True)

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
        self.tangentsVis_att = self.addAnimParam(
            "Tangents_vis", "Tangents Vis", "bool", False)

        self.spin_att = self.addAnimParam(
            "spin", "Spin", "double", 0, -720, 720)

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """

        # Curves -------------------------------------------
        op = applyop.gear_curveslide2_op(
            self.slv_crv, self.mst_crv, 0, 1.5, .5, .5)

        pm.connectAttr(self.position_att, op + ".position")
        pm.connectAttr(self.lenght_att, op + ".maxstretch")

        op = applyop.gear_curveslide2_op(
            self.slv_upv_crv, self.upv_crv, 0, 1.5, .5, .5)

        pm.connectAttr(self.position_att, op + ".position")
        pm.connectAttr(self.lenght_att, op + ".maxstretch")

        for tang in self.tangentsCtl:
            for shp in tang.getShapes():
                pm.connectAttr(self.tangentsVis_att, shp.attr("visibility"))

        for twnpo, fkctl in zip(self.tweak_npo, self.fk_ctl):
            intMatrix = applyop.gear_intmatrix_op(
                fkctl.attr("worldMatrix"),
                fkctl.getParent().attr("worldMatrix"),
                .5)

            applyop.gear_mulmatrix_op(intMatrix.attr("output"),
                                      twnpo.attr("parentInverseMatrix[0]"),
                                      twnpo)

        dm_node_scl = node.createDecomposeMatrixNode(self.root.worldMatrix)
        if self.settings["keepLength"]:
            arclen_node = pm.arclen(self.slv_crv, ch=True)
            alAttr = pm.getAttr(arclen_node + ".arcLength")

            pm.addAttr(self.slv_crv, ln="length_ratio", k=True, w=True)
            node.createDivNode(arclen_node.arcLength,
                               alAttr,
                               self.slv_crv.length_ratio)

            div_node_scl = node.createDivNode(self.slv_crv.length_ratio,
                                              dm_node_scl.outputScaleX)

        step = 1.000 / (self.def_number - 1)
        u = 0.000
        for i in range(self.def_number):
            mult_node = node.createMulNode(u, self.lenght_att)
            cnsUpv = applyop.pathCns(self.upv_cns[i],
                                     self.slv_upv_crv,
                                     cnsType=False,
                                     u=u,
                                     tangent=False)
            pm.connectAttr(mult_node.outputX, cnsUpv.uValue)

            cns = applyop.pathCns(
                self.div_cns[i], self.slv_crv, False, u, True)
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
            pm.connectAttr(self.spin_att, et_npo + ".rz")

            base_node = node.createMulNode(self.baseSize_att, 1.00000 - u, output=None)
            tip_node = node.createMulNode(self.tipSize_att, u, output=None)
            sum_node = node.createPlusMinusAverage1D([base_node.outputX, tip_node.outputX])
            # print et_npo
            pm.connectAttr(sum_node.output1D, et_npo.scaleX, f=True)
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

        if self.settings["keepLength"]:
            # add the safty distance offset
            self.tweakTip_npo.attr("tx").set(self.off_dist)
            # connect vis line ref
            for shp in self.line_ref.getShapes():
                pm.connectAttr(self.ikVis_att, shp.attr("visibility"))

        for ctl in self.tweak_ctl:
            for shp in ctl.getShapes():
                pm.connectAttr(self.ikVis_att, shp.attr("visibility"))
        for ctl in self.fk_ctl:
            for shp in ctl.getShapes():
                pm.connectAttr(self.fkVis_att, shp.attr("visibility"))
    # =====================================================
    # CONNECTOR
    # =====================================================

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""

        self.relatives["root"] = self.fk_ctl[0]
        self.controlRelatives["root"] = self.fk_ctl[0]
        self.jointRelatives["root"] = 0
        for i in range(0, len(self.fk_ctl) - 1):
            self.relatives["%s_loc" % i] = self.fk_ctl[i + 1]
            self.controlRelatives["%s_loc" % i] = self.fk_ctl[i + 1]
            self.jointRelatives["%s_loc" % i] = i + 1
            self.aliasRelatives["%s_ctl" % i] = i + 1
        self.relatives["%s_loc" % (len(self.fk_ctl) - 1)] = self.Extra_tweak_ctl[-1]
        self.controlRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = self.fk_ctl[-1]
        self.jointRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = len(self.Extra_tweak_ctl) - 1
        # len(self.fk_ctl) - 1)] = len(self.fk_ctl) - 1
        self.aliasRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = len(self.fk_ctl) - 1
