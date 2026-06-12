"""Component Spine IK 02 module"""

import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import node, fcurve, applyop, vector, curve
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

        # Auto bend with position controls  -------------------
        if self.settings["autoBend"]:
            self.autoBendChain = primitive.add2DChain(
                self.root,
                self.getName("autoBend%s_jnt"),
                [self.guide.apos[0], self.guide.apos[1]],
                self.guide.blades["blade"].z * -1,
                False,
                True)

            for j in self.autoBendChain:
                j.drawStyle.set(2)

        # Ik Controlers ------------------------------------
        t = transform.getTransformLookingAt(
            self.guide.apos[0],
            self.guide.apos[1],
            self.guide.blades["blade"].z * -1,
            "yx",
            self.negate)

        self.ik0_npo = primitive.addTransform(
            self.root, self.getName("ik0_npo"), t)
        self.ik0_ctl = self.addCtl(self.ik0_npo,
                                   "ik0_ctl",
                                   t,
                                   self.color_ik,
                                   "compas",
                                   w=self.size,
                                   tp=self.parentCtlTag)

        attribute.setKeyableAttributes(self.ik0_ctl, self.tr_params)
        attribute.setRotOrder(self.ik0_ctl, "ZXY")
        attribute.setInvertMirror(self.ik0_ctl, ["tx", "ry", "rz"])

        # hip base joint
        # TODO: add option in setting for on/off
        if True:
            self.hip_lvl = primitive.addTransform(
                self.ik0_ctl, self.getName("hip_lvl"), t)
            self.jnt_pos.append([self.hip_lvl, "hip"])

        t = transform.setMatrixPosition(t, self.guide.apos[1])
        if self.settings["autoBend"]:
            self.autoBend_npo = primitive.addTransform(
                self.root, self.getName("spinePosition_npo"), t)

            self.autoBend_ctl = self.addCtl(self.autoBend_npo,
                                            "spinePosition_ctl",
                                            t,
                                            self.color_ik,
                                            "square",
                                            w=self.size,
                                            d=.3 * self.size,
                                            tp=self.parentCtlTag)

            attribute.setKeyableAttributes(self.autoBend_ctl,
                                           ["tx", "ty", "tz", "ry"])

            attribute.setInvertMirror(self.autoBend_ctl, ["tx", "ry"])

            self.ik1_npo = primitive.addTransform(
                self.autoBendChain[0], self.getName("ik1_npo"), t)

            self.ik1autoRot_lvl = primitive.addTransform(
                self.ik1_npo, self.getName("ik1autoRot_lvl"), t)

            self.ik1_ctl = self.addCtl(self.ik1autoRot_lvl,
                                       "ik1_ctl",
                                       t,
                                       self.color_ik,
                                       "compas",
                                       w=self.size,
                                       tp=self.autoBend_ctl)
        else:
            t = transform.setMatrixPosition(t, self.guide.apos[1])
            self.ik1_npo = primitive.addTransform(
                self.root, self.getName("ik1_npo"), t)

            self.ik1_ctl = self.addCtl(self.ik1_npo,
                                       "ik1_ctl",
                                       t,
                                       self.color_ik,
                                       "compas",
                                       w=self.size,
                                       tp=self.ik0_ctl)

        attribute.setKeyableAttributes(self.ik1_ctl, self.tr_params)
        attribute.setRotOrder(self.ik1_ctl, "ZXY")
        attribute.setInvertMirror(self.ik1_ctl, ["tx", "ry", "rz"])

        # Tangent controllers -------------------------------
        if self.settings["centralTangent"]:
            vec_pos = vector.linearlyInterpolate(self.guide.apos[0],
                                                 self.guide.apos[1],
                                                 .33)
            t = transform.setMatrixPosition(t, vec_pos)

            self.tan0_npo = primitive.addTransform(
                self.ik0_ctl, self.getName("tan0_npo"), t)

            self.tan0_off = primitive.addTransform(
                self.tan0_npo, self.getName("tan0_off"), t)

            self.tan0_ctl = self.addCtl(self.tan0_off,
                                        "tan0_ctl",
                                        t,
                                        self.color_ik,
                                        "sphere",
                                        w=self.size * .1,
                                        tp=self.ik0_ctl)

            attribute.setKeyableAttributes(self.tan0_ctl, self.t_params)
            vec_pos = vector.linearlyInterpolate(self.guide.apos[0],
                                                 self.guide.apos[1],
                                                 .66)

            t = transform.setMatrixPosition(t, vec_pos)

            self.tan1_npo = primitive.addTransform(
                self.ik1_ctl, self.getName("tan1_npo"), t)

            self.tan1_off = primitive.addTransform(
                self.tan1_npo, self.getName("tan1_off"), t)

            self.tan1_ctl = self.addCtl(self.tan1_off,
                                        "tan1_ctl",
                                        t,
                                        self.color_ik,
                                        "sphere",
                                        w=self.size * .1,
                                        tp=self.ik0_ctl)

            attribute.setKeyableAttributes(self.tan1_ctl, self.t_params)

            # Tangent mid control
            vec_pos = vector.linearlyInterpolate(self.guide.apos[0],
                                                 self.guide.apos[1],
                                                 .5)
            t = transform.setMatrixPosition(t, vec_pos)

            self.tan_npo = primitive.addTransform(
                self.tan0_npo, self.getName("tan_npo"), t)

            self.tan_ctl = self.addCtl(self.tan_npo,
                                       "tan_ctl",
                                       t,
                                       self.color_fk,
                                       "sphere",
                                       w=self.size * .2,
                                       tp=self.ik1_ctl)

            attribute.setKeyableAttributes(self.tan_ctl, self.t_params)
            attribute.setInvertMirror(self.tan_ctl, ["tx"])

        else:
            vec_pos = vector.linearlyInterpolate(self.guide.apos[0],
                                                 self.guide.apos[1],
                                                 .33)

            t = transform.setMatrixPosition(t, vec_pos)

            self.tan0_npo = primitive.addTransform(
                self.ik0_ctl, self.getName("tan0_npo"), t)

            self.tan0_ctl = self.addCtl(self.tan0_npo,
                                        "tan0_ctl",
                                        t,
                                        self.color_ik,
                                        "sphere",
                                        w=self.size * .2,
                                        tp=self.ik0_ctl)

            attribute.setKeyableAttributes(self.tan0_ctl, self.t_params)

            vec_pos = vector.linearlyInterpolate(self.guide.apos[0],
                                                 self.guide.apos[1],
                                                 .66)

            t = transform.setMatrixPosition(t, vec_pos)

            self.tan1_npo = primitive.addTransform(
                self.ik1_ctl, self.getName("tan1_npo"), t)

            self.tan1_ctl = self.addCtl(self.tan1_npo,
                                        "tan1_ctl",
                                        t,
                                        self.color_ik,
                                        "sphere",
                                        w=self.size * .2,
                                        tp=self.ik1_ctl)

            attribute.setKeyableAttributes(self.tan1_ctl, self.t_params)

        attribute.setInvertMirror(self.tan0_ctl, ["tx"])
        attribute.setInvertMirror(self.tan1_ctl, ["tx"])

        # Curves -------------------------------------------
        self.mst_crv = curve.addCnsCurve(
            self.root,
            self.getName("mst_crv"),
            [self.ik0_ctl, self.tan0_ctl, self.tan1_ctl, self.ik1_ctl],
            3)
        self.slv_crv = curve.addCurve(self.root, self.getName("slv_crv"),
                                      [datatypes.Vector()] * 10,
                                      False,
                                      3)
        self.mst_crv.setAttr("visibility", False)
        self.slv_crv.setAttr("visibility", False)

        # Division -----------------------------------------
        # The user only define how many intermediate division he wants.
        # First and last divisions are an obligation.
        parentdiv = self.root
        parentctl = self.root
        self.div_cns = []
        self.fk_ctl = []
        self.fk_npo = []
        self.scl_transforms = []
        self.twister = []
        self.ref_twist = []

        t = transform.getTransformLookingAt(
            self.guide.apos[0],
            self.guide.apos[1],
            self.guide.blades["blade"].z * -1,
            "yx",
            self.negate)

        parent_twistRef = primitive.addTransform(
            self.root,
            self.getName("reference"),
            transform.getTransform(self.root))

        self.jointList = []
        self.preiviousCtlTag = self.parentCtlTag
        for i in range(self.settings["division"]):

            # References
            div_cns = primitive.addTransform(parentdiv,
                                             self.getName("%s_cns" % i))
            pm.setAttr(div_cns + ".inheritsTransform", False)
            self.div_cns.append(div_cns)
            parentdiv = div_cns

            # Controlers (First and last one are fake)
            # if i in [0]:
            # TODO: add option setting to add or not the first and
            #  last controller for the fk
            if i in [0, self.settings["division"] - 1] and False:
                # if i in [0, self.settings["division"] - 1]:
                fk_ctl = primitive.addTransform(
                    parentctl,
                    self.getName("%s_loc" % i),
                    transform.getTransform(parentctl))

                fk_npo = fk_ctl
                if i in [self.settings["division"] - 1]:
                    self.fk_ctl.append(fk_ctl)
            else:
                fk_npo = primitive.addTransform(
                    parentctl,
                    self.getName("fk%s_npo" % (i)),
                    transform.getTransform(parentctl))

                fk_ctl = self.addCtl(fk_npo,
                                     "fk%s_ctl" % (i),
                                     transform.getTransform(parentctl),
                                     self.color_fk,
                                     "cube",
                                     w=self.size,
                                     h=self.size * .05,
                                     d=self.size,
                                     tp=self.preiviousCtlTag)

                self.fk_ctl.append(fk_ctl)
                self.preiviousCtlTag = fk_ctl

            for x in self.fk_ctl:
                attribute.setKeyableAttributes(x)
                attribute.setRotOrder(x, "ZXY")
                attribute.setInvertMirror(x, ["tx", "rz", "ry"])

            self.fk_npo.append(fk_npo)
            parentctl = fk_ctl
            scl_ref = primitive.addTransform(parentctl,
                                             self.getName("%s_scl_ref" % i),
                                             transform.getTransform(parentctl))

            self.scl_transforms.append(scl_ref)

            # Deformers (Shadow)
            self.jnt_pos.append([scl_ref, i])

            # Twist references (This objects will replace the spinlookup
            # slerp solver behavior)
            t = transform.getTransformLookingAt(
                self.guide.apos[0],
                self.guide.apos[1],
                self.guide.blades["blade"].z * -1,
                "yx",
                self.negate)

            twister = primitive.addTransform(
                parent_twistRef, self.getName("%s_rot_ref" % i), t)

            ref_twist = primitive.addTransform(
                parent_twistRef, self.getName("%s_pos_ref" % i), t)

            ref_twist.setTranslation(
                datatypes.Vector(1.0, 0, 0), space="preTransform")

            self.twister.append(twister)
            self.ref_twist.append(ref_twist)

        # Connections (Hooks) ------------------------------
        self.cnx0 = primitive.addTransform(self.root, self.getName("0_cnx"))
        self.cnx1 = primitive.addTransform(self.root, self.getName("1_cnx"))

    def addAttributes(self):

        # Anim -------------------------------------------
        self.position_att = self.addAnimParam(
            "position", "Position", "double", self.settings["position"], 0, 1)

        self.maxstretch_att = self.addAnimParam("maxstretch",
                                                "Max Stretch",
                                                "double",
                                                self.settings["maxstretch"],
                                                1)

        self.maxsquash_att = self.addAnimParam("maxsquash",
                                               "Max Squash",
                                               "double",
                                               self.settings["maxsquash"],
                                               0,
                                               1)

        self.softness_att = self.addAnimParam(
            "softness", "Softness", "double", self.settings["softness"], 0, 1)

        self.lock_ori0_att = self.addAnimParam("lock_ori0",
                                               "Lock Ori 0",
                                               "double",
                                               self.settings["lock_ori"],
                                               0,
                                               1)

        self.lock_ori1_att = self.addAnimParam("lock_ori1",
                                               "Lock Ori 1",
                                               "double",
                                               self.settings["lock_ori"],
                                               0,
                                               1)

        self.tan0_att = self.addAnimParam("tan0", "Tangent 0", "double", 1, 0)
        self.tan1_att = self.addAnimParam("tan1", "Tangent 1", "double", 1, 0)

        # Volume
        self.volume_att = self.addAnimParam(
            "volume", "Volume", "double", 1, 0, 1)

        if self.settings["autoBend"]:
            self.sideBend_att = self.addAnimParam(
                "sideBend", "Side Bend", "double", .5, 0, 2)

            self.frontBend_att = self.addAnimParam(
                "frontBend", "Front Bend", "double", .5, 0, 2)

        # Setup ------------------------------------------
        # Eval Fcurve
        if self.guide.paramDefs["st_profile"].value:
            self.st_value = self.guide.paramDefs["st_profile"].value
            self.sq_value = self.guide.paramDefs["sq_profile"].value
        else:
            self.st_value = fcurve.getFCurveValues(self.settings["st_profile"],
                                                   self.divisions)
            self.sq_value = fcurve.getFCurveValues(self.settings["sq_profile"],
                                                   self.divisions)

        self.st_att = [self.addSetupParam("stretch_%s" % i,
                                          "Stretch %s" % i,
                                          "double",
                                          self.st_value[i],
                                          -1,
                                          0)
                       for i in range(self.settings["division"])]

        self.sq_att = [self.addSetupParam("squash_%s" % i,
                                          "Squash %s" % i,
                                          "double",
                                          self.sq_value[i],
                                          0,
                                          1)
                       for i in range(self.settings["division"])]

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """

        # Auto bend ----------------------------
        if self.settings["autoBend"]:
            mul_node = node.createMulNode(
                [self.autoBendChain[0].ry, self.autoBendChain[0].rz],
                [self.sideBend_att, self.frontBend_att])

            mul_node.outputX >> self.ik1autoRot_lvl.rz
            mul_node.outputY >> self.ik1autoRot_lvl.rx

            self.ikHandleAutoBend = primitive.addIkHandle(
                self.autoBend_ctl,
                self.getName("ikHandleAutoBend"),
                self.autoBendChain,
                "ikSCsolver")

        # Tangent position ---------------------------------
        # common part
        d = vector.getDistance(self.guide.apos[0], self.guide.apos[1])
        dist_node = node.createDistNode(self.ik0_ctl, self.ik1_ctl)
        rootWorld_node = node.createDecomposeMatrixNode(
            self.root.attr("worldMatrix"))

        div_node = node.createDivNode(dist_node + ".distance",
                                      rootWorld_node + ".outputScaleX")

        div_node = node.createDivNode(div_node + ".outputX", d)

        # tan0
        mul_node = node.createMulNode(self.tan0_att,
                                      self.tan0_npo.getAttr("ty"))

        res_node = node.createMulNode(mul_node + ".outputX",
                                      div_node + ".outputX")

        pm.connectAttr(res_node + ".outputX", self.tan0_npo.attr("ty"))

        # tan1
        mul_node = node.createMulNode(self.tan1_att,
                                      self.tan1_npo.getAttr("ty"))

        res_node = node.createMulNode(mul_node + ".outputX",
                                      div_node + ".outputX")

        pm.connectAttr(res_node + ".outputX", self.tan1_npo.attr("ty"))

        # Tangent Mid --------------------------------------
        if self.settings["centralTangent"]:
            tanIntMat = applyop.gear_intmatrix_op(
                self.tan0_npo.attr("worldMatrix"),
                self.tan1_npo.attr("worldMatrix"),
                .5)

            applyop.gear_mulmatrix_op(
                tanIntMat.attr("output"),
                self.tan_npo.attr("parentInverseMatrix[0]"),
                self.tan_npo)

            pm.connectAttr(self.tan_ctl.attr("translate"),
                           self.tan0_off.attr("translate"))

            pm.connectAttr(self.tan_ctl.attr("translate"),
                           self.tan1_off.attr("translate"))

        # Curves -------------------------------------------
        op = applyop.gear_curveslide2_op(
            self.slv_crv, self.mst_crv, 0, 1.5, .5, .5)

        pm.connectAttr(self.position_att, op + ".position")
        pm.connectAttr(self.maxstretch_att, op + ".maxstretch")
        pm.connectAttr(self.maxsquash_att, op + ".maxsquash")
        pm.connectAttr(self.softness_att, op + ".softness")

        # Volume driver ------------------------------------
        crv_node = node.createCurveInfoNode(self.slv_crv)

        # Division -----------------------------------------
        for i in range(self.settings["division"]):

            # References
            u = i / (self.settings["division"] - 1.0)
            if i == 0:  # we add extra 10% to the first vertebra
                u = (1.0 / (self.settings["division"] - 1.0)) / 10

            cns = applyop.pathCns(
                self.div_cns[i], self.slv_crv, False, u, True)

            cns.setAttr("frontAxis", 1)  # front axis is 'Y'
            cns.setAttr("upAxis", 0)  # front axis is 'X'

            # Roll
            intMatrix = applyop.gear_intmatrix_op(
                self.ik0_ctl + ".worldMatrix",
                self.ik1_ctl + ".worldMatrix",
                u)

            dm_node = node.createDecomposeMatrixNode(intMatrix + ".output")
            pm.connectAttr(dm_node + ".outputRotate",
                           self.twister[i].attr("rotate"))

            pm.parentConstraint(self.twister[i],
                                self.ref_twist[i],
                                maintainOffset=True)

            pm.connectAttr(self.ref_twist[i] + ".translate",
                           cns + ".worldUpVector")

            # compensate scale reference
            div_node = node.createDivNode([1, 1, 1],
                                          [rootWorld_node + ".outputScaleX",
                                           rootWorld_node + ".outputScaleY",
                                           rootWorld_node + ".outputScaleZ"])

            # Squash n Stretch
            op = applyop.gear_squashstretch2_op(self.scl_transforms[i],
                                                self.root,
                                                pm.arclen(self.slv_crv),
                                                "y",
                                                div_node + ".output")

            pm.connectAttr(self.volume_att, op + ".blend")
            pm.connectAttr(crv_node + ".arcLength", op + ".driver")
            pm.connectAttr(self.st_att[i], op + ".stretch")
            pm.connectAttr(self.sq_att[i], op + ".squash")

            # Controlers
            if i == 0:
                mulmat_node = applyop.gear_mulmatrix_op(
                    self.div_cns[i].attr("worldMatrix"),
                    self.root.attr("worldInverseMatrix"))

                dm_node = node.createDecomposeMatrixNode(
                    mulmat_node + ".output")

                pm.connectAttr(dm_node + ".outputTranslate",
                               self.fk_npo[i].attr("t"))

            else:
                mulmat_node = applyop.gear_mulmatrix_op(
                    self.div_cns[i].attr("worldMatrix"),
                    self.div_cns[i - 1].attr("worldInverseMatrix"))

                dm_node = node.createDecomposeMatrixNode(
                    mulmat_node + ".output")

                mul_node = node.createMulNode(div_node + ".output",
                                              dm_node + ".outputTranslate")

                pm.connectAttr(mul_node + ".output", self.fk_npo[i].attr("t"))

            pm.connectAttr(dm_node + ".outputRotate", self.fk_npo[i].attr("r"))

            # Orientation Lock
            if i == 0:
                dm_node = node.createDecomposeMatrixNode(
                    self.ik0_ctl + ".worldMatrix")

                blend_node = node.createBlendNode(
                    [dm_node + ".outputRotate%s" % s for s in "XYZ"],
                    [cns + ".rotate%s" % s for s in "XYZ"],
                    self.lock_ori0_att)

                self.div_cns[i].attr("rotate").disconnect()

                pm.connectAttr(blend_node + ".output",
                               self.div_cns[i] + ".rotate")

            elif i == self.settings["division"] - 1:
                dm_node = node.createDecomposeMatrixNode(
                    self.ik1_ctl + ".worldMatrix")

                blend_node = node.createBlendNode(
                    [dm_node + ".outputRotate%s" % s for s in "XYZ"],
                    [cns + ".rotate%s" % s for s in "XYZ"],
                    self.lock_ori1_att)

                self.div_cns[i].attr("rotate").disconnect()
                pm.connectAttr(blend_node + ".output",
                               self.div_cns[i] + ".rotate")

        # Connections (Hooks) ------------------------------
        pm.parentConstraint(self.hip_lvl, self.cnx0)
        pm.scaleConstraint(self.hip_lvl, self.cnx0)
        pm.parentConstraint(self.scl_transforms[-1], self.cnx1)
        pm.scaleConstraint(self.scl_transforms[-1], self.cnx1)

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.cnx0
        self.relatives["eff"] = self.cnx1

        self.controlRelatives["root"] = self.fk_ctl[0]
        self.controlRelatives["eff"] = self.fk_ctl[-2]

        self.jointRelatives["root"] = 0
        self.jointRelatives["eff"] = -1

        self.aliasRelatives["root"] = "base"
        self.aliasRelatives["eff"] = "tip"
