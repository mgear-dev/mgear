import ast
import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import node, fcurve, applyop, vector, icon
from mgear.core import attribute, transform, primitive, string

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
        self.up_axis = pm.upAxis(q=True, axis=True)

        self.length0 = vector.getDistance(
            self.guide.apos[0], self.guide.apos[1]
        )
        self.length1 = vector.getDistance(
            self.guide.apos[1], self.guide.apos[2]
        )
        self.length2 = vector.getDistance(
            self.guide.apos[2], self.guide.apos[3]
        )

        # custom colors
        self.color_offset_fk = [1, 0.25, 0]  # orange

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
        # FK 0
        t = transform.getTransformLookingAt(
            self.guide.apos[0],
            self.guide.apos[1],
            self.normal,
            "xz",
            self.negate,
        )
        if self.settings["rest_T_Pose"]:
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
        self.fk0_ctl = self.addCtl(
            self.fk0_npo,
            "fk0_ctl",
            t,
            self.color_fk,
            "circle",
            w=self.size * 0.3,
            ro=datatypes.Vector([0, 0, 1.5708]),
            tp=self.parentCtlTag,
        )

        # FK 1
        t = transform.getTransformLookingAt(
            self.guide.apos[1],
            self.guide.apos[2],
            self.normal,
            "xz",
            self.negate,
        )

        if self.settings["rest_T_Pose"]:
            t_npo = transform.setMatrixPosition(
                transform.getTransform(self.fk0_ctl), self.guide.apos[1]
            )
        else:
            t_npo = t

        self.fk1_npo = primitive.addTransform(
            self.fk0_ctl, self.getName("fk1_npo"), t_npo
        )

        self.fk1_ctl = self.addCtl(
            self.fk1_npo,
            "fk1_ctl",
            t,
            self.color_fk,
            "circle",
            w=self.size * 0.3,
            ro=datatypes.Vector([0, 0, 1.5708]),
            tp=self.fk0_ctl,
        )

        for f_ctl in [
            self.fk0_ctl,
            self.fk1_ctl,
        ]:
            attribute.setKeyableAttributes(
                f_ctl, ["tx", "ty", "tz", "ro", "rx", "ry", "rz"]
            )

        # FK 2
        t = transform.getTransformLookingAt(
            self.guide.apos[2],
            self.guide.apos[3],
            self.normal,
            "xz",
            self.negate,
        )

        if self.settings["rest_T_Pose"]:
            t_npo = transform.setMatrixPosition(
                transform.getTransform(self.fk0_ctl), self.guide.apos[2]
            )
        else:
            t_npo = t

        self.fk2_npo = primitive.addTransform(
            self.fk1_ctl, self.getName("fk2_npo"), t_npo
        )

        if self.settings["rest_T_Pose"]:
            self.fk2_npo.rz.set(90)

        self.fk2_ctl = self.addCtl(
            self.fk2_npo,
            "fk2_ctl",
            t,
            self.color_fk,
            "circle",
            w=self.size * 0.3,
            ro=datatypes.Vector([0, 0, 1.5708]),
            tp=self.fk1_ctl,
        )
        attribute.setKeyableAttributes(self.fk2_ctl)

        self.fk_ctl = [self.fk0_ctl, self.fk1_ctl, self.fk2_ctl]

        for x in self.fk_ctl:
            attribute.setInvertMirror(x, ["tx", "ty", "tz"])

        # IK upv ---------------------------------

        # create tip point
        self.tip_ref = primitive.addTransform(
            self.legChainUpvRef[0],
            self.getName("tip_ref"),
            self.legChainUpvRef[0].getMatrix(worldSpace=True),
        )

        # create interpolate obj
        self.interpolate_lvl = primitive.addTransform(
            self.legChainUpvRef[0],
            self.getName("int_lvl"),
            self.legChainUpvRef[0].getMatrix(worldSpace=True),
        )

        # create roll npo and ctl
        self.roll_ctl_npo = primitive.addTransform(
            self.root,
            self.getName("roll_ctl_npo"),
            self.legChainUpvRef[0].getMatrix(worldSpace=True),
        )
        if self.negate:
            off_x = -1.5708
        else:
            off_x = 1.5708
        off_y = 1.5708

        self.roll_ctl = self.addCtl(
            self.roll_ctl_npo,
            "roll_ctl",
            transform.getTransform(self.roll_ctl_npo),
            self.color_ik,
            "compas",
            w=self.size * 0.3,
            ro=datatypes.Vector([off_x, off_y, 0]),
            tp=self.parentCtlTag,
        )
        attribute.setKeyableAttributes(self.roll_ctl, ["rx"])
        # create upv control
        v = self.guide.apos[2] - self.guide.apos[0]
        v = self.normal ^ v
        v.normalize()
        v *= self.size * 0.8
        v += self.guide.apos[1]

        self.upv_cns = primitive.addTransformFromPos(
            self.root, self.getName("upv_cns"), v
        )

        self.upv_ctl = self.addCtl(
            self.upv_cns,
            "upv_ctl",
            transform.getTransform(self.upv_cns),
            self.color_ik,
            "diamond",
            w=self.size * 0.12,
            tp=self.parentCtlTag,
        )

        if self.settings["mirrorMid"]:
            if self.negate:
                self.upv_cns.rz.set(180)
                self.upv_cns.sy.set(-1)
        else:
            attribute.setInvertMirror(self.upv_ctl, ["tx"])
        attribute.setKeyableAttributes(self.upv_ctl, self.t_params)

        # IK Controlers -----------------------------------

        if self.settings["rest_T_Pose"]:
            leg_length = vector.getDistance(
                self.guide.pos["root"], self.guide.pos["knee"]
            ) + vector.getDistance(
                self.guide.pos["knee"], self.guide.pos["ankle"]
            )
            if self.up_axis == "y":
                ankle_pos = self.guide.pos["root"] - datatypes.Vector(
                    0, leg_length, 0
                )
            else:
                ankle_pos = self.guide.pos["root"] - datatypes.Vector(
                    0, 0, leg_length
                )

        else:
            ankle_pos = self.guide.pos["ankle"]

        self.ik_cns = primitive.addTransformFromPos(
            self.root_ctl, self.getName("ik_cns"), ankle_pos
        )

        t = transform.getTransformFromPos(ankle_pos)
        self.ikcns_ctl = self.addCtl(
            self.ik_cns,
            "ikcns_ctl",
            t,
            self.color_ik,
            "null",
            w=self.size * 0.12,
            tp=self.root_ctl,
        )

        attribute.setInvertMirror(self.ikcns_ctl, ["tx"])

        m = transform.getTransformFromPos(self.guide.pos["ankle"])

        self.ik_ctl = self.addCtl(
            self.ikcns_ctl,
            "ik_ctl",
            m,
            self.color_ik,
            "cube",
            w=self.size * 0.12,
            h=self.size * 0.12,
            d=self.size * 0.12,
            tp=self.roll_ctl,
        )

        pos = self.guide.pos["ankle"]
        pos[1] = 0
        self.ik_squash = primitive.addTransformFromPos(
            self.ik_ctl, self.getName("ik_squash"), pos
        )
        attribute.setKeyableAttributes(self.ik_ctl)
        attribute.setRotOrder(self.ik_ctl, "XZY")
        attribute.setInvertMirror(self.ik_ctl, ["tx", "ry", "rz"])

        self.fk_ik_ctls = self.fk_ctl + [self.ik_ctl]

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

        # Elbow bone1 ref
        t = transform.getTransform(self.fk_ctl[1])
        self.knee_ref = primitive.addTransform(
            self.root, self.getName("knee_ref"), t
        )

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
            self.negate,
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
            self.negate,
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
        self.extra_div = 2
        self.divisions = (
            self.settings["div0"] + self.settings["div1"] + self.extra_div
        )

        tagP = self.parentCtlTag
        self.tweak_npo = []
        self.tweak_ctl = []
        self.div_cns = []
        self.roll_offset = []

        # joint Description Name
        jd_names = ast.literal_eval(
            self.settings["jointNamesDescription_custom"]
        )
        jdn_thigh = jd_names[0]
        jdn_calf = jd_names[1]
        jdn_thigh_twist = jd_names[2]
        jdn_calf_twist = jd_names[3]
        jdn_foot = jd_names[4]
        for i in range(self.divisions):
            div_cns = primitive.addTransform(
                self.root_ctl, self.getName("div%s_loc" % i)
            )

            self.div_cns.append(div_cns)

            t = transform.getTransform(div_cns)
            tweak_npo = primitive.addTransform(
                div_cns, self.getName("tweak%s_npo" % i)
            )
            self.tweak_npo.append(tweak_npo)
            tweak_ctl = self.addCtl(
                tweak_npo,
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

            roll_off = primitive.addTransform(
                tweak_ctl, self.getName("roll%s_off" % i)
            )

            self.roll_offset.append(roll_off)

            # setting the joints
            # auto rotation offset
            rot_off = [
                self.settings["joint_rot_offset_x"],
                self.settings["joint_rot_offset_y"],
                self.settings["joint_rot_offset_z"] + 180,
            ]
            if i == 0:
                root_leaf = False
                if self.settings["div0"]:
                    self.leg_root_base = primitive.addTransform(self.root, self.getName("divRoot_loc"))
                else:
                    if self.settings["leafJoints"]:
                        root_leaf = True
                    self.leg_root_base = roll_off

                if self.negate:
                    rot_off_root = None
                else:
                    rot_off_root = rot_off

                self.jnt_pos.append(
                    {
                        "obj": self.leg_root_base,
                        "name": jdn_thigh,
                        "guide_relative": "root",
                        "data_contracts": "Ik",
                        "leaf_joint": root_leaf,
                        "rot_off": rot_off_root,
                    }
                )
                current_parent = "root"
                twist_name = jdn_thigh_twist
                twist_idx = 1
                increment = 1
                # extra joint twist/swing
                if self.settings["div0"]:
                    self.jnt_pos.append(
                        {
                            "obj": roll_off,
                            "name": jdn_thigh + "_swing",
                            "leaf_joint": self.settings["leafJoints"],
                            "data_contracts": "Twist,Squash",
                            "newActiveJnt": current_parent,
                            "rot_off": rot_off_root,
                        }
                    )
            elif i == self.settings["div0"] + 1:
                self.jnt_pos.append(
                    {
                        "obj": roll_off,
                        "name": jdn_calf,
                        "newActiveJnt": current_parent,
                        "guide_relative": "knee",
                        "data_contracts": "Ik",
                        "leaf_joint": self.settings["leafJoints"],
                        "rot_off": rot_off,
                    }
                )
                twist_name = jdn_calf_twist
                current_parent = "knee"
                twist_idx = self.settings["div1"]
                increment = -1
            else:
                self.jnt_pos.append(
                    {
                        "obj": roll_off,
                        "name": string.replaceSharpWithPadding(
                            twist_name, twist_idx
                        ),
                        "newActiveJnt": current_parent,
                        "data_contracts": "Twist,Squash",
                        "rot_off": rot_off,
                    }
                )
                twist_idx += increment

        # End reference ------------------------------------
        # To help the deformation on the ankle
        self.end_ref = primitive.addTransform(
            self.eff_loc, self.getName("end_ref"), m
        )
        for a in "xyz":
            self.end_ref.attr("s%s" % a).set(1.0)
        if self.negate:
            self.end_ref.attr("ry").set(-180.0)

        t = transform.getTransform(self.end_ref)
        pos = self.guide.pos["ankle"]
        pos[1] = 0
        self.tweak_scl = primitive.addTransformFromPos(
            self.end_ref, self.getName("tweakEnd_scl"), pos
        )
        tweak_npo = primitive.addTransform(
            self.tweak_scl, self.getName("tweakEnd_npo"), t
        )
        tweak_ctl = self.addCtl(
            tweak_npo,
            "tweakEnd_ctl",
            t,
            self.color_fk,
            "square",
            w=self.size * 0.15,
            d=self.size * 0.15,
            ro=datatypes.Vector([0, 0, 1.5708]),
            tp=tagP,
        )
        attribute.setKeyableAttributes(tweak_ctl)
        self.tweak_ctl.append(tweak_ctl)

        # set offset orientation to match EPIC standard orientation
        self.end_jnt_off = primitive.addTransform(
            tweak_ctl, self.getName("end_off"), m
        )
        if self.up_axis == "z":
            if self.negate:
                self.end_jnt_off.rz.set(-180)

        self.jnt_pos.append(
            {
                "obj": self.end_jnt_off,
                "name": jdn_foot,
                "newActiveJnt": current_parent,
                "guide_relative": "ankle",
                "data_contracts": "Ik",
                "leaf_joint": self.settings["leafJoints"],
                "rot_off": rot_off,
            }
        )

        # Bendy controls
        t = transform.getInterpolateTransformMatrix(
            self.fk_ctl[0], self.tws1A_npo, 0.5
        )
        self.uplegBendyA_loc = primitive.addTransform(
            self.root_ctl,
            self.getName("uplegBendyA_loc"),
            self.fk_ctl[0].getMatrix(worldSpace=True),
        )

        self.uplegBendyA_npo = primitive.addTransform(
            self.uplegBendyA_loc, self.getName("uplegBendyA_npo"), t
        )

        self.uplegBendyA_ctl = self.addCtl(
            self.uplegBendyA_npo,
            "uplegBendyA_ctl",
            t,
            self.color_ik,
            "circle",
            w=self.size * 0.2,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl,
        )

        if self.negate and self.settings["mirrorMid"]:
            self.uplegBendyA_npo.sx.set(-1)
        elif self.negate:
            self.uplegBendyA_npo.rz.set(180)
            self.uplegBendyA_npo.sz.set(-1)

        attribute.setKeyableAttributes(self.uplegBendyA_ctl, self.t_params)

        t = transform.getInterpolateTransformMatrix(
            self.fk_ctl[0], self.tws1A_npo, 0.9
        )
        self.uplegBendyB_npo = primitive.addTransform(
            self.tws1A_loc, self.getName("uplegBendyB_npo"), t
        )

        self.uplegBendyB_ctl = self.addCtl(
            self.uplegBendyB_npo,
            "uplegBendyB_ctl",
            t,
            self.color_ik,
            "circle",
            w=self.size * 0.1,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl,
        )

        if self.negate and self.settings["mirrorMid"]:
            self.uplegBendyB_npo.sx.set(-1)
            self.uplegBendyB_npo.sy.set(-1)
            self.uplegBendyB_npo.sz.set(-1)
        elif self.negate:
            self.uplegBendyB_npo.rz.set(180)
            self.uplegBendyB_npo.sz.set(-1)

        attribute.setKeyableAttributes(self.uplegBendyB_ctl, self.t_params)

        tC = self.tws1B_npo.getMatrix(worldSpace=True)
        tC = transform.setMatrixPosition(tC, self.guide.apos[2])
        t = transform.getInterpolateTransformMatrix(self.tws1B_npo, tC, 0.1)
        self.lowlegBendyA_npo = primitive.addTransform(
            self.tws1B_loc, self.getName("lowlegBendyA_npo"), t
        )

        self.lowlegBendyA_ctl = self.addCtl(
            self.lowlegBendyA_npo,
            "lowlegBendyA_ctl",
            t,
            self.color_ik,
            "circle",
            w=self.size * 0.1,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl,
        )

        if self.negate and self.settings["mirrorMid"]:
            self.lowlegBendyA_npo.sx.set(-1)
            self.lowlegBendyA_npo.sy.set(-1)
            self.lowlegBendyA_npo.sz.set(-1)
        elif self.negate:
            self.lowlegBendyA_npo.rz.set(180)
            self.lowlegBendyA_npo.sz.set(-1)

        attribute.setKeyableAttributes(self.lowlegBendyA_ctl, self.t_params)

        t = transform.getInterpolateTransformMatrix(self.tws1B_npo, tC, 0.5)

        self.lowlegBendyB_loc = primitive.addTransform(
            self.root, self.getName("lowlegBendyB_loc"), tC
        )

        self.lowlegBendyB_npo = primitive.addTransform(
            self.lowlegBendyB_loc, self.getName("lowlegBendyB_npo"), t
        )

        self.lowlegBendyB_ctl = self.addCtl(
            self.lowlegBendyB_npo,
            "lowlegBendyB_ctl",
            t,
            self.color_ik,
            "circle",
            w=self.size * 0.2,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl,
        )

        if self.negate and self.settings["mirrorMid"]:
            self.lowlegBendyB_npo.sx.set(-1)
        elif self.negate:
            self.lowlegBendyB_npo.rz.set(180)
            self.lowlegBendyB_npo.sz.set(-1)

        attribute.setKeyableAttributes(self.lowlegBendyB_ctl, self.t_params)

        t = self.mid_ctl.getMatrix(worldSpace=True)
        self.kneeBendy_npo = primitive.addTransform(
            self.mid_ctl, self.getName("kneeBendy_npo"), t
        )

        self.kneeBendy_ctl = self.addCtl(
            self.kneeBendy_npo,
            "kneeBendy_ctl",
            t,
            self.color_fk,
            "circle",
            w=self.size * 0.25,
            ro=datatypes.Vector(0, 0, 1.570796),
            tp=self.mid_ctl,
        )

        if self.negate:
            self.kneeBendy_npo.rz.set(180)
            self.kneeBendy_npo.sz.set(-1)
        attribute.setKeyableAttributes(self.kneeBendy_ctl, self.t_params)

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
            "roll", "Roll upv", "double", 0, -180, 180, uihost=self.ik_ctl
        )
        self.legBaseRoll_att = self.addAnimParam(
            "legBaseRoll", "Leg Base Roll", "double", 0
        )
        self.scale_att = self.addAnimParam(
            "ikscale", "Scale", "double", 1, 0.001, 10
        )
        self.maxstretch_att = self.addAnimParam(
            "maxstretch",
            "Max Stretch",
            "double",
            self.settings["maxstretch"],
            1,
            100,
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
            "volume", "Volume Joint Scale", "double", 0, 0, 1
        )

        self.rootVis_att = self.addAnimParam(
            "root_ctl_vis", "Root Ctl vis", "bool", False
        )
        self.bendyVis_att = self.addAnimParam(
            "Bendy_vis", "Bendy vis", "bool", False
        )
        self.kneeBendyVis_att = self.addAnimParam(
            "kneeBendy_vis", "Knee Bendy vis", "bool", False
        )

        self.upvAimVis_att = self.addAnimParam(
            "UpvAim_vis", "Upv Aim vis", "bool", True
        )
        self.upvCtlVis_att = self.addAnimParam(
            "UpvCtl_vis", "Upv Roll Ctl vis", "bool", False
        )

        self.tweakVis_att = self.addAnimParam(
            "Tweak_vis", "Tweak Vis", "bool", False
        )
        self.midCtl_att = self.addAnimParam(
            "mid_ctl_vis", "Mid Ctl Vis", "bool", False
        )
        self.ikCnsCtl_att = self.addAnimParam(
            "ik_cns_ctl_vis", "IK Cns Ctl Vis", "bool", False
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

        ref_names = ["Auto", "ikFoot", "World_ctl"]
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
        self.volume_blenshape_att = self.addSetupParam(
            "volume_blendshape", "Volume Blendshape", "double", 0, 0, 10
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
        # handle special case for full mirror behaviour negating
        # scaleY axis to -1
        if self.upv_cns.sy.get() < 0:
            references = []
            for x in [self.legChainUpvRef[0], self.ik_ctl]:
                ref_trans_name = (
                    self.upv_cns.getName() + "_" + x.getName() + "_space_ref"
                )
                ref_trans = primitive.addTransform(
                    x,
                    ref_trans_name,
                )
                transform.matchWorldTransform(self.upv_cns, ref_trans)
                references.append(ref_trans)
            pm.parentConstraint(
                references[0], references[1], self.upv_cns, mo=True
            )
        else:
            pm.parentConstraint(
                self.legChainUpvRef[0], self.ik_ctl, self.upv_cns, mo=True
            )

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
            pm.connectAttr(self.ikCnsCtl_att, shp.attr("visibility"))
        for shp in self.ik_ctl.getShapes():
            pm.connectAttr(self.blend_att, shp.attr("visibility"))
        for shp in self.line_ref.getShapes():
            pm.connectAttr(self.blend_att, shp.attr("visibility"))

        for shp in self.roll_ctl.getShapes():
            pm.connectAttr(self.blend_att, shp.attr("visibility"))

        pm.connectAttr(self.upvAimVis_att, self.upv_cns.visibility)
        pm.connectAttr(self.upvCtlVis_att, self.roll_ctl_npo.visibility)
        for shp in self.mid_ctl.getShapes():
            pm.connectAttr(self.midCtl_att, shp.attr("visibility"))

        for tweak_ctl in self.tweak_ctl:
            for shp in tweak_ctl.getShapes():
                pm.connectAttr(self.tweakVis_att, shp.attr("visibility"))

        for shp in self.root_ctl.getShapes():
            pm.connectAttr(self.rootVis_att, shp.attr("visibility"))

        # Bendy controls vis
        for shp in self.uplegBendyA_ctl.getShapes():
            pm.connectAttr(self.bendyVis_att, shp.attr("visibility"))
        for shp in self.uplegBendyB_ctl.getShapes():
            pm.connectAttr(self.kneeBendyVis_att, shp.attr("visibility"))
        for shp in self.lowlegBendyA_ctl.getShapes():
            pm.connectAttr(self.kneeBendyVis_att, shp.attr("visibility"))
        for shp in self.lowlegBendyB_ctl.getShapes():
            pm.connectAttr(self.bendyVis_att, shp.attr("visibility"))
        for shp in self.kneeBendy_ctl.getShapes():
            pm.connectAttr(self.kneeBendyVis_att, shp.attr("visibility"))

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

        # NOTE: Ideally we should not change hierarchy or move object after
        # object generation method. But is much easier this way since every
        # part is in the final and correct position
        # after the  ctrn_loc is in the correct position with the ikfk2bone op

        # point constrain tip reference
        pm.pointConstraint(self.ik_ctl, self.tip_ref, mo=False)

        # interpolate transform  mid point locator
        int_matrix = applyop.gear_intmatrix_op(
            self.legChainUpvRef[0].attr("worldMatrix"),
            self.tip_ref.attr("worldMatrix"),
            0.5,
        )
        applyop.gear_mulmatrix_op(
            int_matrix.attr("output"),
            self.interpolate_lvl.attr("parentInverseMatrix[0]"),
            self.interpolate_lvl,
        )

        # match roll ctl npo to ctrn_loc current transform (so correct orient)
        transform.matchWorldTransform(self.ctrn_loc, self.roll_ctl_npo)

        # match roll ctl npo to interpolate transform current position
        pos = self.interpolate_lvl.getTranslation(space="world")
        self.roll_ctl_npo.setTranslation(pos, space="world")

        # parent constraint roll control npo to interpolate trans
        pm.parentConstraint(self.interpolate_lvl, self.roll_ctl_npo, mo=True)

        # scale: this fix the scalin popping issue
        intM_node = applyop.gear_intmatrix_op(
            self.fk_ref.attr("worldMatrix"),
            self.ik_ref.attr("worldMatrix"),
            o_node.attr("blend"),
        )
        mulM_node = applyop.gear_mulmatrix_op(
            intM_node.attr("output"), self.eff_loc.attr("parentInverseMatrix")
        )
        dm_node = node.createDecomposeMatrixNode(mulM_node.attr("output"))
        dm_node.attr("outputScale") >> self.eff_loc.attr("scale")

        pm.connectAttr(self.blend_att, o_node + ".blend")
        if self.negate:
            mulVal = -1
            rollMulVal = 1
        else:
            mulVal = 1
            rollMulVal = -1
        roll_m_node = node.createMulNode(self.roll_att, mulVal)
        roll_m_node2 = node.createMulNode(self.roll_ctl.attr("rx"), rollMulVal)
        node.createPlusMinusAverage1D(
            [roll_m_node.outputX, roll_m_node2.outputX],
            operation=1,
            output=o_node + ".roll",
        )

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

        if self.negate:
            self.ikhUpLegTwist.attr("dForwardAxis").set(1)

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

        # bendy controls
        muldiv_node = pm.createNode("multiplyDivide")
        muldiv_node.attr("input2X").set(-1)
        pm.connectAttr(self.tws1A_npo.attr("rz"), muldiv_node.attr("input1X"))
        muldiv_nodeBias = pm.createNode("multiplyDivide")
        if self.negate:
            sum_node = node.createPlusMinusAverage1D(
                [muldiv_node.attr("outputX"), 180], operation=2
            )
            pm.connectAttr(sum_node.output1D, muldiv_nodeBias.attr("input1X"))
        else:
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
            self.lowlegBendyB_loc,
            self.lowlegBendyA_npo,
            axis=axis,
            wupType=2,
            wupVector=[0, 0, 1],
            wupObject=self.mid_ctl,
            maintainOffset=False,
        )

        pm.pointConstraint(self.eff_loc, self.lowlegBendyB_loc)

        muldiv_node = pm.createNode("multiplyDivide")
        muldiv_node.attr("input2X").set(-1)
        pm.connectAttr(self.tws1B_npo.attr("rz"), muldiv_node.attr("input1X"))
        muldiv_nodeBias = pm.createNode("multiplyDivide")
        if self.negate:
            sum_node = node.createPlusMinusAverage1D(
                [muldiv_node.attr("outputX"), 180], operation=1
            )
            pm.connectAttr(sum_node.output1D, muldiv_nodeBias.attr("input1X"))
        else:
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
            self.uplegBendyA_loc,
            self.uplegBendyB_npo,
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

        self.volDriver_att = div_node2.outputX

        # connecting bendy scaele compensation after volume to
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
            div_node2.attr("outputX"), self.uplegBendyA_loc.attr("sx")
        )

        div_nodeLowLeg = node.createDivNode(
            distB_node + ".distance", dm_node.attr("outputScaleX")
        )
        div_node2 = node.createDivNode(
            div_nodeLowLeg + ".outputX", distB_node.attr("distance").get()
        )

        pm.connectAttr(div_node2.attr("outputX"), self.tws1B_loc.attr("sx"))
        pm.connectAttr(
            div_node2.attr("outputX"), self.lowlegBendyB_loc.attr("sx")
        )

        # conection curve
        cnts = [
            self.uplegBendyA_loc,
            self.uplegBendyA_ctl,
            self.uplegBendyB_ctl,
            self.kneeBendy_ctl,
        ]
        applyop.gear_curvecns_op(self.uplegTwistCrv, cnts)

        cnts = [
            self.kneeBendy_ctl,
            self.lowlegBendyA_ctl,
            self.lowlegBendyB_ctl,
            self.lowlegBendyB_loc,
        ]
        applyop.gear_curvecns_op(self.lowlegTwistCrv, cnts)

        # connect elbow ref
        cns = pm.parentConstraint(self.bone1, self.knee_ref, mo=False)
        if self.negate and self.settings["div1"]:
            pm.setAttr(cns + ".target[0].targetOffsetRotateZ", 180)

        # Divisions ----------------------------------------
        # at 0 or 1 the division will follow exactly the rotation of the
        # controler.. and we wont have this nice bendy + roll
        div_offset = int(self.extra_div / 2)
        for i, div_cns in enumerate(self.div_cns):
            if i == 0:
                if self.settings["div0"]:
                    mulmat_node = applyop.gear_mulmatrix_op(
                        self.uplegTwistChain[i] + ".worldMatrix",
                        div_cns + ".parentInverseMatrix",
                    )
                    mulmat_node = applyop.gear_mulmatrix_op(
                        self.uplegRollRef[0] + ".worldMatrix",
                        self.leg_root_base + ".parentInverseMatrix",
                    )
                else:
                    mulmat_node = applyop.gear_mulmatrix_op(
                        self.uplegRollRef[0] + ".worldMatrix",
                        div_cns + ".parentInverseMatrix",
                    )
                lastUpLegDiv = div_cns
            elif i < (self.settings["div0"] + div_offset):
                mulmat_node = applyop.gear_mulmatrix_op(
                    self.uplegTwistChain[i] + ".worldMatrix",
                    div_cns + ".parentInverseMatrix",
                )
                lastUpLegDiv = div_cns
            elif (
                i == (self.settings["div0"] + div_offset)
                and self.settings["div0"] == 0
            ):
                mulmat_node = applyop.gear_mulmatrix_op(
                    self.knee_ref + ".worldMatrix",
                    div_cns + ".parentInverseMatrix",
                )
                lastUpLegDiv = div_cns
            else:
                o_node = self.lowlegTwistChain[
                    i - (self.settings["div0"] + div_offset)
                ]
                mulmat_node = applyop.gear_mulmatrix_op(
                    o_node + ".worldMatrix", div_cns + ".parentInverseMatrix"
                )
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

        # TODO: check for a more clean and elegant solution instead of
        # re-match the world matrix again
        transform.matchWorldTransform(self.fk_ctl[0], self.match_fk0_off)
        transform.matchWorldTransform(self.fk_ctl[1], self.match_fk1_off)
        transform.matchWorldTransform(self.fk_ctl[0], self.match_fk0)
        transform.matchWorldTransform(self.fk_ctl[1], self.match_fk1)

        # match IK/FK ref
        pm.parentConstraint(self.bone0, self.match_fk0_off, mo=True)
        pm.parentConstraint(self.bone1, self.match_fk1_off, mo=True)

        # base leg joint final connection.
        # we doing it at the end to ensure the div_cns is in the final position
        transform.matchWorldTransform(self.div_cns[0], self.leg_root_base)
        if self.settings["div0"]:
            applyop.oriCns(self.bone0, self.leg_root_base, maintainOffset=True)
        else:
            applyop.oriCns(self.bone0, self.tweak_npo[0], maintainOffset=True)

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        offset = int(self.extra_div / 2)
        self.relatives["root"] = self.div_cns[0]
        self.relatives["knee"] = self.div_cns[self.settings["div0"] + offset]
        self.relatives["ankle"] = self.div_cns[-1]
        self.relatives["eff"] = self.end_ref

        self.controlRelatives["root"] = self.fk0_ctl
        self.controlRelatives["knee"] = self.fk1_ctl
        self.controlRelatives["ankle"] = self.ik_ctl
        self.controlRelatives["eff"] = self.fk2_ctl

        # we need to account with the extra joint for swing
        if self.settings["div0"]:
            offset = offset + 1

        self.jointRelatives["root"] = 0
        self.jointRelatives["knee"] = self.settings["div0"] + offset
        self.jointRelatives["ankle"] = -1
        self.jointRelatives["eff"] = -1

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
