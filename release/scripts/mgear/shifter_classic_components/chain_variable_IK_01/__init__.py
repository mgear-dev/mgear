
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

        # FK controllers ------------------------------------
        self.crv_lvl = []
        self.ik_ctl = []
        self.upv_curv_lvl = []
        t = self.guide.tra["root"]

        parent = self.root
        tOld = False
        self.previusTag = self.parentCtlTag
        for i, t in enumerate(transform.getChainTransform(self.guide.apos,
                                                          self.normal,
                                                          self.negate)):
            self.dist = vector.getDistance(self.guide.apos[i],
                                           self.guide.apos[i + 1])
            if not tOld:
                tnpo = t
            else:
                tnpo = transform.setMatrixPosition(
                    tOld,
                    transform.getPositionFromMatrix(t))

            crv_lvl = primitive.addTransform(
                parent, self.getName("crv%s_lvl" % i), tnpo)
            upv_curv_lvl = primitive.addTransform(
                crv_lvl, self.getName("upv%s_lvl" % i), t)
            upv_curv_lvl.attr("tz").set(.01)

            self.crv_lvl.append(crv_lvl)
            self.upv_curv_lvl.append(upv_curv_lvl)
            tOld = t
            parent = crv_lvl

        # add crv end anchor
        t = self.guide.atra[-1]
        crvEnd_lvl = primitive.addTransform(
            crv_lvl, self.getName("crvEnd_lvl"), t)

        upv_curv_lvl = primitive.addTransform(
            crvEnd_lvl, self.getName("upvcrvEnd_lvl"), t)
        upv_curv_lvl.attr("tz").set(.01)

        self.crv_points = self.crv_lvl + [crvEnd_lvl]
        self.upv_curv_lvl.append(upv_curv_lvl)

        if self.negate:
            self.off_dist = self.dist * -1
        else:
            self.off_dist = self.dist

        # IK controls
        tagP = self.parentCtlTag
        self.ik_upv_cns = []
        self.ik_npo_cns = []
        self.ik_upv_lvl = []
        self.ik_number = self.settings["ikNb"]
        for i in range(self.ik_number):
            # References
            ik_npo_cns = primitive.addTransform(self.root,
                                                self.getName("ik%s_cns" % i))

            pm.setAttr(ik_npo_cns + ".inheritsTransform", False)
            self.ik_npo_cns.append(ik_npo_cns)

            ik_upv_cns = primitive.addTransform(self.root,
                                                self.getName("ik%s_upv" % i))

            pm.setAttr(ik_upv_cns + ".inheritsTransform", False)
            self.ik_upv_cns.append(ik_upv_cns)

            t = transform.getTransform(ik_npo_cns)
            ik_ctl = self.addCtl(
                ik_npo_cns,
                "ik%s_ctl" % i,
                t,
                self.color_ik,
                "square",
                w=self.size * .15,
                h=self.size * .15,
                d=self.size * .15,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=tagP)

            attribute.setKeyableAttributes(ik_ctl)

            tagP = ik_ctl
            self.ik_ctl.append(ik_ctl)

            ik_upv_lvl = primitive.addTransform(
                ik_ctl, self.getName("ik%s_lvl" % i), t)
            ik_upv_lvl.attr("tz").set(.01)
            self.ik_upv_lvl.append(ik_upv_lvl)

        # add length offset control if keep length
        # This option will be added only if keep length is active
        if self.settings["keepLength"]:
            self.ikTip_npo = primitive.addTransform(
                ik_ctl, self.getName("ikTip_npo"), t)
            ik_ctl = self.addCtl(
                self.ikTip_npo,
                "ikTip_ctl",
                t,
                self.color_fk,
                "square",
                w=self.size * .1,
                h=self.size * .1,
                d=self.size * .1,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=tagP)

            ik_upv_lvl = primitive.addTransform(
                ik_ctl, self.getName("ikTip_lvl"), t)
            ik_upv_lvl.attr("tz").set(.01)

            # move to align with the parent
            # we will offset later, so we cheat the space for keep lenght
            self.ikTip_npo.attr("tx").set(0)

            self.ik_ctl.append(ik_ctl)
            self.ik_upv_lvl.append(ik_upv_lvl)

            # add visual reference
            self.line_ref = icon.connection_display_curve(
                self.getName("visualRef"),
                [self.ikTip_npo.getParent(), ik_ctl])

        # set keyable attr for tweak controls
        [attribute.setKeyableAttributes(i_ctl, ["tx", "ty", "tz", "rx"])
            for i_ctl in self.ik_ctl]

        # Curves -------------------------------------------
        self.mst_crv = curve.addCnsCurve(self.root,
                                         self.getName("mst_crv"),
                                         self.crv_points,
                                         3)

        self.upv_crv = curve.addCnsCurve(self.root,
                                         self.getName("upv_crv"),
                                         self.upv_curv_lvl,
                                         3)

        self.mst_crv.setAttr("visibility", False)
        self.upv_crv.setAttr("visibility", False)

        self.mstIK_crv = curve.addCnsCurve(self.root,
                                           self.getName("mstIK_crv"),
                                           self.ik_ctl[:],
                                           3)

        self.upvIK_crv = curve.addCnsCurve(self.root,
                                           self.getName("upvIK_crv"),
                                           self.ik_upv_lvl,
                                           3)

        self.mstIK_crv.setAttr("visibility", False)
        self.upvIK_crv.setAttr("visibility", False)

        # Divisions
        self.div_cns = []
        self.upv_cns = []

        if self.settings["overrideJntNb"]:
            self.def_number = self.settings["jntNb"]
        else:
            self.def_number = len(self.guide.apos)

        if self.settings["extraTweak"]:
            tagP = self.parentCtlTag
            self.extratweak_ctl = []

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

            if self.settings["extraTweak"]:
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
            else:
                self.jnt_pos.append([div_cns, i])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""
        self.ikVis_att = self.addAnimParam("IK_vis",
                                           "IK vis",
                                           "bool",
                                           True)

        if self.settings["keepLength"]:
            self.length_ratio_att = self.addAnimParam("length_ratio",
                                                      "Length Ratio",
                                                      "double",
                                                      1,
                                                      0.0001,
                                                      10)
        if self.settings["extraTweak"]:
            self.tweakVis_att = self.addAnimParam(
                "Tweak_vis", "Tweak Vis", "bool", False)

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

        # IK controls
        if self.ik_number > 1:
            div_val = self.ik_number - 1
        else:
            div_val = 1
        step = 0.998 / div_val
        u = 0.001

        for i in range(self.ik_number):
            cnsUpv = applyop.pathCns(self.ik_upv_cns[i],
                                     self.upv_crv,
                                     cnsType=False,
                                     u=u,
                                     tangent=False)

            cns = applyop.pathCns(
                self.ik_npo_cns[i], self.mst_crv, False, u, True)

            # Connectiong the scale for scaling compensation
            for axis, AX in zip("xyz", "XYZ"):
                pm.connectAttr(dm_node_scl.attr("outputScale{}".format(AX)),
                               self.ik_npo_cns[i].attr("s{}".format(axis)))

            cns.setAttr("worldUpType", 1)
            cns.setAttr("frontAxis", 0)
            cns.setAttr("upAxis", 1)

            pm.connectAttr(self.ik_upv_cns[i].attr("worldMatrix[0]"),
                           cns.attr("worldUpMatrix"))
            u += step

        # Divisions
        if self.settings["keepLength"]:
            arclen_node = pm.arclen(self.mstIK_crv, ch=True)
            alAttr = pm.getAttr(arclen_node + ".arcLength")
            ration_node = node.createMulNode(self.length_ratio_att,
                                             alAttr)

            pm.addAttr(self.mstIK_crv, ln="length_ratio", k=True, w=True)
            node.createDivNode(arclen_node.arcLength,
                               ration_node.outputX,
                               self.mstIK_crv.length_ratio)

            div_node_scl = node.createDivNode(self.mstIK_crv.length_ratio,
                                              dm_node_scl.outputScaleX)

        if self.def_number > 1:
            div_val = self.def_number - 1
        else:
            div_val = 1
        step = 0.998 / div_val
        u = 0.001

        for i in range(self.def_number):
            cnsUpv = applyop.pathCns(self.upv_cns[i],
                                     self.upvIK_crv,
                                     cnsType=False,
                                     u=u,
                                     tangent=False)

            cns = applyop.pathCns(
                self.div_cns[i], self.mstIK_crv, False, u, True)

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

                pm.connectAttr(cond_node + ".outColorR",
                               cnsUpv + ".uValue")
                pm.connectAttr(cond_node + ".outColorR",
                               cns + ".uValue")

            cns.setAttr("worldUpType", 1)
            cns.setAttr("frontAxis", 0)
            cns.setAttr("upAxis", 1)

            pm.connectAttr(self.upv_cns[i].attr("worldMatrix[0]"),
                           cns.attr("worldUpMatrix"))
            u += step

        if self.settings["keepLength"]:
            # add the safty distance offset
            self.ikTip_npo.attr("tx").set(self.off_dist)
            # connect vis line ref
            for shp in self.line_ref.getShapes():
                pm.connectAttr(self.ikVis_att, shp.attr("visibility"))

        for ctl in self.ik_ctl:
            for shp in ctl.getShapes():
                pm.connectAttr(self.ikVis_att, shp.attr("visibility"))

        if self.settings["extraTweak"]:
            for tweak_ctl in self.extratweak_ctl:
                for shp in tweak_ctl.getShapes():
                    pm.connectAttr(self.tweakVis_att, shp.attr("visibility"))

    # =====================================================
    # CONNECTOR
    # =====================================================

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""

        self.relatives["root"] = self.ik_ctl[0]
        self.controlRelatives["root"] = self.ik_ctl[0]
        self.jointRelatives["root"] = 0
        for i in range(0, len(self.guide.apos) - 1):
            self.relatives["%s_loc" % i] = self.ik_ctl[-1]
            self.controlRelatives["%s_loc" % i] = self.ik_ctl[-1]
            self.jointRelatives["%s_loc" % i] = i + 1
            self.aliasRelatives["%s_ctl" % i] = i + 1
        self.relatives["%s_loc" % (len(self.guide.apos) - 1)] = self.ik_ctl[-1]
        self.controlRelatives["%s_loc" % (
            len(self.guide.apos) - 1)] = self.ik_ctl[-1]
        self.jointRelatives["%s_loc" % (
            len(self.guide.apos) - 1)] = len(self.guide.apos) - 1
        self.aliasRelatives["%s_loc" % (
            len(self.guide.apos) - 1)] = len(self.guide.apos) - 1
