"""Component Arm 2 joints 01 module"""

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
        self.binormal = self.getBiNormalFromPos(self.guide.apos)

        self.length0 = vector.getDistance(self.guide.apos[0],
                                          self.guide.apos[1])
        self.length1 = vector.getDistance(self.guide.apos[1],
                                          self.guide.apos[2])
        self.length2 = vector.getDistance(self.guide.apos[2],
                                          self.guide.apos[3])

        # 1 bone chain for upv ref
        self.armChainUpvRef = primitive.add2DChain(
            self.root,
            self.getName("armUpvRef%s_jnt"),
            [self.guide.apos[0], self.guide.apos[2]],
            self.normal, False, self.WIP)

        self.armChainUpvRef[1].setAttr(
            "jointOrientZ",
            self.armChainUpvRef[1].getAttr("jointOrientZ") * -1)

        # FK Controlers -----------------------------------
        t = transform.getTransformLookingAt(self.guide.apos[0],
                                            self.guide.apos[1],
                                            self.normal,
                                            "xz",
                                            self.negate)
        self.fk0_npo = primitive.addTransform(self.root,
                                              self.getName("fk0_npo"),
                                              t)

        po_vec = datatypes.Vector(.5 * self.length0 * self.n_factor, 0, 0)
        self.fk0_ctl = self.addCtl(self.fk0_npo,
                                   "fk0_ctl",
                                   t,
                                   self.color_fk,
                                   "cube",
                                   w=self.length0,
                                   h=self.size * .1,
                                   d=self.size * .1,
                                   po=po_vec,
                                   tp=self.parentCtlTag)

        attribute.setKeyableAttributes(
            self.fk0_ctl,
            ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx"])

        t = transform.getTransformLookingAt(self.guide.apos[1],
                                            self.guide.apos[2],
                                            self.normal,
                                            "xz",
                                            self.negate)
        self.fk1_npo = primitive.addTransform(self.fk0_ctl,
                                              self.getName("fk1_npo"),
                                              t)

        po_vec = datatypes.Vector(.5 * self.length1 * self.n_factor, 0, 0)
        self.fk1_ctl = self.addCtl(self.fk1_npo,
                                   "fk1_ctl",
                                   t,
                                   self.color_fk,
                                   "cube",
                                   w=self.length1,
                                   h=self.size * .1,
                                   d=self.size * .1,
                                   po=po_vec,
                                   tp=self.fk0_ctl)

        attribute.setKeyableAttributes(
            self.fk1_ctl,
            ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx"])

        t = transform.getTransformLookingAt(self.guide.apos[2],
                                            self.guide.apos[3],
                                            self.normal,
                                            "xz",
                                            self.negate)
        self.fk2_npo = primitive.addTransform(self.fk1_ctl,
                                              self.getName("fk2_npo"),
                                              t)

        po_vec = datatypes.Vector(.5 * self.length2 * self.n_factor, 0, 0)
        self.fk2_ctl = self.addCtl(self.fk2_npo,
                                   "fk2_ctl",
                                   t,
                                   self.color_fk,
                                   "cube",
                                   w=self.length2,
                                   h=self.size * .1,
                                   d=self.size * .1,
                                   po=po_vec,
                                   tp=self.fk1_ctl)

        attribute.setKeyableAttributes(self.fk2_ctl)

        self.fk_ctl = [self.fk0_ctl, self.fk1_ctl, self.fk2_ctl]

        for x in self.fk_ctl:
            attribute.setInvertMirror(x, ["tx", "ty", "tz"])

        # IK Controlers -----------------------------------

        # Define the wrist transform (wt)
        if not self.settings["guideOrientWrist"]:
            if self.settings["mirrorIK"] and self.negate:
                m = transform.getTransformLookingAt(self.guide.pos["wrist"],
                                                    self.guide.pos["eff"],
                                                    self.normal,
                                                    "x-y",
                                                    True)
            else:
                m = transform.getTransformLookingAt(self.guide.pos["wrist"],
                                                    self.guide.pos["eff"],
                                                    self.normal,
                                                    "xy",
                                                    False)
        else:
            m = transform.getTransformFromPos(self.guide.pos["wrist"])

        self.ik_cns = primitive.addTransform(self.root,
                                             self.getName("ik_cns"),
                                             m)

        self.ikcns_ctl = self.addCtl(self.ik_cns,
                                     "ikcns_ctl",
                                     m,
                                     self.color_ik,
                                     "null",
                                     w=self.size * .12,
                                     tp=self.parentCtlTag)

        attribute.setInvertMirror(self.ikcns_ctl, ["tx", "ty", "tz"])

        self.ik_ctl = self.addCtl(self.ikcns_ctl,
                                  "ik_ctl",
                                  m,
                                  self.color_ik,
                                  "cube",
                                  w=self.size * .12,
                                  h=self.size * .12,
                                  d=self.size * .12,
                                  tp=self.ikcns_ctl)
        if self.settings["mirrorIK"]:
            if self.negate:
                self.ik_cns.sx.set(-1)
        else:
            attribute.setInvertMirror(self.ik_ctl, ["tx", "ry", "rz"])
        attribute.setKeyableAttributes(self.ik_ctl)
        self.ik_ctl_ref = primitive.addTransform(self.ik_ctl,
                                                 self.getName("ikCtl_ref"),
                                                 m)

        # upv
        v = self.guide.apos[2] - self.guide.apos[0]
        v = self.normal ^ v
        v.normalize()
        v *= self.size * .5
        v += self.guide.apos[1]

        self.upv_cns = primitive.addTransformFromPos(self.root,
                                                     self.getName("upv_cns"),
                                                     v)

        self.upv_ctl = self.addCtl(self.upv_cns,
                                   "upv_ctl",
                                   transform.getTransform(self.upv_cns),
                                   self.color_ik,
                                   "diamond",
                                   w=self.size * .12,
                                   tp=self.parentCtlTag)

        if self.settings["mirrorMid"]:
            if self.negate:
                self.upv_cns.rz.set(180)
                self.upv_cns.sy.set(-1)
        else:
            attribute.setInvertMirror(self.upv_ctl, ["tx"])
        attribute.setKeyableAttributes(self.upv_ctl, self.t_params)

        # IK rotation controls
        if self.settings["ikTR"]:
            self.ikRot_npo = primitive.addTransform(self.root,
                                                    self.getName("ikRot_npo"),
                                                    m)
            self.ikRot_cns = primitive.addTransform(self.ikRot_npo,
                                                    self.getName("ikRot_cns"),
                                                    m)
            self.ikRot_ctl = self.addCtl(self.ikRot_cns,
                                         "ikRot_ctl",
                                         m,
                                         self.color_ik,
                                         "sphere",
                                         w=self.size * .12,
                                         tp=self.ik_ctl)
            attribute.setKeyableAttributes(self.ikRot_ctl, self.r_params)

        # References --------------------------------------
        # Calculate  again the transfor for the IK ref. This way align with FK
        trnIK_ref = transform.getTransformLookingAt(self.guide.pos["wrist"],
                                                    self.guide.pos["eff"],
                                                    self.normal,
                                                    "xz",
                                                    self.negate)
        self.ik_ref = primitive.addTransform(self.ik_ctl_ref,
                                             self.getName("ik_ref"),
                                             trnIK_ref)
        self.fk_ref = primitive.addTransform(self.fk_ctl[2],
                                             self.getName("fk_ref"),
                                             trnIK_ref)

        # Chain --------------------------------------------
        # The outputs of the ikfk2bone solver
        self.bone0 = primitive.addLocator(
            self.root,
            self.getName("0_bone"),
            transform.getTransform(self.fk_ctl[0]))

        self.bone0_shp = self.bone0.getShape()
        self.bone0_shp.setAttr("localPositionX", self.n_factor * .5)
        self.bone0_shp.setAttr("localScale", .5, 0, 0)
        self.bone0.setAttr("sx", self.length0)
        bShape = self.bone0.getShape()
        bShape.setAttr("visibility", False)

        t = transform.getTransform(self.fk_ctl[1])
        self.bone1 = primitive.addLocator(self.root,
                                          self.getName("1_bone"),
                                          t)

        self.bone1_shp = self.bone1.getShape()
        self.bone1_shp.setAttr("localPositionX", self.n_factor * .5)
        self.bone1_shp.setAttr("localScale", .5, 0, 0)
        self.bone1.setAttr("sx", self.length1)
        bShape = self.bone1.getShape()
        bShape.setAttr("visibility", False)

        # Elbow control

        tA = transform.getTransformLookingAt(self.guide.apos[0],
                                             self.guide.apos[1],
                                             self.normal,
                                             "xz",
                                             self.negate)
        tA = transform.setMatrixPosition(tA, self.guide.apos[1])
        tB = transform.getTransformLookingAt(self.guide.apos[1],
                                             self.guide.apos[2],
                                             self.normal,
                                             "xz",
                                             self.negate)

        t = transform.getInterpolateTransformMatrix(tA, tB)
        self.ctrn_loc = primitive.addTransform(self.root,
                                               self.getName("ctrn_loc"),
                                               t)

        # match IK FK references
        self.match_fk0_off = self.add_match_ref(self.fk_ctl[1],
                                                self.root,
                                                "matchFk0_npo",
                                                False)

        self.match_fk0 = self.add_match_ref(self.fk_ctl[0],
                                            self.match_fk0_off,
                                            "fk0_mth")

        self.match_fk1_off = self.add_match_ref(self.fk_ctl[2],
                                                self.root,
                                                "matchFk1_npo",
                                                False)

        self.match_fk1 = self.add_match_ref(self.fk_ctl[1],
                                            self.match_fk1_off,
                                            "fk1_mth")

        if self.settings["ikTR"]:
            reference = self.ikRot_ctl

            self.match_ikRot = self.add_match_ref(self.ikRot_ctl,
                                                  self.fk2_ctl,
                                                  "ikRot_mth")
        else:
            reference = self.ik_ctl

        self.match_fk2 = self.add_match_ref(self.fk_ctl[2],
                                            reference,
                                            "fk2_mth")

        self.match_ik = self.add_match_ref(self.ik_ctl,
                                           self.fk2_ctl,
                                           "ik_mth")

        self.match_ikUpv = self.add_match_ref(self.upv_ctl,
                                              self.fk0_ctl,
                                              "upv_mth")

        # Eff locator
        self.eff_loc = primitive.addTransformFromPos(
            self.root,
            self.getName("eff_loc"),
            self.guide.apos[2])

        # Mid Controler ------------------------------------

        t = transform.getTransform(self.ctrn_loc)
        self.mid_cns = primitive.addTransform(self.ctrn_loc,
                                              self.getName("mid_cns"),
                                              t)
        self.mid_ctl = self.addCtl(self.mid_cns,
                                   "mid_ctl",
                                   t,
                                   self.color_ik,
                                   "sphere",
                                   w=self.size * .2,
                                   tp=self.parentCtlTag)

        if self.settings["mirrorMid"]:
            if self.negate:
                self.mid_cns.rz.set(180)
                self.mid_cns.sz.set(-1)
        else:
            attribute.setInvertMirror(self.mid_ctl, ["tx", "ty", "tz"])
        attribute.setKeyableAttributes(self.mid_ctl, self.t_params)

        # Roll join ref---------------------------------
        self.tws0_loc = primitive.addTransform(
            self.root,
            self.getName("tws0_loc"),
            transform.getTransform(self.fk_ctl[0]))

        self.tws1_npo = primitive.addTransform(
            self.ctrn_loc,
            self.getName("tws1_npo"),
            transform.getTransform(self.ctrn_loc))

        self.tws1_loc = primitive.addTransform(
            self.tws1_npo,
            self.getName("tws1_loc"),
            transform.getTransform(self.ctrn_loc))

        self.tws1A_npo = primitive.addTransform(self.mid_ctl,
                                                self.getName("tws1A_npo"),
                                                tA)
        self.tws1A_loc = primitive.addTransform(self.tws1A_npo,
                                                self.getName("tws1A_loc"),
                                                tA)
        self.tws1B_npo = primitive.addTransform(self.mid_ctl,
                                                self.getName("tws1B_npo"),
                                                tB)
        self.tws1B_loc = primitive.addTransform(self.tws1B_npo,
                                                self.getName("tws1B_loc"),
                                                tB)

        self.tws2_npo = primitive.addTransform(
            self.root,
            self.getName("tws2_npo"),
            transform.getTransform(self.fk_ctl[2]))

        self.tws2_loc = primitive.addTransform(
            self.tws2_npo,
            self.getName("tws2_loc"),
            transform.getTransform(self.fk_ctl[2]))

        # Roll twist chain ---------------------------------
        # Arm
        self.armChainPos = []
        ii = 1.0 / (self.settings["div0"] + 1)
        i = 0.0
        for p in range(self.settings["div0"] + 2):
            p_vec = vector.linearlyInterpolate(self.guide.pos["root"],
                                               self.guide.pos["elbow"],
                                               blend=i)
            self.armChainPos.append(p_vec)
            i = i + ii

        self.armTwistChain = primitive.add2DChain(
            self.root,
            self.getName("armTwist%s_jnt"),
            self.armChainPos,
            self.normal,
            False,
            self.WIP)

        # Forearm
        self.forearmChainPos = []
        ii = 1.0 / (self.settings["div1"] + 1)
        i = 0.0
        for p in range(self.settings["div1"] + 2):
            p_vec = vector.linearlyInterpolate(self.guide.pos["elbow"],
                                               self.guide.pos["wrist"],
                                               blend=i)
            self.forearmChainPos.append(p_vec)
            i = i + ii

        self.forearmTwistChain = primitive.add2DChain(
            self.root,
            self.getName("forearmTwist%s_jnt"),
            self.forearmChainPos,
            self.normal, False,
            self.WIP)
        pm.parent(self.forearmTwistChain[0], self.mid_ctl)

        # Hand Aux chain and nonroll
        self.auxChainPos = []
        ii = .5
        i = 0.0
        for p in range(3):
            p_vec = vector.linearlyInterpolate(self.guide.pos["wrist"],
                                               self.guide.pos["eff"],
                                               blend=i)
            self.auxChainPos.append(p_vec)
            i = i + ii
        t = self.root.getMatrix(worldSpace=True)
        self.aux_npo = primitive.addTransform(self.root,
                                              self.getName("aux_npo"),
                                              t)
        self.auxTwistChain = primitive.add2DChain(
            self.aux_npo,
            self.getName("auxTwist%s_jnt"),
            self.auxChainPos,
            self.normal,
            False,
            self.WIP)

        # Non Roll join ref ---------------------------------
        self.armRollRef = primitive.add2DChain(
            self.root,
            self.getName("armRollRef%s_jnt"),
            self.armChainPos[:2],
            self.normal,
            False,
            self.WIP)

        self.forearmRollRef = primitive.add2DChain(
            self.aux_npo,
            self.getName("forearmRollRef%s_jnt"),
            self.auxChainPos[:2],
            self.normal,
            False,
            self.WIP)

        # Divisions ----------------------------------------
        # We have attribute least one division attribute the start, the end
        # and one for the elbow. + 2 for elbow angle control
        self.divisions = self.settings["div0"] + self.settings["div1"] + 4

        self.div_cns = []
        for i in range(self.divisions):

            div_cns = primitive.addTransform(self.root,
                                             self.getName("div%s_loc" % i))

            self.div_cns.append(div_cns)

            self.jnt_pos.append([div_cns, i])

        # End reference ------------------------------------
        # To help the deformation on the wrist
        self.end_ref = primitive.addTransform(
            self.eff_loc,
            self.getName("end_ref"),
            transform.getTransform(self.eff_loc))
        if self.negate:
            self.end_ref.attr("rz").set(180.0)

        self.jnt_pos.append([self.end_ref, "end"])

        # Tangent controls
        t = transform.getInterpolateTransformMatrix(self.fk_ctl[0],
                                                    self.tws1A_npo,
                                                    .5)
        self.armTangentA_loc = primitive.addTransform(
            self.root,
            self.getName("armTangentA_loc"),
            self.fk_ctl[0].getMatrix(worldSpace=True))

        self.armTangentA_npo = primitive.addTransform(
            self.armTangentA_loc,
            self.getName("armTangentA_npo"),
            t)

        self.armTangentA_ctl = self.addCtl(self.armTangentA_npo,
                                           "armTangentA_ctl",
                                           t,
                                           self.color_ik,
                                           "circle",
                                           w=self.size * .2,
                                           ro=datatypes.Vector(0, 0, 1.570796),
                                           tp=self.mid_ctl)
        if self.settings["mirrorMid"] and self.negate:
            self.armTangentA_npo.sx.set(-1)
        attribute.setKeyableAttributes(self.armTangentA_ctl, self.t_params)

        t = transform.getInterpolateTransformMatrix(self.fk_ctl[0],
                                                    self.tws1A_npo,
                                                    .9)
        self.armTangentB_npo = primitive.addTransform(
            self.tws1A_loc,
            self.getName("armTangentB_npo"),
            t)
        self.armTangentB_ctl = self.addCtl(self.armTangentB_npo,
                                           "armTangentB_ctl",
                                           t,
                                           self.color_ik,
                                           "circle",
                                           w=self.size * .1,
                                           ro=datatypes.Vector(0, 0, 1.570796),
                                           tp=self.mid_ctl)
        if self.settings["mirrorMid"] and self.negate:
            self.armTangentB_npo.rx.set(180)
            self.armTangentB_npo.sx.set(-1)
        attribute.setKeyableAttributes(self.armTangentB_ctl, self.t_params)

        tC = self.tws1B_npo.getMatrix(worldSpace=True)
        tC = transform.setMatrixPosition(tC, self.guide.apos[2])
        t = transform.getInterpolateTransformMatrix(self.tws1B_npo, tC, .1)
        self.forearmTangentA_npo = primitive.addTransform(
            self.tws1B_loc,
            self.getName("forearmTangentA_npo"),
            t)

        self.forearmTangentA_ctl = self.addCtl(
            self.forearmTangentA_npo,
            "forearmTangentA_ctl",
            t,
            self.color_ik,
            "circle",
            w=self.size * .1,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl)

        if self.settings["mirrorMid"] and self.negate:
            self.forearmTangentA_npo.rx.set(180)
            self.forearmTangentA_npo.sx.set(-1)
        attribute.setKeyableAttributes(self.forearmTangentA_ctl, self.t_params)

        t = transform.getInterpolateTransformMatrix(self.tws1B_npo, tC, .5)
        self.forearmTangentB_loc = primitive.addTransform(
            self.root,
            self.getName("forearmTangentB_loc"),
            tC)
        self.forearmTangentB_npo = primitive.addTransform(
            self.forearmTangentB_loc,
            self.getName("forearmTangentB_npo"),
            t)
        self.forearmTangentB_ctl = self.addCtl(
            self.forearmTangentB_npo,
            "forearmTangentB_ctl",
            t,
            self.color_ik,
            "circle",
            w=self.size * .2,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl)

        if self.settings["mirrorMid"] and self.negate:
            self.forearmTangentB_npo.sx.set(-1)
        attribute.setKeyableAttributes(self.forearmTangentB_ctl, self.t_params)

        t = self.mid_ctl.getMatrix(worldSpace=True)
        self.elbowTangent_npo = primitive.addTransform(
            self.mid_ctl,
            self.getName("elbowTangent_npo"),
            t)

        self.elbowTangent_ctl = self.addCtl(
            self.elbowTangent_npo,
            "elbowTangent_ctl",
            t,
            self.color_fk,
            "circle",
            w=self.size * .15,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl)

        attribute.setKeyableAttributes(self.elbowTangent_ctl, self.t_params)

        # add visual reference
        self.line_ref = icon.connection_display_curve(
            self.getName("visalRef"), [self.upv_ctl, self.mid_ctl])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        # Anim -------------------------------------------
        self.blend_att = self.addAnimParam("blend",
                                           "Fk/Ik Blend",
                                           "double",
                                           self.settings["blend"],
                                           0,
                                           1)
        self.roll_att = self.addAnimParam("roll",
                                          "Roll",
                                          "double",
                                          0,
                                          -180,
                                          180)
        self.scale_att = self.addAnimParam("ikscale",
                                           "Scale",
                                           "double",
                                           1,
                                           .001,
                                           99)
        self.maxstretch_att = self.addAnimParam("maxstretch",
                                                "Max Stretch",
                                                "double",
                                                self.settings["maxstretch"],
                                                1,
                                                99)
        self.slide_att = self.addAnimParam("slide",
                                           "Slide",
                                           "double",
                                           .5,
                                           0,
                                           1)
        self.softness_att = self.addAnimParam("softness",
                                              "Softness",
                                              "double",
                                              0,
                                              0,
                                              1)
        self.reverse_att = self.addAnimParam("reverse",
                                             "Reverse",
                                             "double",
                                             0,
                                             0,
                                             1)
        self.roundness_att = self.addAnimParam("roundness",
                                               "Roundness",
                                               "double",
                                               0,
                                               0,
                                               1)
        self.volume_att = self.addAnimParam("volume",
                                            "Volume",
                                            "double",
                                            1,
                                            0,
                                            1)
        self.tangentVis_att = self.addAnimParam("Tangent_vis",
                                                "Tangent vis",
                                                "bool",
                                                False)

        # Ref
        if self.settings["ikrefarray"]:
            ref_names = self.settings["ikrefarray"].split(",")
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam(
                    "ikref",
                    "Ik Ref",
                    0,
                    self.settings["ikrefarray"].split(","))

        if self.settings["ikTR"]:
            ref_names = ["Auto", "ik_ctl"]
            if self.settings["ikrefarray"]:
                ref_names = ref_names + self.settings["ikrefarray"].split(",")
            self.ikRotRef_att = self.addAnimEnumParam("ikRotRef",
                                                      "Ik Rot Ref",
                                                      0,
                                                      ref_names)

        if self.settings["upvrefarray"]:
            ref_names = self.settings["upvrefarray"].split(",")
            ref_names = ["Auto"] + ref_names
            if len(ref_names) > 1:
                self.upvref_att = self.addAnimEnumParam("upvref",
                                                        "UpV Ref",
                                                        0,
                                                        ref_names)

        if self.settings["pinrefarray"]:
            ref_names = self.settings["pinrefarray"].split(",")
            ref_names = ["Auto"] + ref_names
            if len(ref_names) > 1:
                self.pin_att = self.addAnimEnumParam("elbowref",
                                                     "Elbow Ref",
                                                     0,
                                                     ref_names)
        if self.validProxyChannels:
            attribute.addProxyAttribute(
                [self.blend_att, self.roundness_att],
                [self.fk0_ctl,
                    self.fk1_ctl,
                    self.fk2_ctl,
                    self.ik_ctl,
                    self.upv_ctl])
            attribute.addProxyAttribute(self.roll_att,
                                        [self.ik_ctl, self.upv_ctl])

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
                                          self.st_value[i], -1, 0)
                       for i in range(self.divisions)]

        self.sq_att = [self.addSetupParam("squash_%s" % i,
                                          "Squash %s" % i,
                                          "double",
                                          self.sq_value[i],
                                          0,
                                          1)
                       for i in range(self.divisions)]

        self.resample_att = self.addSetupParam("resample",
                                               "Resample",
                                               "bool",
                                               True)
        self.absolute_att = self.addSetupParam("absolute",
                                               "Absolute",
                                               "bool",
                                               False)

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        # 1 bone chain Upv ref ======================================
        self.ikHandleUpvRef = primitive.addIkHandle(
            self.root,
            self.getName("ikHandleLegChainUpvRef"),
            self.armChainUpvRef,
            "ikSCsolver")
        pm.pointConstraint(self.ik_ctl, self.ikHandleUpvRef)
        pm.parentConstraint(self.armChainUpvRef[0], self.upv_cns, mo=True)

        # Visibilities -------------------------------------
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
        if self.settings["ikTR"]:
            for shp in self.ikRot_ctl.getShapes():
                pm.connectAttr(self.blend_att, shp.attr("visibility"))

        # Controls ROT order -----------------------------------
        attribute.setRotOrder(self.fk0_ctl, "XZY")
        attribute.setRotOrder(self.fk1_ctl, "XYZ")
        attribute.setRotOrder(self.fk2_ctl, "YZX")
        attribute.setRotOrder(self.ik_ctl, "XYZ")

        # IK Solver -----------------------------------------
        out = [self.bone0, self.bone1, self.ctrn_loc, self.eff_loc]
        o_node = applyop.gear_ikfk2bone_op(out,
                                           self.root,
                                           self.ik_ref,
                                           self.upv_ctl,
                                           self.fk_ctl[0],
                                           self.fk_ctl[1],
                                           self.fk_ref,
                                           self.length0,
                                           self.length1,
                                           self.negate)

        if self.settings["ikTR"]:
            # connect the control inputs
            outEff_dm = o_node.listConnections(c=True)[-1][1]

            in_attr = self.ikRot_npo.attr("translate")
            outEff_dm.attr("outputTranslate") >> in_attr

            outEff_dm.attr("outputScale") >> self.ikRot_npo.attr("scale")
            dm_node = node.createDecomposeMatrixNode(o_node.attr("outB"))
            dm_node.attr("outputRotate") >> self.ikRot_npo.attr("rotate")

            # rotation

            mulM_node = applyop.gear_mulmatrix_op(
                self.ikRot_ctl.attr("worldMatrix"),
                self.eff_loc.attr("parentInverseMatrix"))

            intM_node = applyop.gear_intmatrix_op(o_node.attr("outEff"),
                                                  mulM_node.attr("output"),
                                                  o_node.attr("blend"))
            dm_node = node.createDecomposeMatrixNode(intM_node.attr("output"))
            dm_node.attr("outputRotate") >> self.eff_loc.attr("rotate")
            transform.matchWorldTransform(self.fk2_ctl, self.ikRot_cns)

        # scale: this fix the scalin popping issue
        intM_node = applyop.gear_intmatrix_op(
            self.fk2_ctl.attr("worldMatrix"),
            self.ik_ctl_ref.attr("worldMatrix"),
            o_node.attr("blend"))

        mulM_node = applyop.gear_mulmatrix_op(
            intM_node.attr("output"),
            self.eff_loc.attr("parentInverseMatrix"))

        dm_node = node.createDecomposeMatrixNode(mulM_node.attr("output"))
        dm_node.attr("outputScale") >> self.eff_loc.attr("scale")

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

        o_node = applyop.gear_mulmatrix_op(
            self.eff_loc.attr("worldMatrix"),
            self.root.attr("worldInverseMatrix"))

        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(o_node + ".output", dm_node + ".inputMatrix")
        pm.connectAttr(dm_node + ".outputTranslate",
                       self.tws2_npo.attr("translate"))

        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(o_node + ".output", dm_node + ".inputMatrix")
        pm.connectAttr(dm_node + ".outputRotate", self.tws2_npo.attr("rotate"))

        # spline IK for  twist jnts
        self.ikhArmTwist, self.armTwistCrv = applyop.splineIK(
            self.getName("armTwist"),
            self.armTwistChain,
            parent=self.root,
            cParent=self.bone0)

        self.ikhForearmTwist, self.forearmTwistCrv = applyop.splineIK(
            self.getName("forearmTwist"),
            self.forearmTwistChain,
            parent=self.root,
            cParent=self.bone1)

        # references
        self.ikhArmRef, self.tmpCrv = applyop.splineIK(
            self.getName("armRollRef"),
            self.armRollRef,
            parent=self.root,
            cParent=self.bone0)

        self.ikhForearmRef, self.tmpCrv = applyop.splineIK(
            self.getName("forearmRollRef"),
            self.forearmRollRef,
            parent=self.root,
            cParent=self.eff_loc)

        self.ikhAuxTwist, self.tmpCrv = applyop.splineIK(
            self.getName("auxTwist"),
            self.auxTwistChain,
            parent=self.root,
            cParent=self.eff_loc)

        # setting connexions for ikhArmTwist
        self.ikhArmTwist.attr("dTwistControlEnable").set(True)
        self.ikhArmTwist.attr("dWorldUpType").set(4)
        self.ikhArmTwist.attr("dWorldUpAxis").set(3)
        self.ikhArmTwist.attr("dWorldUpVectorZ").set(1.0)
        self.ikhArmTwist.attr("dWorldUpVectorY").set(0.0)
        self.ikhArmTwist.attr("dWorldUpVectorEndZ").set(1.0)
        self.ikhArmTwist.attr("dWorldUpVectorEndY").set(0.0)

        pm.connectAttr(self.armRollRef[0].attr("worldMatrix[0]"),
                       self.ikhArmTwist.attr("dWorldUpMatrix"))
        pm.connectAttr(self.bone0.attr("worldMatrix[0]"),
                       self.ikhArmTwist.attr("dWorldUpMatrixEnd"))

        # setting connexions for ikhAuxTwist
        self.ikhAuxTwist.attr("dTwistControlEnable").set(True)
        self.ikhAuxTwist.attr("dWorldUpType").set(4)
        self.ikhAuxTwist.attr("dWorldUpAxis").set(3)
        self.ikhAuxTwist.attr("dWorldUpVectorZ").set(1.0)
        self.ikhAuxTwist.attr("dWorldUpVectorY").set(0.0)
        self.ikhAuxTwist.attr("dWorldUpVectorEndZ").set(1.0)
        self.ikhAuxTwist.attr("dWorldUpVectorEndY").set(0.0)
        pm.connectAttr(self.forearmRollRef[0].attr("worldMatrix[0]"),
                       self.ikhAuxTwist.attr("dWorldUpMatrix"))
        pm.connectAttr(self.eff_loc.attr("worldMatrix[0]"),
                       self.ikhAuxTwist.attr("dWorldUpMatrixEnd"))
        pm.connectAttr(self.auxTwistChain[1].attr("rx"),
                       self.ikhForearmTwist.attr("twist"))

        pm.parentConstraint(self.bone1, self.aux_npo, maintainOffset=True)

        # scale arm length for twist chain (not the squash and stretch)
        arclen_node = pm.arclen(self.armTwistCrv, ch=True)
        alAttrArm = arclen_node.attr("arcLength")
        muldiv_nodeArm = pm.createNode("multiplyDivide")
        pm.connectAttr(arclen_node.attr("arcLength"),
                       muldiv_nodeArm.attr("input1X"))
        muldiv_nodeArm.attr("input2X").set(alAttrArm.get())
        muldiv_nodeArm.attr("operation").set(2)
        for jnt in self.armTwistChain:
            pm.connectAttr(muldiv_nodeArm.attr("outputX"), jnt.attr("sx"))

        # scale forearm length for twist chain (not the squash and stretch)
        arclen_node = pm.arclen(self.forearmTwistCrv, ch=True)
        alAttrForearm = arclen_node.attr("arcLength")
        muldiv_nodeForearm = pm.createNode("multiplyDivide")
        pm.connectAttr(arclen_node.attr("arcLength"),
                       muldiv_nodeForearm.attr("input1X"))
        muldiv_nodeForearm.attr("input2X").set(alAttrForearm.get())
        muldiv_nodeForearm.attr("operation").set(2)
        for jnt in self.forearmTwistChain:
            pm.connectAttr(muldiv_nodeForearm.attr("outputX"), jnt.attr("sx"))

        # scale compensation for the first  twist join
        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(self.root.attr("worldMatrix[0]"),
                       dm_node.attr("inputMatrix"))
        pm.connectAttr(dm_node.attr("outputScale"),
                       self.armTwistChain[0].attr("inverseScale"))
        pm.connectAttr(dm_node.attr("outputScale"),
                       self.forearmTwistChain[0].attr("inverseScale"))

        # tangent controls
        muldiv_node = pm.createNode("multiplyDivide")
        muldiv_node.attr("input2X").set(-1)
        pm.connectAttr(self.tws1A_npo.attr("rz"), muldiv_node.attr("input1X"))
        muldiv_nodeBias = pm.createNode("multiplyDivide")
        pm.connectAttr(muldiv_node.attr("outputX"),
                       muldiv_nodeBias.attr("input1X"))
        pm.connectAttr(self.roundness_att, muldiv_nodeBias.attr("input2X"))
        pm.connectAttr(muldiv_nodeBias.attr("outputX"),
                       self.tws1A_loc.attr("rz"))
        if self.negate:
            axis = "xz"
        else:
            axis = "-xz"
        applyop.aimCns(self.tws1A_npo,
                       self.tws0_loc,
                       axis=axis,
                       wupType=2,
                       wupVector=[0, 0, 1],
                       wupObject=self.mid_ctl,
                       maintainOffset=False)

        applyop.aimCns(self.forearmTangentB_loc,
                       self.forearmTangentA_npo,
                       axis=axis,
                       wupType=2,
                       wupVector=[0, 0, 1],
                       wupObject=self.mid_ctl,
                       maintainOffset=False)

        pm.pointConstraint(self.eff_loc, self.forearmTangentB_loc)

        muldiv_node = pm.createNode("multiplyDivide")
        muldiv_node.attr("input2X").set(-1)
        pm.connectAttr(self.tws1B_npo.attr("rz"), muldiv_node.attr("input1X"))
        muldiv_nodeBias = pm.createNode("multiplyDivide")
        pm.connectAttr(muldiv_node.attr("outputX"),
                       muldiv_nodeBias.attr("input1X"))
        pm.connectAttr(self.roundness_att,
                       muldiv_nodeBias.attr("input2X"))
        pm.connectAttr(muldiv_nodeBias.attr("outputX"),
                       self.tws1B_loc.attr("rz"))
        if self.negate:
            axis = "-xz"
        else:
            axis = "xz"
        applyop.aimCns(self.tws1B_npo,
                       self.tws2_loc,
                       axis=axis,
                       wupType=2,
                       wupVector=[0, 0, 1],
                       wupObject=self.mid_ctl,
                       maintainOffset=False)

        applyop.aimCns(self.armTangentA_loc,
                       self.armTangentB_npo,
                       axis=axis,
                       wupType=2,
                       wupVector=[0, 0, 1],
                       wupObject=self.mid_ctl,
                       maintainOffset=False)

        # Volume -------------------------------------------
        distA_node = node.createDistNode(self.tws0_loc, self.tws1_loc)
        distB_node = node.createDistNode(self.tws1_loc, self.tws2_loc)
        add_node = node.createAddNode(distA_node + ".distance",
                                      distB_node + ".distance")
        div_node = node.createDivNode(add_node + ".output",
                                      self.root.attr("sx"))

        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(self.root.attr("worldMatrix"), dm_node + ".inputMatrix")

        div_node2 = node.createDivNode(div_node + ".outputX",
                                       dm_node + ".outputScaleX")
        self.volDriver_att = div_node2 + ".outputX"

        # connecting tangent scaele compensation after
        # volume to avoid duplicate some nodes
        distA_node = node.createDistNode(self.tws0_loc, self.mid_ctl)
        distB_node = node.createDistNode(self.mid_ctl, self.tws2_loc)

        div_nodeArm = node.createDivNode(distA_node + ".distance",
                                         dm_node.attr("outputScaleX"))
        div_node2 = node.createDivNode(div_nodeArm + ".outputX",
                                       distA_node.attr("distance").get())
        pm.connectAttr(div_node2.attr("outputX"),
                       self.tws1A_loc.attr("sx"))
        pm.connectAttr(div_node2.attr("outputX"),
                       self.armTangentA_loc.attr("sx"))

        div_nodeForearm = node.createDivNode(distB_node + ".distance",
                                             dm_node.attr("outputScaleX"))
        div_node2 = node.createDivNode(div_nodeForearm + ".outputX",
                                       distB_node.attr("distance").get())
        pm.connectAttr(div_node2.attr("outputX"),
                       self.tws1B_loc.attr("sx"))
        pm.connectAttr(div_node2.attr("outputX"),
                       self.forearmTangentB_loc.attr("sx"))

        # conection curve
        cns_list = [self.armTangentA_loc, self.armTangentA_ctl,
                    self.armTangentB_ctl, self.elbowTangent_ctl]
        applyop.gear_curvecns_op(self.armTwistCrv, cns_list)

        cns_list = [self.elbowTangent_ctl, self.forearmTangentA_ctl,
                    self.forearmTangentB_ctl, self.forearmTangentB_loc]
        applyop.gear_curvecns_op(self.forearmTwistCrv, cns_list)

        # Tangent controls vis
        for shp in self.armTangentA_ctl.getShapes():
            pm.connectAttr(self.tangentVis_att, shp.attr("visibility"))
        for shp in self.armTangentB_ctl.getShapes():
            pm.connectAttr(self.tangentVis_att, shp.attr("visibility"))
        for shp in self.forearmTangentA_ctl.getShapes():
            pm.connectAttr(self.tangentVis_att, shp.attr("visibility"))
        for shp in self.forearmTangentB_ctl.getShapes():
            pm.connectAttr(self.tangentVis_att, shp.attr("visibility"))
        for shp in self.elbowTangent_ctl.getShapes():
            pm.connectAttr(self.tangentVis_att, shp.attr("visibility"))

        # Divisions ----------------------------------------
        # attribute 0 or 1 the division will follow exactly the rotation of
        # the controler.. and we wont have this nice tangent + roll
        for i, div_cns in enumerate(self.div_cns):
            if i < (self.settings["div0"] + 2):
                mulmat_node = applyop.gear_mulmatrix_op(
                    self.armTwistChain[i] + ".worldMatrix",
                    div_cns + ".parentInverseMatrix")
                lastArmDiv = div_cns
            else:
                ftc = self.forearmTwistChain[i - (self.settings["div0"] + 2)]
                mulmat_node = applyop.gear_mulmatrix_op(
                    ftc + ".worldMatrix",
                    div_cns + ".parentInverseMatrix")
                lastForeDiv = div_cns

            dm_node = node.createDecomposeMatrixNode(mulmat_node + ".output")
            pm.connectAttr(dm_node + ".outputTranslate", div_cns + ".t")
            pm.connectAttr(dm_node + ".outputRotate", div_cns + ".r")

            # Squash n Stretch
            o_node = applyop.gear_squashstretch2_op(
                div_cns,
                None,
                pm.getAttr(self.volDriver_att),
                "x")
            pm.connectAttr(self.volume_att, o_node + ".blend")
            pm.connectAttr(self.volDriver_att, o_node + ".driver")
            pm.connectAttr(self.st_att[i], o_node + ".stretch")
            pm.connectAttr(self.sq_att[i], o_node + ".squash")

        # force translation for last loc arm and foreamr
        applyop.gear_mulmatrix_op(self.elbowTangent_ctl.worldMatrix,
                                  lastArmDiv.parentInverseMatrix,
                                  lastArmDiv,
                                  "t")
        applyop.gear_mulmatrix_op(self.tws2_loc.worldMatrix,
                                  lastForeDiv.parentInverseMatrix,
                                  lastForeDiv,
                                  "t")

        # return

        # NOTE: next line fix the issue on meters.
        # This is special case becasuse the IK solver from mGear use the scale
        # as lenght and we have shear
        # TODO: check for a more clean and elegant solution instead of re-match
        # the world matrix again
        transform.matchWorldTransform(self.fk_ctl[0], self.match_fk0_off)
        transform.matchWorldTransform(self.fk_ctl[1], self.match_fk1_off)
        transform.matchWorldTransform(self.fk_ctl[0], self.match_fk0)
        transform.matchWorldTransform(self.fk_ctl[1], self.match_fk1)

        # match IK/FK ref
        pm.parentConstraint(self.bone0, self.match_fk0_off, mo=True)
        pm.parentConstraint(self.bone1, self.match_fk1_off, mo=True)
        if self.settings["ikTR"]:
            transform.matchWorldTransform(self.ikRot_ctl, self.match_ikRot)
            transform.matchWorldTransform(self.fk_ctl[2], self.match_fk2)

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.div_cns[0]
        self.relatives["elbow"] = self.div_cns[self.settings["div0"] + 2]
        self.relatives["wrist"] = self.div_cns[-1]
        self.relatives["eff"] = self.eff_loc

        self.jointRelatives["root"] = 0
        self.jointRelatives["elbow"] = self.settings["div0"] + 2
        self.jointRelatives["wrist"] = len(self.div_cns) - 2
        self.jointRelatives["eff"] = -1

        self.controlRelatives["root"] = self.fk0_ctl
        self.controlRelatives["elbow"] = self.fk1_ctl
        self.controlRelatives["wrist"] = self.fk2_ctl
        self.controlRelatives["eff"] = self.fk2_ctl

    def addConnection(self):
        """Add more connection definition to the set"""

        self.connections["shoulder_01"] = self.connect_shoulder_01

    def connect_standard(self):
        """standard connection definition for the component"""

        if self.settings["ikTR"]:
            self.parent.addChild(self.root)
            self.connectRef(self.settings["ikrefarray"], self.ik_cns)
            self.connectRef(self.settings["upvrefarray"], self.upv_cns, True)

            if self.settings["ikrefarray"]:
                ikRotRefArray = "Auto,ik_ctl," + self.settings["ikrefarray"]
            else:
                ikRotRefArray = "Auto,ik_ctl"
            self.connectRef2(ikRotRefArray,
                             self.ikRot_cns,
                             self.ikRotRef_att,
                             [self.ikRot_npo, self.ik_ctl],
                             True)
        else:
            self.connect_standardWithIkRef()

        if self.settings["pinrefarray"]:
            self.connectRef2("Auto," + self.settings["pinrefarray"],
                             self.mid_cns,
                             self.pin_att,
                             [self.ctrn_loc],
                             False)

    def connect_shoulder_01(self):
        """ Custom connection to be use with shoulder 01 component"""

        self.connect_standard()
        pm.parent(self.armRollRef[0],
                  self.ikHandleUpvRef,
                  self.parent_comp.ctl)
