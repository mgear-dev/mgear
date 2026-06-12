"""Component Leg 2 joints Free Tangents 01 module"""

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
        self.fk0_npo = primitive.addTransform(
            self.root_ctl, self.getName("fk0_npo"), t
        )
        self.fk0_ctl = self.addCtl(
            self.fk0_npo,
            "fk0_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.length0,
            h=self.size * 0.1,
            d=self.size * 0.1,
            po=datatypes.Vector(0.5 * self.length0 * self.n_factor, 0, 0),
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
        self.fk1_npo = primitive.addTransform(
            self.fk0_ctl, self.getName("fk1_npo"), t
        )
        self.fk1_ctl = self.addCtl(
            self.fk1_npo,
            "fk1_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.length1,
            h=self.size * 0.1,
            d=self.size * 0.1,
            po=datatypes.Vector(0.5 * self.length1 * self.n_factor, 0, 0),
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

        self.fk2_npo = primitive.addTransform(
            self.fk1_ctl, self.getName("fk2_npo"), t
        )

        self.fk2_ctl = self.addCtl(
            self.fk2_npo,
            "fk2_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.length2,
            h=self.size * 0.1,
            d=self.size * 0.1,
            po=datatypes.Vector(0.5 * self.length2 * self.n_factor, 0, 0),
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

        m = transform.getTransformLookingAt(
            self.guide.pos["ankle"],
            self.guide.pos["eff"],
            self.x_axis,
            "zx",
            False,
        )

        self.ik_ctl = self.addCtl(
            self.ikcns_ctl,
            "ik_ctl",
            transform.getTransformFromPos(self.guide.pos["ankle"]),
            self.color_ik,
            "cube",
            w=self.size * 0.12,
            h=self.size * 0.12,
            d=self.size * 0.12,
            tp=self.ikcns_ctl,
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

        tA = transform.getTransformLookingAt(
            self.guide.apos[0],
            self.guide.apos[1],
            self.normal,
            "xz",
            self.negate,
        )
        tA = transform.setMatrixPosition(tA, self.guide.apos[1])
        tB = transform.getTransformLookingAt(
            self.guide.apos[1],
            self.guide.apos[2],
            self.normal,
            "xz",
            self.negate,
        )
        t = transform.getInterpolateTransformMatrix(tA, tB)
        self.ctrn_loc = primitive.addTransform(
            self.root, self.getName("ctrn_loc"), t
        )
        self.eff_loc = primitive.addTransformFromPos(
            self.root_ctl, self.getName("eff_loc"), self.guide.apos[2]
        )

        # tws_ref
        t = transform.getRotationFromAxis(
            datatypes.Vector(0, -1, 0), self.normal, "xz", self.negate
        )
        t = transform.setMatrixPosition(t, self.guide.pos["ankle"])

        self.tws_ref = primitive.addTransform(
            self.eff_loc, self.getName("tws_ref"), t
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
        if self.settings["mirrorMid"]:
            if self.negate:
                self.mid_cns.rz.set(180)
                self.mid_cns.sz.set(-1)
        else:
            attribute.setInvertMirror(self.mid_ctl, ["tx", "ty", "tz"])
        attribute.setKeyableAttributes(self.mid_ctl, self.t_params)

        # Twist references ---------------------------------
        x = datatypes.Vector(0, -1, 0)
        x = x * transform.getTransform(self.eff_loc)
        z = datatypes.Vector(self.normal.x, self.normal.y, self.normal.z)
        z = z * transform.getTransform(self.eff_loc)

        m = transform.getRotationFromAxis(x, z, "xz", self.negate)
        m = transform.setMatrixPosition(
            m, transform.getTranslation(self.ik_ctl)
        )

        self.tws0_loc = primitive.addTransform(
            self.root_ctl,
            self.getName("tws0_loc"),
            transform.getTransform(self.fk_ctl[0]),
        )
        self.tws0_rot = primitive.addTransform(
            self.tws0_loc,
            self.getName("tws0_rot"),
            transform.getTransform(self.fk_ctl[0]),
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

        self.tws1A_npo = primitive.addTransform(
            self.mid_ctl, self.getName("tws1A_npo"), tA
        )
        self.tws1A_loc = primitive.addTransform(
            self.tws1A_npo, self.getName("tws1A_loc"), tA
        )
        self.tws1B_npo = primitive.addTransform(
            self.mid_ctl, self.getName("tws1B_npo"), tB
        )
        self.tws1B_loc = primitive.addTransform(
            self.tws1B_npo, self.getName("tws1B_loc"), tB
        )

        self.tws2_npo = primitive.addTransform(
            self.root,
            self.getName("tws2_npo"),
            transform.getTransform(self.fk_ctl[2]),
        )
        self.tws2_loc = primitive.addTransform(
            self.tws2_npo,
            self.getName("tws2_loc"),
            transform.getTransform(self.fk_ctl[2]),
        )
        self.tws2_rot = primitive.addTransform(
            self.tws2_npo,
            self.getName("tws2_rot"),
            transform.getTransform(self.fk_ctl[2]),
        )

        # Roll twist chain ---------------------------------
        # Arm
        self.uplegChainPos = []
        ii = 1.0 / (self.settings["div0"] + 1)
        i = 0.0
        for p in range(self.settings["div0"] + 2):
            self.uplegChainPos.append(
                vector.linearlyInterpolate(
                    self.guide.pos["root"], self.guide.pos["knee"], blend=i
                )
            )
            i = i + ii

        self.uplegTwistChain = primitive.add2DChain(
            self.root,
            self.getName("uplegTwist%s_jnt"),
            self.uplegChainPos,
            self.normal,
            False,
            self.WIP,
        )

        # Forearm
        self.lowlegChainPos = []
        ii = 1.0 / (self.settings["div1"] + 1)
        i = 0.0
        for p in range(self.settings["div1"] + 2):
            self.lowlegChainPos.append(
                vector.linearlyInterpolate(
                    self.guide.pos["knee"], self.guide.pos["ankle"], blend=i
                )
            )
            i = i + ii

        self.lowlegTwistChain = primitive.add2DChain(
            self.root,
            self.getName("lowlegTwist%s_jnt"),
            self.lowlegChainPos,
            self.normal,
            False,
            self.WIP,
        )
        pm.parent(self.lowlegTwistChain[0], self.mid_ctl)

        # Hand Aux chain and nonroll
        self.auxChainPos = []
        ii = 0.5
        i = 0.0
        for p in range(3):
            self.auxChainPos.append(
                vector.linearlyInterpolate(
                    self.guide.pos["ankle"], self.guide.pos["eff"], blend=i
                )
            )
            i = i + ii
        t = self.root.getMatrix(worldSpace=True)

        self.aux_npo = primitive.addTransform(
            self.root, self.getName("aux_npo"), t
        )
        self.auxTwistChain = primitive.add2DChain(
            self.aux_npo,
            self.getName("auxTwist%s_jnt"),
            self.lowlegChainPos[:3],
            self.normal,
            False,
            self.WIP,
        )
        # Non Roll join ref ---------------------------------
        self.uplegRollRef = primitive.add2DChain(
            self.root,
            self.getName("uplegRollRef%s_jnt"),
            self.uplegChainPos[:2],
            self.normal,
            False,
            self.WIP,
        )

        self.lowlegRollRef = primitive.add2DChain(
            self.aux_npo,
            self.getName("lowlegRollRef%s_jnt"),
            self.lowlegChainPos[:2],
            self.normal,
            False,
            self.WIP,
        )
        # Divisions ----------------------------------------
        # We have at least one division at the start, the end and one for the
        # elbow. + 2 for knee angle control
        self.divisions = self.settings["div0"] + self.settings["div1"] + 4

        self.div_cns = []
        for i in range(self.divisions):

            div_cns = primitive.addTransform(
                self.root_ctl, self.getName("div%s_loc" % i)
            )

            self.div_cns.append(div_cns)

            self.jnt_pos.append([div_cns, i])

        # End reference ------------------------------------
        # To help the deformation on the ankle
        self.end_ref = primitive.addTransform(
            self.eff_loc, self.getName("end_ref"), m
        )
        for a in "xyz":
            self.end_ref.attr("s%s" % a).set(1.0)
        if self.negate:
            self.end_ref.attr("ry").set(-180.0)
        self.jnt_pos.append([self.end_ref, "end"])

        # Tangent controls
        t = transform.getInterpolateTransformMatrix(
            self.fk_ctl[0], self.tws1A_npo, 0.5
        )
        self.uplegTangentA_loc = primitive.addTransform(
            self.root_ctl,
            self.getName("uplegTangentA_loc"),
            self.fk_ctl[0].getMatrix(worldSpace=True),
        )

        self.uplegTangentA_npo = primitive.addTransform(
            self.uplegTangentA_loc, self.getName("uplegTangentA_npo"), t
        )

        self.uplegTangentA_ctl = self.addCtl(
            self.uplegTangentA_npo,
            "uplegTangentA_ctl",
            t,
            self.color_ik,
            "circle",
            w=self.size * 0.2,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl,
        )

        if self.negate:
            self.uplegTangentA_npo.rz.set(180)
            self.uplegTangentA_npo.sz.set(-1)
        attribute.setKeyableAttributes(self.uplegTangentA_ctl, self.t_params)

        t = transform.getInterpolateTransformMatrix(
            self.fk_ctl[0], self.tws1A_npo, 0.9
        )
        self.uplegTangentB_npo = primitive.addTransform(
            self.tws1A_loc, self.getName("uplegTangentB_npo"), t
        )

        self.uplegTangentB_ctl = self.addCtl(
            self.uplegTangentB_npo,
            "uplegTangentB_ctl",
            t,
            self.color_ik,
            "circle",
            w=self.size * 0.1,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl,
        )

        if self.negate:
            self.uplegTangentB_npo.rz.set(180)
            self.uplegTangentB_npo.sz.set(-1)
        attribute.setKeyableAttributes(self.uplegTangentB_ctl, self.t_params)

        tC = self.tws1B_npo.getMatrix(worldSpace=True)
        tC = transform.setMatrixPosition(tC, self.guide.apos[2])
        t = transform.getInterpolateTransformMatrix(self.tws1B_npo, tC, 0.1)
        self.lowlegTangentA_npo = primitive.addTransform(
            self.tws1B_loc, self.getName("lowlegTangentA_npo"), t
        )

        self.lowlegTangentA_ctl = self.addCtl(
            self.lowlegTangentA_npo,
            "lowlegTangentA_ctl",
            t,
            self.color_ik,
            "circle",
            w=self.size * 0.1,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl,
        )

        if self.negate:
            self.lowlegTangentA_npo.rz.set(180)
            self.lowlegTangentA_npo.sz.set(-1)
        attribute.setKeyableAttributes(self.lowlegTangentA_ctl, self.t_params)

        t = transform.getInterpolateTransformMatrix(self.tws1B_npo, tC, 0.5)

        self.lowlegTangentB_loc = primitive.addTransform(
            self.root, self.getName("lowlegTangentB_loc"), tC
        )

        self.lowlegTangentB_npo = primitive.addTransform(
            self.lowlegTangentB_loc, self.getName("lowlegTangentB_npo"), t
        )

        self.lowlegTangentB_ctl = self.addCtl(
            self.lowlegTangentB_npo,
            "lowlegTangentB_ctl",
            t,
            self.color_ik,
            "circle",
            w=self.size * 0.2,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl,
        )

        if self.negate:
            self.lowlegTangentB_npo.rz.set(180)
            self.lowlegTangentB_npo.sz.set(-1)
        attribute.setKeyableAttributes(self.lowlegTangentB_ctl, self.t_params)

        t = self.mid_ctl.getMatrix(worldSpace=True)
        self.kneeTangent_npo = primitive.addTransform(
            self.mid_ctl, self.getName("kneeTangent_npo"), t
        )

        self.kneeTangent_ctl = self.addCtl(
            self.kneeTangent_npo,
            "kneeTangent_ctl",
            t,
            self.color_fk,
            "circle",
            w=self.size * 0.25,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl,
        )

        if self.negate:
            self.kneeTangent_npo.rz.set(180)
            self.kneeTangent_npo.sz.set(-1)
        attribute.setKeyableAttributes(self.kneeTangent_ctl, self.t_params)

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
            "roundness", "Roundness", "double", 0, 0, 1
        )
        self.volume_att = self.addAnimParam(
            "volume", "Volume", "double", 0, 0, 1
        )
        self.tangentVis_att = self.addAnimParam(
            "Tangent_vis", "Tangent vis", "bool", False
        )

        # Ref
        if self.settings["ikrefarray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["ikrefarray"].split(",")
            )
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam(
                    "ikref", "Ik Ref", 0, ref_names
                )

        ref_names = ["Auto", "ikFoot"]
        if self.settings["upvrefarray"]:
            ref_names += self.get_valid_alias_list(
                self.settings["upvrefarray"].split(",")
            )
        if len(ref_names) > 1:
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
            attribute.addProxyAttribute(
                [self.blend_att, self.roundness_att],
                [
                    self.fk0_ctl,
                    self.fk1_ctl,
                    self.fk2_ctl,
                    self.ik_ctl,
                    self.upv_ctl,
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

        # 1 bone chain Upv ref ==============================
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

        for shp in self.fk0_ctl.getShapes():
            pm.connectAttr(fkvis_node + ".outputX", shp.attr("visibility"))
        for shp in self.fk1_ctl.getShapes():
            pm.connectAttr(fkvis_node + ".outputX", shp.attr("visibility"))
        for shp in self.fk2_ctl.getShapes():
            pm.connectAttr(fkvis_node + ".outputX", shp.attr("visibility"))

        # ik
        for shp in self.upv_ctl.getShapes():
            pm.connectAttr(self.blend_att, shp.attr("visibility"))
        for shp in self.ikcns_ctl.getShapes():
            pm.connectAttr(self.blend_att, shp.attr("visibility"))
        for shp in self.ik_ctl.getShapes():
            pm.connectAttr(self.blend_att, shp.attr("visibility"))
        for shp in self.line_ref.getShapes():
            pm.connectAttr(self.blend_att, shp.attr("visibility"))

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
        # pm.connectAttr(self.roll_att, o_node+".roll")
        pm.connectAttr(self.scale_att, o_node + ".scaleA")
        pm.connectAttr(self.scale_att, o_node + ".scaleB")
        pm.connectAttr(self.maxstretch_att, o_node + ".maxstretch")
        pm.connectAttr(self.slide_att, o_node + ".slide")
        pm.connectAttr(self.softness_att, o_node + ".softness")
        pm.connectAttr(self.reverse_att, o_node + ".reverse")

        # Twist references ---------------------------------
        o_node = applyop.gear_mulmatrix_op(
            self.eff_loc.attr("worldMatrix"),
            self.root.attr("worldInverseMatrix"),
        )

        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(o_node + ".output", dm_node + ".inputMatrix")
        pm.connectAttr(
            dm_node + ".outputTranslate", self.tws2_npo.attr("translate")
        )

        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(o_node + ".output", dm_node + ".inputMatrix")
        pm.connectAttr(dm_node + ".outputRotate", self.tws2_npo.attr("rotate"))

        # spline IK for  twist jnts
        self.ikhUpLegTwist, self.uplegTwistCrv = applyop.splineIK(
            self.getName("uplegTwist"),
            self.uplegTwistChain,
            parent=self.root,
            cParent=self.bone0,
        )

        self.ikhLowLegTwist, self.lowlegTwistCrv = applyop.splineIK(
            self.getName("lowlegTwist"),
            self.lowlegTwistChain,
            parent=self.root,
            cParent=self.bone1,
        )

        # references
        self.ikhUpLegRef, self.tmpCrv = applyop.splineIK(
            self.getName("uplegRollRef"),
            self.uplegRollRef,
            parent=self.root,
            cParent=self.bone0,
        )

        self.ikhLowLegRef, self.tmpCrv = applyop.splineIK(
            self.getName("lowlegRollRef"),
            self.lowlegRollRef,
            parent=self.root,
            cParent=self.eff_loc,
        )

        self.ikhAuxTwist, self.tmpCrv = applyop.splineIK(
            self.getName("auxTwist"),
            self.auxTwistChain,
            parent=self.root,
            cParent=self.eff_loc,
        )

        # setting connexions for ikhUpLegTwist
        self.ikhUpLegTwist.attr("dTwistControlEnable").set(True)
        self.ikhUpLegTwist.attr("dWorldUpType").set(4)
        self.ikhUpLegTwist.attr("dWorldUpAxis").set(3)
        self.ikhUpLegTwist.attr("dWorldUpVectorZ").set(1.0)
        self.ikhUpLegTwist.attr("dWorldUpVectorY").set(0.0)
        self.ikhUpLegTwist.attr("dWorldUpVectorEndZ").set(1.0)
        self.ikhUpLegTwist.attr("dWorldUpVectorEndY").set(0.0)
        pm.connectAttr(
            self.uplegRollRef[0].attr("worldMatrix[0]"),
            self.ikhUpLegTwist.attr("dWorldUpMatrix"),
        )
        pm.connectAttr(
            self.bone0.attr("worldMatrix[0]"),
            self.ikhUpLegTwist.attr("dWorldUpMatrixEnd"),
        )

        # setting connexions for ikhAuxTwist
        self.ikhAuxTwist.attr("dTwistControlEnable").set(True)
        self.ikhAuxTwist.attr("dWorldUpType").set(4)
        self.ikhAuxTwist.attr("dWorldUpAxis").set(3)
        self.ikhAuxTwist.attr("dWorldUpVectorZ").set(1.0)
        self.ikhAuxTwist.attr("dWorldUpVectorY").set(0.0)
        self.ikhAuxTwist.attr("dWorldUpVectorEndZ").set(1.0)
        self.ikhAuxTwist.attr("dWorldUpVectorEndY").set(0.0)
        pm.connectAttr(
            self.lowlegRollRef[0].attr("worldMatrix[0]"),
            self.ikhAuxTwist.attr("dWorldUpMatrix"),
        )
        pm.connectAttr(
            self.tws_ref.attr("worldMatrix[0]"),
            self.ikhAuxTwist.attr("dWorldUpMatrixEnd"),
        )
        pm.connectAttr(
            self.auxTwistChain[1].attr("rx"), self.ikhLowLegTwist.attr("twist")
        )

        pm.parentConstraint(self.bone1, self.aux_npo, maintainOffset=True)

        # scale arm length for twist chain (not the squash and stretch)
        arclen_node = pm.arclen(self.uplegTwistCrv, ch=True)
        alAttrUpLeg = arclen_node.attr("arcLength")
        muldiv_nodeArm = pm.createNode("multiplyDivide")
        pm.connectAttr(
            arclen_node.attr("arcLength"), muldiv_nodeArm.attr("input1X")
        )
        muldiv_nodeArm.attr("input2X").set(alAttrUpLeg.get())
        muldiv_nodeArm.attr("operation").set(2)
        for jnt in self.uplegTwistChain:
            pm.connectAttr(muldiv_nodeArm.attr("outputX"), jnt.attr("sx"))

        # scale forearm length for twist chain (not the squash and stretch)
        arclen_node = pm.arclen(self.lowlegTwistCrv, ch=True)
        alAttrLowLeg = arclen_node.attr("arcLength")
        muldiv_nodeLowLeg = pm.createNode("multiplyDivide")
        pm.connectAttr(
            arclen_node.attr("arcLength"), muldiv_nodeLowLeg.attr("input1X")
        )
        muldiv_nodeLowLeg.attr("input2X").set(alAttrLowLeg.get())
        muldiv_nodeLowLeg.attr("operation").set(2)
        for jnt in self.lowlegTwistChain:
            pm.connectAttr(muldiv_nodeLowLeg.attr("outputX"), jnt.attr("sx"))

        # scale compensation for the first  twist join
        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(
            self.root.attr("worldMatrix[0]"), dm_node.attr("inputMatrix")
        )
        pm.connectAttr(
            dm_node.attr("outputScale"),
            self.uplegTwistChain[0].attr("inverseScale"),
        )
        pm.connectAttr(
            dm_node.attr("outputScale"),
            self.lowlegTwistChain[0].attr("inverseScale"),
        )

        # tangent controls
        muldiv_node = pm.createNode("multiplyDivide")
        muldiv_node.attr("input2X").set(-1)
        pm.connectAttr(self.tws1A_npo.attr("rz"), muldiv_node.attr("input1X"))
        muldiv_nodeBias = pm.createNode("multiplyDivide")
        pm.connectAttr(
            muldiv_node.attr("outputX"), muldiv_nodeBias.attr("input1X")
        )
        pm.connectAttr(self.roundness_att, muldiv_nodeBias.attr("input2X"))
        pm.connectAttr(
            muldiv_nodeBias.attr("outputX"), self.tws1A_loc.attr("rz")
        )
        if self.negate:
            axis = "xz"
        else:
            axis = "-xz"
        applyop.aimCns(
            self.tws1A_npo,
            self.tws0_loc,
            axis=axis,
            wupType=2,
            wupVector=[0, 0, 1],
            wupObject=self.mid_ctl,
            maintainOffset=False,
        )

        applyop.aimCns(
            self.lowlegTangentB_loc,
            self.lowlegTangentA_npo,
            axis=axis,
            wupType=2,
            wupVector=[0, 0, 1],
            wupObject=self.mid_ctl,
            maintainOffset=False,
        )

        pm.pointConstraint(self.eff_loc, self.lowlegTangentB_loc)

        muldiv_node = pm.createNode("multiplyDivide")
        muldiv_node.attr("input2X").set(-1)
        pm.connectAttr(self.tws1B_npo.attr("rz"), muldiv_node.attr("input1X"))
        muldiv_nodeBias = pm.createNode("multiplyDivide")
        pm.connectAttr(
            muldiv_node.attr("outputX"), muldiv_nodeBias.attr("input1X")
        )
        pm.connectAttr(self.roundness_att, muldiv_nodeBias.attr("input2X"))
        pm.connectAttr(
            muldiv_nodeBias.attr("outputX"), self.tws1B_loc.attr("rz")
        )
        if self.negate:
            axis = "-xz"
        else:
            axis = "xz"
        applyop.aimCns(
            self.tws1B_npo,
            self.tws2_loc,
            axis=axis,
            wupType=2,
            wupVector=[0, 0, 1],
            wupObject=self.mid_ctl,
            maintainOffset=False,
        )

        applyop.aimCns(
            self.uplegTangentA_loc,
            self.uplegTangentB_npo,
            axis=axis,
            wupType=2,
            wupVector=[0, 0, 1],
            wupObject=self.mid_ctl,
            maintainOffset=False,
        )

        # Volume -------------------------------------------
        distA_node = node.createDistNode(self.tws0_loc, self.tws1_loc)
        distB_node = node.createDistNode(self.tws1_loc, self.tws2_loc)
        add_node = node.createAddNode(
            distA_node + ".distance", distB_node + ".distance"
        )
        div_node = node.createDivNode(
            add_node + ".output", self.root_ctl.attr("sx")
        )

        # comp scaling issue
        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(self.root.attr("worldMatrix"), dm_node + ".inputMatrix")

        div_node2 = node.createDivNode(
            div_node + ".outputX", dm_node + ".outputScaleX"
        )

        self.volDriver_att = div_node2 + ".outputX"

        # connecting tangent scaele compensation after volume to
        # avoid duplicate some nodes
        distA_node = node.createDistNode(self.tws0_loc, self.mid_ctl)
        distB_node = node.createDistNode(self.mid_ctl, self.tws2_loc)

        div_nodeUpLeg = node.createDivNode(
            distA_node + ".distance", dm_node.attr("outputScaleX")
        )

        div_node2 = node.createDivNode(
            div_nodeUpLeg + ".outputX", distA_node.attr("distance").get()
        )

        pm.connectAttr(div_node2.attr("outputX"), self.tws1A_loc.attr("sx"))

        pm.connectAttr(
            div_node2.attr("outputX"), self.uplegTangentA_loc.attr("sx")
        )

        div_nodeLowLeg = node.createDivNode(
            distB_node + ".distance", dm_node.attr("outputScaleX")
        )
        div_node2 = node.createDivNode(
            div_nodeLowLeg + ".outputX", distB_node.attr("distance").get()
        )

        pm.connectAttr(div_node2.attr("outputX"), self.tws1B_loc.attr("sx"))
        pm.connectAttr(
            div_node2.attr("outputX"), self.lowlegTangentB_loc.attr("sx")
        )

        # conection curve
        cnts = [
            self.uplegTangentA_loc,
            self.uplegTangentA_ctl,
            self.uplegTangentB_ctl,
            self.kneeTangent_ctl,
        ]
        applyop.gear_curvecns_op(self.uplegTwistCrv, cnts)

        cnts = [
            self.kneeTangent_ctl,
            self.lowlegTangentA_ctl,
            self.lowlegTangentB_ctl,
            self.lowlegTangentB_loc,
        ]
        applyop.gear_curvecns_op(self.lowlegTwistCrv, cnts)

        # Tangent controls vis
        for shp in self.uplegTangentA_ctl.getShapes():
            pm.connectAttr(self.tangentVis_att, shp.attr("visibility"))
        for shp in self.uplegTangentB_ctl.getShapes():
            pm.connectAttr(self.tangentVis_att, shp.attr("visibility"))
        for shp in self.lowlegTangentA_ctl.getShapes():
            pm.connectAttr(self.tangentVis_att, shp.attr("visibility"))
        for shp in self.lowlegTangentB_ctl.getShapes():
            pm.connectAttr(self.tangentVis_att, shp.attr("visibility"))
        for shp in self.kneeTangent_ctl.getShapes():
            pm.connectAttr(self.tangentVis_att, shp.attr("visibility"))

        # Divisions ----------------------------------------
        # at 0 or 1 the division will follow exactly the rotation of the
        # controler.. and we wont have this nice tangent + roll
        for i, div_cns in enumerate(self.div_cns):
            if i < (self.settings["div0"] + 2):
                mulmat_node = applyop.gear_mulmatrix_op(
                    self.uplegTwistChain[i] + ".worldMatrix",
                    div_cns + ".parentInverseMatrix",
                )
                lastUpLegDiv = div_cns
            else:
                o_node = self.lowlegTwistChain[i - (self.settings["div0"] + 2)]
                mulmat_node = applyop.gear_mulmatrix_op(
                    o_node + ".worldMatrix", div_cns + ".parentInverseMatrix"
                )
                lastLowLegDiv = div_cns
            dm_node = node.createDecomposeMatrixNode(mulmat_node + ".output")
            pm.connectAttr(dm_node + ".outputTranslate", div_cns + ".t")
            pm.connectAttr(dm_node + ".outputRotate", div_cns + ".r")

            # Squash n Stretch
            o_node = applyop.gear_squashstretch2_op(
                div_cns, None, pm.getAttr(self.volDriver_att), "x"
            )
            pm.connectAttr(self.volume_att, o_node + ".blend")
            pm.connectAttr(self.volDriver_att, o_node + ".driver")
            pm.connectAttr(self.st_att[i], o_node + ".stretch")
            pm.connectAttr(self.sq_att[i], o_node + ".squash")

        # force translation for last loc arm and foreamr
        applyop.gear_mulmatrix_op(
            self.kneeTangent_ctl.worldMatrix,
            lastUpLegDiv.parentInverseMatrix,
            lastUpLegDiv,
            "t",
        )
        applyop.gear_mulmatrix_op(
            self.tws2_loc.worldMatrix,
            lastLowLegDiv.parentInverseMatrix,
            lastLowLegDiv,
            "t",
        )

        # NOTE: next line fix the issue on meters.
        # This is special case becasuse the IK solver from mGear use the
        # scale as lenght and we have shear
        # TODO: check for a more clean and elegant solution instead of
        # re-match the world matrix again
        transform.matchWorldTransform(self.fk_ctl[0], self.match_fk0_off)
        transform.matchWorldTransform(self.fk_ctl[1], self.match_fk1_off)
        transform.matchWorldTransform(self.fk_ctl[0], self.match_fk0)
        transform.matchWorldTransform(self.fk_ctl[1], self.match_fk1)

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
        self.relatives["knee"] = self.div_cns[self.settings["div0"] + 2]
        self.relatives["ankle"] = self.div_cns[-1]
        self.relatives["eff"] = self.end_ref

        self.controlRelatives["root"] = self.fk0_ctl
        self.controlRelatives["knee"] = self.fk1_ctl
        self.controlRelatives["ankle"] = self.ik_ctl
        self.controlRelatives["eff"] = self.fk2_ctl

        self.jointRelatives["root"] = 0
        self.jointRelatives["knee"] = self.settings["div0"] + 2
        self.jointRelatives["ankle"] = len(self.div_cns)
        self.jointRelatives["eff"] = len(self.div_cns)

        self.aliasRelatives["eff"] = "foot"

    def connect_standard(self):
        self.parent.addChild(self.root)

        # Set the Ik Reference
        self.connectRef(self.settings["ikrefarray"], self.ik_cns)
        if self.settings["upvrefarray"]:
            self.connectRef(
                "Auto,ikFoot," + self.settings["upvrefarray"],
                self.upv_cns,
                True,
            )
        else:
            self.connectRef("Auto,ikFoot", self.upv_cns, True)

        if self.settings["pinrefarray"]:
            self.connectRef2(
                "Auto," + self.settings["pinrefarray"],
                self.mid_cns,
                self.pin_att,
                [self.ctrn_loc],
                False,
            )
