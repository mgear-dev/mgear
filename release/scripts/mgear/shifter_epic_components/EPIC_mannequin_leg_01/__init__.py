import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import node, fcurve, applyop, vector, icon
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

        self.WIP = self.options["mode"]
        self.up_axis = pm.upAxis(q=True, axis=True)

        self.normal = self.getNormalFromPos(self.guide.apos)

        self.length0 = vector.getDistance(
            self.guide.apos[0], self.guide.apos[1]
        )
        self.length1 = vector.getDistance(
            self.guide.apos[1], self.guide.apos[2]
        )
        self.length2 = vector.getDistance(
            self.guide.apos[2], self.guide.apos[3]
        )

        # 1 bone chain for upv ref
        self.legChainUpvRef = primitive.add2DChain(
            self.root,
            self.getName("legUpvRef%s_jnt"),
            [self.guide.apos[0], self.guide.apos[2]],
            self.normal,
            False,
            self.WIP,
        )

        self.legChainUpvRef[1].setAttr(
            "jointOrientZ", self.legChainUpvRef[1].getAttr("jointOrientZ") * -1
        )

        # extra neutral pose
        t = transform.getTransformFromPos(self.guide.apos[0])

        self.root_npo = primitive.addTransform(
            self.root, self.getName("root_npo"), t
        )
        self.root_ctl = self.addCtl(
            self.root_npo,
            "root_ctl",
            t,
            self.color_fk,
            "circle",
            w=self.length0 / 6,
            tp=self.parentCtlTag,
        )

        # FK Controlers -----------------------------------
        t = transform.getTransformLookingAt(
            self.guide.apos[0],
            self.guide.apos[1],
            self.normal,
            "xz",
            self.negate,
        )
        if self.settings["FK_rest_T_Pose"]:
            if self.negate:
                x_dir = 1
            else:
                x_dir = -1

            if self.up_axis == "y":
                x = datatypes.Vector(0, x_dir, 0)
            else:
                x = datatypes.Vector(0, 0, x_dir)
            z = datatypes.Vector(-1, 0, 0)

            t_npo = transform.getRotationFromAxis(x, z, "xz", False)
            t_npo = transform.setMatrixPosition(t_npo, self.guide.apos[0])
        else:
            t_npo = t

        self.fk0_npo = primitive.addTransform(
            self.root_ctl, self.getName("fk0_npo"), t_npo
        )
        po_vec = datatypes.Vector(0.5 * self.length0 * self.n_factor, 0, 0)
        self.fk0_ctl = self.addCtl(
            self.fk0_npo,
            "fk0_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.length0,
            h=self.size * 0.1,
            d=self.size * 0.1,
            po=po_vec,
            tp=self.root_ctl,
        )
        attribute.setKeyableAttributes(
            self.fk0_ctl, ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx"]
        )

        t = transform.getTransformLookingAt(
            self.guide.apos[1],
            self.guide.apos[2],
            self.normal,
            "xz",
            self.negate,
        )

        if self.settings["FK_rest_T_Pose"]:
            t_npo = transform.setMatrixPosition(
                transform.getTransform(self.fk0_ctl), self.guide.apos[1]
            )
        else:
            t_npo = t

        self.fk1_npo = primitive.addTransform(
            self.fk0_ctl, self.getName("fk1_npo"), t_npo
        )

        po_vec = datatypes.Vector(0.5 * self.length1 * self.n_factor, 0, 0)
        self.fk1_ctl = self.addCtl(
            self.fk1_npo,
            "fk1_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.length1,
            h=self.size * 0.1,
            d=self.size * 0.1,
            po=po_vec,
            tp=self.fk0_ctl,
        )

        attribute.setKeyableAttributes(
            self.fk1_ctl, ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx"]
        )

        t = transform.getTransformLookingAt(
            self.guide.apos[2],
            self.guide.apos[3],
            self.normal,
            "xz",
            self.negate,
        )
        if self.settings["FK_rest_T_Pose"]:
            t_npo = transform.setMatrixPosition(
                transform.getTransform(self.fk0_ctl), self.guide.apos[2]
            )
        else:
            t_npo = t

        self.fk2_npo = primitive.addTransform(
            self.fk1_ctl, self.getName("fk2_npo"), t_npo
        )

        if self.settings["FK_rest_T_Pose"]:
            self.fk2_npo.rz.set(90)

        po_vec = datatypes.Vector(0.5 * self.length2 * self.n_factor, 0, 0)
        self.fk2_ctl = self.addCtl(
            self.fk2_npo,
            "fk2_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.length2,
            h=self.size * 0.1,
            d=self.size * 0.1,
            po=po_vec,
            tp=self.fk1_ctl,
        )
        attribute.setKeyableAttributes(self.fk2_ctl)

        self.fk_ctl = [self.fk0_ctl, self.fk1_ctl, self.fk2_ctl]

        for x in self.fk_ctl:
            attribute.setInvertMirror(x, ["tx", "ty", "tz"])

        # IK Controlers -----------------------------------

        self.ik_cns = primitive.addTransformFromPos(
            self.root_ctl, self.getName("ik_cns"), self.guide.pos["ankle"]
        )

        self.ikcns_ctl = self.addCtl(
            self.ik_cns,
            "ikcns_ctl",
            transform.getTransformFromPos(self.guide.pos["ankle"]),
            self.color_ik,
            "null",
            w=self.size * 0.12,
            tp=self.root_ctl,
        )
        attribute.setInvertMirror(self.ikcns_ctl, ["tx"])

        # m = transform.getTransformLookingAt(self.guide.pos["ankle"],
        #                                     self.guide.pos["eff"],
        #                                     self.x_axis,
        #                                     "zx",
        #                                     False)
        # if self.settings["FK_rest_T_Pose"]:
        #     t_ik = transform.getTransformLookingAt(self.guide.pos["ankle"],
        #                                            self.guide.pos["eff"],
        #                                            self.normal * -1,
        #                                            "zx",
        #                                            False)
        # else:
        t_ik = transform.getTransformFromPos(self.guide.pos["ankle"])

        self.ik_ctl = self.addCtl(
            self.ikcns_ctl,
            "ik_ctl",
            t_ik,
            self.color_ik,
            "cube",
            w=self.size * 0.12,
            h=self.size * 0.12,
            d=self.size * 0.12,
        )
        attribute.setKeyableAttributes(self.ik_ctl)
        attribute.setRotOrder(self.ik_ctl, "XZY")
        attribute.setInvertMirror(self.ik_ctl, ["tx", "ry", "rz"])

        # upv
        v = self.guide.apos[2] - self.guide.apos[0]
        v = self.normal ^ v
        v.normalize()
        v *= self.size * 0.5
        v += self.guide.apos[1]

        self.upv_cns = primitive.addTransformFromPos(
            self.ik_ctl, self.getName("upv_cns"), v
        )

        self.upv_ctl = self.addCtl(
            self.upv_cns,
            "upv_ctl",
            transform.getTransform(self.upv_cns),
            self.color_ik,
            "diamond",
            w=self.size * 0.12,
            tp=self.root_ctl,
        )

        self.add_controller_tag(self.ik_ctl, self.upv_ctl)
        if self.settings["mirrorMid"]:
            if self.negate:
                self.upv_cns.rz.set(180)
                self.upv_cns.sy.set(-1)
        else:
            attribute.setInvertMirror(self.upv_ctl, ["tx"])
        attribute.setKeyableAttributes(self.upv_ctl, self.t_params)

        # References --------------------------------------
        self.ik_ref = primitive.addTransform(
            self.ik_ctl,
            self.getName("ik_ref"),
            transform.getTransform(self.ik_ctl),
        )
        self.fk_ref = primitive.addTransform(
            self.fk_ctl[2],
            self.getName("fk_ref"),
            transform.getTransform(self.ik_ctl),
        )

        # Chain --------------------------------------------
        # The outputs of the ikfk2bone solver
        self.bone0 = primitive.addLocator(
            self.root_ctl,
            self.getName("0_bone"),
            transform.getTransform(self.fk_ctl[0]),
        )

        self.bone0_shp = self.bone0.getShape()
        self.bone0_shp.setAttr("localPositionX", self.n_factor * 0.5)
        self.bone0_shp.setAttr("localScale", 0.5, 0, 0)
        self.bone0.setAttr("sx", self.length0)
        self.bone0.setAttr("visibility", False)

        self.bone1 = primitive.addLocator(
            self.root_ctl,
            self.getName("1_bone"),
            transform.getTransform(self.fk_ctl[1]),
        )
        self.bone1_shp = self.bone1.getShape()
        self.bone1_shp.setAttr("localPositionX", self.n_factor * 0.5)
        self.bone1_shp.setAttr("localScale", 0.5, 0, 0)
        self.bone1.setAttr("sx", self.length1)
        self.bone1.setAttr("visibility", False)

        self.ctrn_loc = primitive.addTransformFromPos(
            self.root_ctl, self.getName("ctrn_loc"), self.guide.apos[1]
        )
        self.eff_loc = primitive.addTransformFromPos(
            self.root_ctl, self.getName("eff_loc"), self.guide.apos[2]
        )

        # tws_ref
        if self.up_axis == "y":
            t = transform.getRotationFromAxis(
                datatypes.Vector(0, -1, 0), self.normal, "xz", self.negate
            )
        else:
            t = transform.getRotationFromAxis(
                datatypes.Vector(0, 0, -1), self.normal, "xz", self.negate
            )
        t = transform.setMatrixPosition(t, self.guide.pos["ankle"])

        # addind an npo parent transform to fix flip in Maya 2018.2
        self.tws_npo = primitive.addTransform(
            self.eff_loc, self.getName("tws_npo"), t
        )

        self.tws_ref = primitive.addTransform(
            self.tws_npo, self.getName("tws_ref"), t
        )

        # Mid Controler ------------------------------------
        t = transform.getTransform(self.ctrn_loc)
        self.mid_cns = primitive.addTransform(
            self.ctrn_loc, self.getName("mid_cns"), t
        )
        self.mid_ctl = self.addCtl(
            self.mid_cns,
            "mid_ctl",
            t,
            self.color_ik,
            "sphere",
            w=self.size * 0.2,
            tp=self.root_ctl,
        )

        attribute.setKeyableAttributes(
            self.mid_ctl,
            params=["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx"],
        )

        if self.settings["mirrorMid"]:
            if self.negate:
                self.mid_cns.rz.set(180)
                self.mid_cns.sz.set(-1)
        else:
            attribute.setInvertMirror(self.mid_ctl, ["tx", "ty", "tz"])

        # Twist references ---------------------------------
        x = datatypes.Vector(0, -1, 0)
        x = x * transform.getTransform(self.eff_loc)
        z = datatypes.Vector(self.normal.x, self.normal.y, self.normal.z)
        z = z * transform.getTransform(self.eff_loc)

        m = transform.getRotationFromAxis(x, z, "xz", self.negate)
        m = transform.setMatrixPosition(
            m, transform.getTranslation(self.ik_ctl)
        )

        self.rollRef = primitive.add2DChain(
            self.root,
            self.getName("rollChain"),
            self.guide.apos[:2],
            self.normal,
            self.negate,
            self.WIP,
        )

        t = transform.getTransformLookingAt(
            self.guide.pos["base"],
            self.guide.apos[1],
            self.normal,
            "xz",
            self.negate,
        )
        self.tws0_loc = primitive.addTransform(
            self.root_ctl, self.getName("tws0_loc"), t
        )

        self.tws0_rot = primitive.addTransform(
            self.tws0_loc, self.getName("tws0_rot"), t
        )

        self.tws1_loc = primitive.addTransform(
            self.ctrn_loc,
            self.getName("tws1_loc"),
            transform.getTransform(self.ctrn_loc),
        )

        self.tws1_rot = primitive.addTransform(
            self.tws1_loc,
            self.getName("tws1_rot"),
            transform.getTransform(self.ctrn_loc),
        )

        self.tws2_loc = primitive.addTransform(
            self.root_ctl,
            self.getName("tws2_loc"),
            transform.getTransform(self.tws_ref),
        )

        self.tws2_rot = primitive.addTransform(
            self.tws2_loc,
            self.getName("tws2_rot"),
            transform.getTransform(self.tws_ref),
        )

        self.tws2_rot.setAttr("sx", 0.001)

        # Divisions ----------------------------------------

        self.divisions = self.settings["div0"] + self.settings["div1"] + 2

        self.div_cns = []

        if self.settings["extraTweak"]:
            tagP = self.parentCtlTag
            self.tweak_ctl = []

        for i in range(self.divisions):

            div_cns = primitive.addTransform(
                self.root_ctl, self.getName("div%s_loc" % i)
            )

            self.div_cns.append(div_cns)

            if self.settings["extraTweak"]:
                t = transform.getTransform(div_cns)
                tweak_ctl = self.addCtl(
                    div_cns,
                    "tweak%s_ctl" % i,
                    t,
                    self.color_fk,
                    "square",
                    w=self.size * 0.15,
                    d=self.size * 0.15,
                    ro=datatypes.Vector([0, 0, 1.5708]),
                    tp=tagP,
                )
                attribute.setKeyableAttributes(tweak_ctl)

                tagP = tweak_ctl
                self.tweak_ctl.append(tweak_ctl)
                driver = tweak_ctl
            else:
                driver = div_cns

            # setting the joints
            if i == 0:
                self.jnt_pos.append(
                    {
                        "obj": driver,
                        "name": "thigh",
                        "guide_relative": "root",
                        "data_contracts": "Ik",
                    }
                )
                current_parent = "root"
                twist_name = "thigh_twist_"
                twist_idx = 1
                increment = 1
            elif i == self.settings["div0"] + 1:
                self.jnt_pos.append(
                    {
                        "obj": driver,
                        "name": "calf",
                        "newActiveJnt": current_parent,
                        "guide_relative": "knee",
                        "data_contracts": "Ik",
                    }
                )
                twist_name = "calf_twist_"
                current_parent = "knee"
                twist_idx = self.settings["div1"]
                increment = -1
            else:
                self.jnt_pos.append(
                    {
                        "obj": driver,
                        "name": twist_name + str(twist_idx).zfill(2),
                        "newActiveJnt": current_parent,
                        "data_contracts": "Twist,Squash",
                    }
                )
                twist_idx += increment

        # End reference ------------------------------------
        # To help the deformation on the ankle
        self.end_ref = primitive.addTransform(
            self.tws2_rot, self.getName("end_ref"), m
        )
        # set the offset rotation for the hand
        self.end_jnt_off = primitive.addTransform(
            self.end_ref, self.getName("end_off"), m
        )
        if self.up_axis == "z":
            self.end_jnt_off.rz.set(-90)
        self.jnt_pos.append(
            {
                "obj": self.end_jnt_off,
                "name": "foot",
                "newActiveJnt": current_parent,
                "guide_relative": "ankle",
                "data_contracts": "Ik",
            }
        )

        # match IK FK references
        self.match_fk0_off = self.add_match_ref(
            self.fk_ctl[1], self.root, "matchFk0_npo", False
        )

        self.match_fk0 = self.add_match_ref(
            self.fk_ctl[0], self.match_fk0_off, "fk0_mth"
        )

        self.match_fk1_off = self.add_match_ref(
            self.fk_ctl[2], self.root, "matchFk1_npo", False
        )

        self.match_fk1 = self.add_match_ref(
            self.fk_ctl[1], self.match_fk1_off, "fk1_mth"
        )

        self.match_fk2 = self.add_match_ref(
            self.fk_ctl[2], self.ik_ctl, "fk2_mth"
        )

        self.match_ik = self.add_match_ref(self.ik_ctl, self.fk2_ctl, "ik_mth")

        self.match_ikUpv = self.add_match_ref(
            self.upv_ctl, self.fk0_ctl, "upv_mth"
        )

        # add visual reference
        self.line_ref = icon.connection_display_curve(
            self.getName("visalRef"), [self.upv_ctl, self.mid_ctl]
        )

    def addAttributes(self):

        # Anim -------------------------------------------
        self.blend_att = self.addAnimParam(
            "blend", "Fk/Ik Blend", "double", self.settings["blend"], 0, 1
        )
        self.roll_att = self.addAnimParam(
            "roll", "Roll", "double", 0, -180, 180
        )
        self.scale_att = self.addAnimParam(
            "ikscale", "Scale", "double", 1, 0.001, 99
        )
        self.maxstretch_att = self.addAnimParam(
            "maxstretch",
            "Max Stretch",
            "double",
            self.settings["maxstretch"],
            1,
            99,
        )
        self.slide_att = self.addAnimParam(
            "slide", "Slide", "double", 0.5, 0, 1
        )
        self.softness_att = self.addAnimParam(
            "softness", "Softness", "double", 0, 0, 1
        )
        self.reverse_att = self.addAnimParam(
            "reverse", "Reverse", "double", 0, 0, 1
        )
        self.roundness_att = self.addAnimParam(
            "roundness", "Roundness", "double", 0, 0, self.size
        )
        self.volume_att = self.addAnimParam(
            "volume", "Volume", "double", 1, 0, 1
        )

        if self.settings["extraTweak"]:
            self.tweakVis_att = self.addAnimParam(
                "Tweak_vis", "Tweak Vis", "bool", False
            )

        # Ref
        if self.settings["ikrefarray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["ikrefarray"].split(",")
            )
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam(
                    "ikref",
                    "Ik Ref",
                    0,
                    self.settings["ikrefarray"].split(","),
                )

        ref_names = ["Auto", "ikFoot"]
        if self.settings["upvrefarray"]:
            ref_names = ref_names + self.get_valid_alias_list(
                self.settings["upvrefarray"].split(",")
            )
        self.upvref_att = self.addAnimEnumParam(
            "upvref", "UpV Ref", 0, ref_names
        )

        if self.settings["pinrefarray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["pinrefarray"].split(",")
            )
            ref_names = ["Auto"] + ref_names
            if len(ref_names) > 1:
                self.pin_att = self.addAnimEnumParam(
                    "kneeref", "Knee Ref", 0, ref_names
                )
        if self.validProxyChannels:
            attrs_list = [self.blend_att, self.roundness_att]
            if self.settings["extraTweak"]:
                attrs_list += [self.tweakVis_att]
            attribute.addProxyAttribute(
                attrs_list,
                [
                    self.fk0_ctl,
                    self.fk1_ctl,
                    self.fk2_ctl,
                    self.ik_ctl,
                    self.upv_ctl,
                    self.mid_ctl,
                ],
            )
            attribute.addProxyAttribute(
                self.roll_att, [self.ik_ctl, self.upv_ctl]
            )

        # Setup ------------------------------------------
        # Eval Fcurve
        if self.guide.paramDefs["st_profile"].value:
            self.st_value = self.guide.paramDefs["st_profile"].value
            self.sq_value = self.guide.paramDefs["sq_profile"].value
        else:
            self.st_value = fcurve.getFCurveValues(
                self.settings["st_profile"], self.divisions
            )
            self.sq_value = fcurve.getFCurveValues(
                self.settings["sq_profile"], self.divisions
            )

        self.st_att = [
            self.addSetupParam(
                "stretch_%s" % i,
                "Stretch %s" % i,
                "double",
                self.st_value[i],
                -1,
                0,
            )
            for i in range(self.divisions)
        ]
        self.sq_att = [
            self.addSetupParam(
                "squash_%s" % i,
                "Squash %s" % i,
                "double",
                self.sq_value[i],
                0,
                1,
            )
            for i in range(self.divisions)
        ]

        self.resample_att = self.addSetupParam(
            "resample", "Resample", "bool", True
        )
        self.absolute_att = self.addSetupParam(
            "absolute", "Absolute", "bool", False
        )

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """

        # 1 bone chain Upv ref ===========================
        self.ikHandleUpvRef = primitive.addIkHandle(
            self.root,
            self.getName("ikHandleLegChainUpvRef"),
            self.legChainUpvRef,
            "ikSCsolver",
        )
        pm.pointConstraint(self.ik_ctl, self.ikHandleUpvRef)
        self.relatives_map_upv = {
            "Auto": self.legChainUpvRef[0],
            "Foot": self.ik_ctl,
        }

        # Visibilities -------------------------------------
        # shape.dispGeometry
        # fk
        fkvis_node = node.createReverseNode(self.blend_att)
        try:
            for shp in self.fk0_ctl.getShapes():
                pm.connectAttr(fkvis_node.outputX, shp.attr("visibility"))
            for shp in self.fk1_ctl.getShapes():
                pm.connectAttr(fkvis_node.outputX, shp.attr("visibility"))
            for shp in self.fk2_ctl.getShapes():
                pm.connectAttr(fkvis_node.outputX, shp.attr("visibility"))

            # ik
            for shp in self.upv_ctl.getShapes():
                pm.connectAttr(self.blend_att, shp.attr("visibility"))
            for shp in self.ikcns_ctl.getShapes():
                pm.connectAttr(self.blend_att, shp.attr("visibility"))
            for shp in self.ik_ctl.getShapes():
                pm.connectAttr(self.blend_att, shp.attr("visibility"))
            for shp in self.line_ref.getShapes():
                pm.connectAttr(self.blend_att, shp.attr("visibility"))
        except RuntimeError:
            pm.displayInfo("Visibility already connecte")

        # IK Solver -----------------------------------------
        out = [self.bone0, self.bone1, self.ctrn_loc, self.eff_loc]
        o_node = applyop.gear_ikfk2bone_op(
            out,
            self.root_ctl,
            self.ik_ref,
            self.upv_ctl,
            self.fk_ctl[0],
            self.fk_ctl[1],
            self.fk_ref,
            self.length0,
            self.length1,
            self.negate,
        )

        pm.connectAttr(self.blend_att, o_node + ".blend")
        if self.negate:
            mulVal = -1
        else:
            mulVal = 1
        node.createMulNode(self.roll_att, mulVal, o_node + ".roll")
        pm.connectAttr(self.scale_att, o_node + ".scaleA")
        pm.connectAttr(self.scale_att, o_node + ".scaleB")
        pm.connectAttr(self.maxstretch_att, o_node + ".maxstretch")
        pm.connectAttr(self.slide_att, o_node + ".slide")
        pm.connectAttr(self.softness_att, o_node + ".softness")
        pm.connectAttr(self.reverse_att, o_node + ".reverse")

        # Twist references ---------------------------------
        self.ikhArmRef, self.tmpCrv = applyop.splineIK(
            self.getName("legRollRef"),
            self.rollRef,
            parent=self.root,
            cParent=self.bone0,
        )

        pm.pointConstraint(self.mid_ctl, self.tws1_loc, maintainOffset=False)
        pm.connectAttr(self.mid_ctl.scaleX, self.tws1_loc.scaleX)
        applyop.oriCns(self.mid_ctl, self.tws1_rot, maintainOffset=False)

        pm.pointConstraint(self.eff_loc, self.tws2_loc, maintainOffset=False)
        pm.scaleConstraint(self.eff_loc, self.tws2_loc, maintainOffset=False)
        applyop.oriCns(self.bone1, self.tws2_loc, maintainOffset=False)

        applyop.oriCns(self.tws_ref, self.tws2_rot)

        if self.settings["div0"]:
            ori_ref = self.rollRef[0]
        else:
            ori_ref = self.bone0

        applyop.oriCns(ori_ref, self.tws0_loc, maintainOffset=True)

        self.tws0_loc.setAttr("sx", 0.000001)
        self.tws2_loc.setAttr("sx", 0.000001)

        add_node = node.createAddNode(self.roundness_att, 0.000001)
        pm.connectAttr(add_node + ".output", self.tws1_rot.attr("sx"))

        # Volume -------------------------------------------
        distA_node = node.createDistNode(self.tws0_loc, self.tws1_loc)
        distB_node = node.createDistNode(self.tws1_loc, self.tws2_loc)
        add_node = node.createAddNode(distA_node.distance, distB_node.distance)
        div_node = node.createDivNode(
            add_node.output, self.root_ctl.attr("sx")
        )

        # comp scaling issue
        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(self.root.attr("worldMatrix"), dm_node.inputMatrix)

        div_node2 = node.createDivNode(div_node.outputX, dm_node.outputScaleX)

        self.volDriver_att = div_node2.outputX

        if self.settings["extraTweak"]:
            for tweak_ctl in self.tweak_ctl:
                for shp in tweak_ctl.getShapes():
                    pm.connectAttr(self.tweakVis_att, shp.attr("visibility"))

        # Divisions ----------------------------------------
        # at 0 or 1 the division will follow exactly the rotation of the
        # controler.. and we wont have this nice tangent + roll
        for i, div_cns in enumerate(self.div_cns):
            subdiv = 40
            if i < (self.settings["div0"] + 1):
                perc = i * 0.5 / (self.settings["div0"] + 1.0)
            elif i < (self.settings["div0"] + 2):
                perc = 0.501
            else:
                perc = 0.5 + (i - self.settings["div0"] - 1.0) * 0.5 / (
                    self.settings["div1"] + 1.0
                )

            perc = max(0.001, min(0.999, perc))

            # Roll
            if self.negate:
                o_node = applyop.gear_rollsplinekine_op(
                    div_cns,
                    [self.tws2_rot, self.tws1_rot, self.tws0_rot],
                    1.0 - perc,
                    subdiv,
                )
            else:
                o_node = applyop.gear_rollsplinekine_op(
                    div_cns,
                    [self.tws0_rot, self.tws1_rot, self.tws2_rot],
                    perc,
                    subdiv,
                )

            pm.connectAttr(self.resample_att, o_node.resample)
            pm.connectAttr(self.absolute_att, o_node.absolute)

            # Squash n Stretch
            o_node = applyop.gear_squashstretch2_op(
                div_cns, None, pm.getAttr(self.volDriver_att), "x"
            )
            pm.connectAttr(self.volume_att, o_node.blend)
            pm.connectAttr(self.volDriver_att, o_node.driver)
            pm.connectAttr(self.st_att[i], o_node.stretch)
            pm.connectAttr(self.sq_att[i], o_node.squash)

        # match IK/FK ref
        pm.parentConstraint(self.bone0, self.match_fk0_off, mo=True)
        pm.parentConstraint(self.bone1, self.match_fk1_off, mo=True)
        return

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.div_cns[0]
        self.relatives["knee"] = self.div_cns[self.settings["div0"] + 1]
        self.relatives["ankle"] = self.div_cns[-1]
        self.relatives["eff"] = self.end_ref

        self.controlRelatives["root"] = self.fk0_ctl
        self.controlRelatives["knee"] = self.fk1_ctl
        self.controlRelatives["ankle"] = self.ik_ctl
        self.controlRelatives["eff"] = self.fk2_ctl

        self.jointRelatives["root"] = 0
        self.jointRelatives["knee"] = self.settings["div0"] + 1
        self.jointRelatives["ankle"] = len(self.div_cns)
        self.jointRelatives["eff"] = len(self.div_cns)

        self.aliasRelatives["eff"] = "foot"

    def connect_standard(self):
        self.parent.addChild(self.root)

        # Set the Ik Reference
        self.connectRef(self.settings["ikrefarray"], self.ik_cns)
        if self.settings["upvrefarray"]:
            self.connectRef(
                "Auto,Foot," + self.settings["upvrefarray"], self.upv_cns, True
            )
        else:
            self.connectRef("Auto,Foot", self.upv_cns, True)

        if self.settings["pinrefarray"]:
            self.connectRef2(
                "Auto," + self.settings["pinrefarray"],
                self.mid_cns,
                self.pin_att,
                [self.ctrn_loc],
                False,
            )
