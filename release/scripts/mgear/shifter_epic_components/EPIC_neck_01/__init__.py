import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component
import ast

from mgear.core import node, fcurve, applyop, vector, curve
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

        # joint Description Names
        jd_names = ast.literal_eval(
            self.settings["jointNamesDescription_custom"]
        )
        jdn_neck = jd_names[0]
        jdn_head = jd_names[1]

        self.normal = self.guide.blades["blade"].z * -1
        self.up_axis = pm.upAxis(q=True, axis=True)

        # Ik Controlers ------------------------------------
        if self.settings["IKWorldOri"]:
            t = datatypes.TransformationMatrix()
        else:
            t = transform.getTransformLookingAt(
                self.guide.pos["tan1"],
                self.guide.pos["neck"],
                self.normal,
                "yx",
                self.negate,
            )

        t = transform.setMatrixPosition(t, self.guide.pos["neck"])

        self.ik_off = primitive.addTransform(
            self.root, self.getName("ik_off"), t
        )
        # handle Z up orientation offset
        if self.up_axis == "z" and self.settings["IKWorldOri"]:
            self.ik_off.rx.set(90)
            t = transform.getTransform(self.ik_off)

        self.ik_cns = primitive.addTransform(
            self.ik_off, self.getName("ik_cns"), t
        )

        self.ik_ctl = self.addCtl(
            self.ik_cns,
            "ik_ctl",
            t,
            self.color_ik,
            "compas",
            w=self.size * 0.5,
            tp=self.parentCtlTag,
        )

        attribute.setKeyableAttributes(self.ik_ctl, self.tr_params)
        attribute.setRotOrder(self.ik_ctl, "ZXY")
        attribute.setInvertMirror(self.ik_ctl, ["tx", "ry", "rz"])

        # Tangents -----------------------------------------
        if self.settings["tangentControls"]:
            t = transform.setMatrixPosition(t, self.guide.pos["tan1"])

            self.tan1_loc = primitive.addTransform(
                self.ik_ctl, self.getName("tan1_loc"), t
            )

            self.tan1_ctl = self.addCtl(
                self.tan1_loc,
                "tan1_ctl",
                t,
                self.color_ik,
                "sphere",
                w=self.size * 0.2,
                tp=self.ik_ctl,
            )

            attribute.setKeyableAttributes(self.tan1_ctl, self.t_params)
            attribute.setInvertMirror(self.tan1_ctl, ["tx"])

            t = transform.getTransformLookingAt(
                self.guide.pos["root"],
                self.guide.pos["tan0"],
                self.normal,
                "yx",
                self.negate,
            )

            t = transform.setMatrixPosition(t, self.guide.pos["tan0"])

            self.tan0_loc = primitive.addTransform(
                self.root, self.getName("tan0_loc"), t
            )

            self.tan0_ctl = self.addCtl(
                self.tan0_loc,
                "tan0_ctl",
                t,
                self.color_ik,
                "sphere",
                w=self.size * 0.2,
                tp=self.ik_ctl,
            )

            attribute.setKeyableAttributes(self.tan0_ctl, self.t_params)
            attribute.setInvertMirror(self.tan0_ctl, ["tx"])

            # Curves -------------------------------------------
            self.mst_crv = curve.addCnsCurve(
                self.root,
                self.getName("mst_crv"),
                [self.root, self.tan0_ctl, self.tan1_ctl, self.ik_ctl],
                3,
            )

            self.slv_crv = curve.addCurve(
                self.root,
                self.getName("slv_crv"),
                [datatypes.Vector()] * 10,
                False,
                3,
            )

            self.mst_crv.setAttr("visibility", False)

        else:
            t = transform.setMatrixPosition(t, self.guide.pos["tan1"])
            self.tan1_loc = primitive.addTransform(
                self.ik_ctl, self.getName("tan1_loc"), t
            )

            t = transform.getTransformLookingAt(
                self.guide.pos["root"],
                self.guide.pos["tan0"],
                self.normal,
                "yx",
                self.negate,
            )

            t = transform.setMatrixPosition(t, self.guide.pos["tan0"])

            self.tan0_loc = primitive.addTransform(
                self.root, self.getName("tan0_loc"), t
            )

            # Curves -------------------------------------------
            self.mst_crv = curve.addCnsCurve(
                self.root,
                self.getName("mst_crv"),
                [self.root, self.tan0_loc, self.tan1_loc, self.ik_ctl],
                3,
            )

            self.slv_crv = curve.addCurve(
                self.root,
                self.getName("slv_crv"),
                [datatypes.Vector()] * 10,
                False,
                3,
            )

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
        self.scl_npo = []

        self.twister = []
        self.ref_twist = []

        # adding 1 for the head
        self.divisions = self.settings["division"] + 1

        parent_twistRef = primitive.addTransform(
            self.root,
            self.getName("reference"),
            transform.getTransform(self.root),
        )

        t = transform.getTransformLookingAt(
            self.guide.pos["root"],
            self.guide.pos["neck"],
            self.normal,
            "yx",
            self.negate,
        )

        self.intMRef = primitive.addTransform(
            self.root, self.getName("intMRef"), t
        )

        self.previousCtlTag = self.parentCtlTag
        for i in range(self.divisions):

            # References
            div_cns = primitive.addTransform(
                parentdiv, self.getName("%s_cns" % i), t
            )

            pm.setAttr(div_cns + ".inheritsTransform", False)
            self.div_cns.append(div_cns)
            parentdiv = div_cns

            scl_npo = primitive.addTransform(
                parentctl,
                self.getName("%s_scl_npo" % i),
                transform.getTransform(parentctl),
            )

            # Controlers (First and last one are fake)

            if i in [self.divisions - 1]:  # 0,
                fk_ctl = primitive.addTransform(
                    scl_npo,
                    self.getName("%s_loc" % i),
                    transform.getTransform(parentctl),
                )

                fk_npo = fk_ctl
            else:
                fk_npo = primitive.addTransform(
                    scl_npo,
                    self.getName("fk%s_npo" % i),
                    transform.getTransform(parentctl),
                )

                fk_ctl = self.addCtl(
                    fk_npo,
                    "fk%s_ctl" % i,
                    transform.getTransform(parentctl),
                    self.color_fk,
                    "cube",
                    w=self.size * 0.2,
                    h=self.size * 0.05,
                    d=self.size * 0.2,
                    tp=self.previousCtlTag,
                )

                attribute.setKeyableAttributes(self.fk_ctl)
                attribute.setRotOrder(fk_ctl, "ZXY")

                self.previousCtlTag = fk_ctl

            self.fk_ctl.append(fk_ctl)

            self.scl_npo.append(scl_npo)
            self.fk_npo.append(fk_npo)
            parentctl = fk_ctl

            if i != self.divisions - 1:
                if i == 0:
                    guide_relative = "root"
                else:
                    guide_relative = None
                self.jnt_pos.append(
                    {
                        "obj": fk_ctl,
                        "name": string.replaceSharpWithPadding(
                            jdn_neck, i + 1
                        ),
                        "guide_relative": guide_relative,
                        "data_contracts": "Twist,Squash",
                        "leaf_joint": self.settings["leafJoints"],
                    }
                )

            t = transform.getTransformLookingAt(
                self.guide.pos["root"],
                self.guide.pos["neck"],
                self.guide.blades["blade"].z * -1,
                "yx",
                self.negate,
            )

            twister = primitive.addTransform(
                parent_twistRef, self.getName("%s_rot_ref" % i), t
            )

            ref_twist = primitive.addTransform(
                parent_twistRef, self.getName("%s_pos_ref" % i), t
            )

            ref_twist.setTranslation(
                datatypes.Vector(0.0, 0, 1.0), space="preTransform"
            )

            self.twister.append(twister)
            self.ref_twist.append(ref_twist)

        for x in self.fk_ctl[:-1]:
            attribute.setInvertMirror(x, ["tx", "rz", "ry"])

        # Head ---------------------------------------------
        t = transform.getTransformLookingAt(
            self.guide.pos["head"],
            self.guide.pos["eff"],
            self.normal,
            "yx",
            self.negate,
        )

        self.head_cns = primitive.addTransform(
            self.root, self.getName("head_cns"), t
        )

        dist = vector.getDistance(
            self.guide.pos["head"], self.guide.pos["eff"]
        )

        self.head_ctl = self.addCtl(
            self.head_cns,
            "head_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.size * 0.5,
            h=dist,
            d=self.size * 0.5,
            po=datatypes.Vector(0, dist * 0.5, 0),
            tp=self.previousCtlTag,
        )

        attribute.setRotOrder(self.head_ctl, "ZXY")
        attribute.setInvertMirror(self.head_ctl, ["tx", "rz", "ry"])

        self.jnt_pos.append(
            {
                "obj": self.head_ctl,
                "name": jdn_head,
                "guide_relative": "neck",
            }
        )

    # =====================================================
    # ATTRIBUTES
    # =====================================================

    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""
        # Anim -------------------------------------------
        self.maxstretch_att = self.addAnimParam(
            "maxstretch",
            "Max Stretch",
            "double",
            self.settings["maxstretch"],
            1,
        )

        self.maxsquash_att = self.addAnimParam(
            "maxsquash",
            "MaxSquash",
            "double",
            self.settings["maxsquash"],
            0,
            1,
        )

        self.softness_att = self.addAnimParam(
            "softness", "Softness", "double", self.settings["softness"], 0, 1
        )

        self.lock_ori_att = self.addAnimParam(
            "lock_ori", "Lock Ori", "double", 1, 0, 1
        )

        self.tan0_att = self.addAnimParam("tan0", "Tangent 0", "double", 1, 0)
        self.tan1_att = self.addAnimParam("tan1", "Tangent 1", "double", 1, 0)

        # Volume
        self.volume_att = self.addAnimParam(
            "volume", "Volume", "double", 1, 0, 1
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

        if self.settings["headrefarray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["headrefarray"].split(",")
            )
            if len(ref_names) > 1:
                ref_names.insert(0, "self")
                self.headref_att = self.addAnimEnumParam(
                    "headref", "Head Ref", 0, ref_names
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

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        # Tangent position ---------------------------------
        # common part
        d = vector.getDistance(self.guide.pos["root"], self.guide.pos["neck"])
        dist_node = node.createDistNode(self.root, self.ik_ctl)
        rootWorld_node = node.createDecomposeMatrixNode(
            self.root.attr("worldMatrix")
        )
        div_node = node.createDivNode(
            dist_node + ".distance", rootWorld_node + ".outputScaleX"
        )
        div_node = node.createDivNode(div_node + ".outputX", d)

        # tan0
        mul_node = node.createMulNode(
            self.tan0_att, self.tan0_loc.getAttr("ty")
        )
        res_node = node.createMulNode(
            mul_node + ".outputX", div_node + ".outputX"
        )
        pm.connectAttr(res_node + ".outputX", self.tan0_loc + ".ty")

        # tan1
        mul_node = node.createMulNode(
            self.tan1_att, self.tan1_loc.getAttr("ty")
        )
        res_node = node.createMulNode(
            mul_node + ".outputX", div_node + ".outputX"
        )
        pm.connectAttr(res_node + ".outputX", self.tan1_loc.attr("ty"))

        # Curves -------------------------------------------
        op = applyop.gear_curveslide2_op(
            self.slv_crv, self.mst_crv, 0, 1.5, 0.5, 0.5
        )
        pm.connectAttr(self.maxstretch_att, op + ".maxstretch")
        pm.connectAttr(self.maxsquash_att, op + ".maxsquash")
        pm.connectAttr(self.softness_att, op + ".softness")

        # Volume driver ------------------------------------
        crv_node = node.createCurveInfoNode(self.slv_crv)

        # Division -----------------------------------------
        for i in range(self.divisions):

            # References
            u = i / (self.divisions - 1.0)

            cns = applyop.pathCns(
                self.div_cns[i], self.slv_crv, False, u, True
            )
            cns.setAttr("frontAxis", 1)  # front axis is 'Y'
            cns.setAttr("upAxis", 2)  # front axis is 'Z'

            # Roll
            intMatrix = applyop.gear_intmatrix_op(
                self.intMRef + ".worldMatrix", self.ik_ctl + ".worldMatrix", u
            )
            dm_node = node.createDecomposeMatrixNode(intMatrix + ".output")
            pm.connectAttr(
                dm_node + ".outputRotate", self.twister[i].attr("rotate")
            )

            pm.parentConstraint(
                self.twister[i], self.ref_twist[i], maintainOffset=True
            )

            pm.connectAttr(
                self.ref_twist[i] + ".translate", cns + ".worldUpVector"
            )

            # Squash n Stretch
            op = applyop.gear_squashstretch2_op(
                self.fk_npo[i], self.root, pm.arclen(self.slv_crv), "y"
            )

            pm.connectAttr(self.volume_att, op + ".blend")
            pm.connectAttr(crv_node + ".arcLength", op + ".driver")
            pm.connectAttr(self.st_att[i], op + ".stretch")
            pm.connectAttr(self.sq_att[i], op + ".squash")
            op.setAttr("driver_min", 0.1)

            # scl compas
            if i != 0:
                div_node = node.createDivNode(
                    [1, 1, 1],
                    [
                        self.fk_npo[i - 1] + ".sx",
                        self.fk_npo[i - 1] + ".sy",
                        self.fk_npo[i - 1] + ".sz",
                    ],
                )

                pm.connectAttr(
                    div_node + ".output", self.scl_npo[i] + ".scale"
                )

            # Controlers
            if i == 0:
                mulmat_node = applyop.gear_mulmatrix_op(
                    self.div_cns[i].attr("worldMatrix"),
                    self.root.attr("worldInverseMatrix"),
                )
            else:
                mulmat_node = applyop.gear_mulmatrix_op(
                    self.div_cns[i].attr("worldMatrix"),
                    self.div_cns[i - 1].attr("worldInverseMatrix"),
                )

            dm_node = node.createDecomposeMatrixNode(mulmat_node + ".output")
            pm.connectAttr(
                dm_node + ".outputTranslate", self.fk_npo[i].attr("t")
            )
            pm.connectAttr(dm_node + ".outputRotate", self.fk_npo[i].attr("r"))

            # Orientation Lock
            if i == self.divisions - 1:
                dm_node = node.createDecomposeMatrixNode(
                    self.ik_ctl + ".worldMatrix"
                )
                blend_node = node.createBlendNode(
                    [dm_node + ".outputRotate%s" % s for s in "XYZ"],
                    [cns + ".rotate%s" % s for s in "XYZ"],
                    self.lock_ori_att,
                )
                self.div_cns[i].attr("rotate").disconnect()

                pm.connectAttr(
                    blend_node + ".output", self.div_cns[i] + ".rotate"
                )

        # Head ---------------------------------------------
        self.fk_ctl[-1].addChild(self.head_cns)

        # scale compensation
        dm_node = node.createDecomposeMatrixNode(
            self.scl_npo[0] + ".parentInverseMatrix"
        )

        pm.connectAttr(dm_node + ".outputScale", self.scl_npo[0] + ".scale")

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.root
        self.relatives["tan1"] = self.root
        self.relatives["tan2"] = self.head_ctl
        self.relatives["neck"] = self.head_ctl
        self.relatives["head"] = self.head_ctl
        self.relatives["eff"] = self.head_ctl

        self.controlRelatives["root"] = self.fk_ctl[0]
        self.controlRelatives["tan1"] = self.head_ctl
        self.controlRelatives["tan2"] = self.head_ctl
        self.controlRelatives["neck"] = self.head_ctl
        self.controlRelatives["head"] = self.head_ctl
        self.controlRelatives["eff"] = self.head_ctl

        self.jointRelatives["root"] = 0
        self.jointRelatives["tan1"] = 0
        self.jointRelatives["tan2"] = len(self.jnt_pos) - 1
        self.jointRelatives["neck"] = len(self.jnt_pos) - 1
        self.jointRelatives["head"] = len(self.jnt_pos) - 1
        self.jointRelatives["eff"] = len(self.jnt_pos) - 1

        self.aliasRelatives["tan1"] = "root"
        self.aliasRelatives["tan2"] = "head"
        self.aliasRelatives["neck"] = "head"
        self.aliasRelatives["eff"] = "head"

    def connect_standard(self):
        self.connect_standardWithIkRef()

    def connect_standardWithIkRef(self):

        self.parent.addChild(self.root)

        if self.settings["chickenStyleIK"]:
            skipTranslate = "none"
        else:
            skipTranslate = ["x", "y", "z"]
        self.connectRef(
            self.settings["ikrefarray"], self.ik_cns, st=skipTranslate
        )

        if self.settings["headrefarray"]:
            ref_names = self.settings["headrefarray"].split(",")

            ref = []
            for ref_name in ref_names:
                ref.append(self.rig.findRelative(ref_name))

            ref.append(self.head_cns)
            cns_node = pm.parentConstraint(
                *ref, skipTranslate="none", maintainOffset=True
            )

            cns_attr_names = pm.parentConstraint(
                cns_node, query=True, weightAliasList=True
            )
            cns_attr = []
            for cname in cns_attr_names:
                cns_attr.append("{}.{}".format(cns_node, cname))
            self.head_cns.attr("tx").disconnect()
            self.head_cns.attr("ty").disconnect()
            self.head_cns.attr("tz").disconnect()

            for i, attr in enumerate(cns_attr):
                node_name = pm.createNode("condition")
                pm.connectAttr(self.headref_att, node_name + ".firstTerm")
                pm.setAttr(node_name + ".secondTerm", i + 1)
                pm.setAttr(node_name + ".operation", 0)
                pm.setAttr(node_name + ".colorIfTrueR", 1)
                pm.setAttr(node_name + ".colorIfFalseR", 0)
                pm.connectAttr(node_name + ".outColorR", attr)
