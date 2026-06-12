import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import transform, primitive, curve, applyop
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

        if self.settings["overrideNegate"]:
            self.mirror_conf = [0, 0, 1,
                                1, 1, 0,
                                0, 0, 0]
        else:
            self.mirror_conf = [0, 0, 0,
                                0, 0, 0,
                                0, 0, 0]

        # IK controls ---------------------------------------------
        self.ik_ctl = []
        self.ik_global_in = []
        self.ik_local_in = []
        self.ik_global_out = []
        self.ik_global_ref = []
        self.previusTag = self.parentCtlTag
        for i, t in enumerate(transform.getChainTransform2(self.guide.apos,
                                                           self.normal,
                                                           self.negate)):

            # global input
            global_t = transform.setMatrixPosition(
                datatypes.Matrix(),
                transform.getPositionFromMatrix(t))
            ik_global_npo = primitive.addTransform(
                self.root, self.getName("ik%s_global_npo" % i), global_t)
            ik_global_in = primitive.addTransform(
                ik_global_npo, self.getName("ik%s_global_in" % i), global_t)
            self.ik_global_in.append(ik_global_in)

            # local input
            ik_local_npo = primitive.addTransform(
                ik_global_in, self.getName("ik%s_local_npo" % i), t)
            ik_local_in = primitive.addTransform(
                ik_local_npo, self.getName("ik%s_local_in" % i), t)
            self.ik_local_in.append(ik_local_in)

            ik_npo = primitive.addTransform(ik_local_in,
                                            self.getName("ik%s_npo" % i),
                                            t)

            # output
            ik_global_out_npo = primitive.addTransform(
                self.root, self.getName("ik%s_global_out_npo" % i), global_t)
            ik_global_out = primitive.addTransform(
                ik_global_out_npo,
                self.getName("ik%s_global_out" % i),
                global_t)
            self.ik_global_out.append(ik_global_out)

            ik_ctl = self.addCtl(
                ik_npo,
                "ik%s_ctl" % i,
                t,
                self.color_ik,
                "square",
                w=self.size * .15,
                h=self.size * .15,
                d=self.size * .15,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=self.previusTag,
                mirrorConf=self.mirror_conf)

            attribute.setKeyableAttributes(ik_ctl, self.tr_params)
            self.ik_ctl.append(ik_ctl)

            # ik global ref
            ik_global_ref = primitive.addTransform(
                ik_ctl,
                self.getName("ik%s_global_ref" % i),
                global_t)
            self.ik_global_ref.append(ik_global_ref)
            attribute.setKeyableAttributes(ik_global_ref, [])

        # Curves -------------------------------------------
        self.mst_crv = curve.addCnsCurve(
            self.root,
            self.getName("mst_crv"),
            self.ik_ctl,
            3)
        self.slv_crv = curve.addCurve(
            self.root, self.getName("slv_crv"),
            [datatypes.Vector()] * 10,
            False,
            3
        )
        self.mst_crv.setAttr("visibility", False)
        self.slv_crv.setAttr("visibility", False)

        # add visual reference
        icon.connection_display_curve(
            self.getName("visualIKRef"),
            self.ik_ctl)

        if not self.settings["isGlobalMaster"]:
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
            self.fk_global_in = []
            self.fk_local_in = []
            self.fk_global_out = []
            self.fk_global_ref = []

            parent_twistRef = primitive.addTransform(
                self.root,
                self.getName("reference"),
                transform.getTransform(self.root))

            self.jointList = []
            self.preiviousCtlTag = self.parentCtlTag
            for i in range(self.settings["fkNb"]):
                # References
                div_cns = primitive.addTransform(parentdiv,
                                                 self.getName("%s_cns" % i))
                pm.setAttr(div_cns + ".inheritsTransform", False)
                self.div_cns.append(div_cns)
                parentdiv = div_cns

                if i in [0, self.settings["fkNb"] - 1] and False:
                    fk_ctl = primitive.addTransform(
                        parentctl,
                        self.getName("%s_loc" % i),
                        transform.getTransform(parentctl))

                    fk_npo = fk_ctl
                    if i in [self.settings["fkNb"] - 1]:
                        self.fk_ctl.append(fk_ctl)
                else:
                    m = transform.getTransform(self.root)
                    m.inverse()
                    t = transform.getTransform(parentctl)

                    fk_npo = primitive.addTransform(
                        parentctl,
                        self.getName("fk%s_npo" % (i)),
                        t)

                    # local input
                    fk_local_npo = primitive.addTransform(
                        fk_npo, self.getName("fk%s_local_npo" % i), t)
                    fk_local_in = primitive.addTransform(
                        fk_local_npo, self.getName("fk%s_local_in" % i), t)
                    self.fk_local_in.append(fk_local_in)

                    fk_ctl = self.addCtl(
                        fk_local_in,
                        "fk%s_ctl" % (i),
                        transform.getTransform(parentctl),
                        self.color_fk,
                        "cube",
                        w=self.size * .1,
                        h=self.size * .1,
                        d=self.size * .1,
                        tp=self.preiviousCtlTag,
                        mirrorConf=self.mirror_conf)

                    attribute.setKeyableAttributes(self.fk_ctl)
                    attribute.setRotOrder(fk_ctl, "ZXY")
                    self.fk_ctl.append(fk_ctl)
                    self.preiviousCtlTag = fk_ctl

                self.fk_npo.append(fk_npo)
                parentctl = fk_ctl
                scl_ref = primitive.addTransform(
                    parentctl,
                    self.getName("%s_scl_ref" % i),
                    transform.getTransform(parentctl))

                self.scl_transforms.append(scl_ref)

                # Deformers (Shadow)
                if self.settings["addJoints"]:
                    self.jnt_pos.append([scl_ref, i])

                # Twist references (This objects will replace the spinlookup
                # slerp solver behavior)
                t = transform.getTransformLookingAt(
                    self.guide.apos[0],
                    self.guide.apos[-1],
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

                for x in self.fk_ctl[:-1]:
                    attribute.setInvertMirror(x, ["tx", "rz", "ry"])
            # add visual reference
            icon.connection_display_curve(
                self.getName("visualFKRef"),
                self.fk_ctl)

    # =====================================================
    # ATTRIBUTES
    # =====================================================

    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""
        if not self.settings["isGlobalMaster"]:
            # Anim -------------------------------------------
            self.position_att = self.addAnimParam(
                "position",
                "Position",
                "double",
                self.settings["position"], 0, 1)

            self.maxstretch_att = self.addAnimParam(
                "maxstretch",
                "Max Stretch",
                "double",
                self.settings["maxstretch"],
                1)

            self.maxsquash_att = self.addAnimParam(
                "maxsquash",
                "Max Squash",
                "double",
                self.settings["maxsquash"],
                0,
                1)

            self.softness_att = self.addAnimParam(
                "softness",
                "Softness",
                "double",
                self.settings["softness"],
                0,
                1)

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        for e, ctl in enumerate(self.ik_ctl):
            out_glob = self.ik_global_out[e]
            out_ref = self.ik_global_ref[e]
            applyop.gear_mulmatrix_op(
                out_ref.attr("worldMatrix"),
                out_glob.attr("parentInverseMatrix[0]"),
                out_glob)

        if not self.settings["isGlobalMaster"]:
            # Curves -------------------------------------------
            op = applyop.gear_curveslide2_op(
                self.slv_crv, self.mst_crv, 0, 1.5, .5, .5)

            pm.connectAttr(self.position_att, op + ".position")
            pm.connectAttr(self.maxstretch_att, op + ".maxstretch")
            pm.connectAttr(self.maxsquash_att, op + ".maxsquash")
            pm.connectAttr(self.softness_att, op + ".softness")

            # Division -----------------------------------------
            rootWorld_node = node.createDecomposeMatrixNode(
                self.root.attr("worldMatrix"))
            for i in range(self.settings["fkNb"]):

                # References
                u = i / (self.settings["fkNb"] - 1.0)
                if i == 0:  # we add extra 10% to the first position
                    u = (1.0 / (self.settings["fkNb"] - 1.0)) / 10

                cns = applyop.pathCns(
                    self.div_cns[i], self.slv_crv, False, u, True)

                cns.setAttr("frontAxis", 0)  # front axis is 'X'
                cns.setAttr("upAxis", 2)  # front axis is 'Z'

                # Roll
                intMatrix = applyop.gear_intmatrix_op(
                    self.ik_ctl[0] + ".worldMatrix",
                    self.ik_ctl[-1] + ".worldMatrix",
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
                div_node = node.createDivNode(
                    [1, 1, 1],
                    [rootWorld_node + ".outputScaleX",
                     rootWorld_node + ".outputScaleY",
                     rootWorld_node + ".outputScaleZ"])

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

                    pm.connectAttr(mul_node + ".output",
                                   self.fk_npo[i].attr("t"))

                pm.connectAttr(dm_node + ".outputRotate",
                               self.fk_npo[i].attr("r"))

                # Orientation Lock
                if i == 0:
                    dm_node = node.createDecomposeMatrixNode(
                        self.ik_ctl[0] + ".worldMatrix")

                    blend_node = node.createBlendNode(
                        [dm_node + ".outputRotate%s" % s for s in "XYZ"],
                        [cns + ".rotate%s" % s for s in "XYZ"],
                        0)

                    self.div_cns[i].attr("rotate").disconnect()

                    pm.connectAttr(blend_node + ".output",
                                   self.div_cns[i] + ".rotate")

                elif i == self.settings["fkNb"] - 1:
                    dm_node = node.createDecomposeMatrixNode(
                        self.ik_ctl[-1] + ".worldMatrix")

                    blend_node = node.createBlendNode(
                        [dm_node + ".outputRotate%s" % s for s in "XYZ"],
                        [cns + ".rotate%s" % s for s in "XYZ"],
                        0)

                    self.div_cns[i].attr("rotate").disconnect()
                    pm.connectAttr(blend_node + ".output",
                                   self.div_cns[i] + ".rotate")

            # CONNECT STACK
            # master components
            mstr_global = self.settings["masterChainGlobal"]
            mstr_local = self.settings["masterChainLocal"]
            if mstr_global:
                mstr_global = self.rig.components[mstr_global]
            if mstr_local:
                mstr_local = self.rig.components[mstr_local]

            # connect  global IK
            if mstr_global:
                for e, ctl in enumerate(self.ik_ctl):
                    # connect in global
                    self.connect_master(mstr_global.ik_global_out,
                                        self.ik_global_in,
                                        e,
                                        self.settings["cnxOffset"])

            # connect in local
            if mstr_local:
                for e, ctl in enumerate(self.ik_ctl):
                    self.connect_master(mstr_local.ik_ctl,
                                        self.ik_local_in,
                                        e,
                                        self.settings["cnxOffset"])

                for e, ctl in enumerate(self.fk_ctl):
                    self.connect_master(mstr_local.fk_ctl,
                                        self.fk_local_in,
                                        e,
                                        self.settings["cnxOffset"])

    def connect_master(self, mstr_out, slave_in, idx, offset):
        """Connect master and slave chain

        Args:
            mstr_out (list): List of master outputs
            slave_in (list): List of slave inputs
            idx (int): Input index
            offset (int): Offset for the mastr ouput index
        """
        # we need to check if  master have enought sections
        # if  connection is out of index, will fallback to the latest
        # section in the master
        if (idx + offset) > len(mstr_out) - 1:
            mstr_e = len(mstr_out) - 1
        else:
            mstr_e = idx + offset
        m_out = mstr_out[mstr_e]
        s_in = slave_in[idx]
        for srt in ["scale", "rotate", "translate"]:
            pm.connectAttr(m_out.attr(srt), s_in.attr(srt))

    # =====================================================
    # CONNECTOR
    # =====================================================

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        if not self.settings["isGlobalMaster"]:
            num_ik_ctl = len(self.ik_ctl)
            num_fk_ctl = len(self.fk_ctl)
            every_each = num_fk_ctl // (num_ik_ctl - 1)

            self.relatives["root"] = self.fk_ctl[0]
            self.controlRelatives["root"] = self.fk_ctl[0]
            self.jointRelatives["root"] = 0

            for i in range(num_ik_ctl - 2):
                fk_index = (i + 1) * every_each
                loc_key = "%s_loc" % i
                self.relatives[loc_key] = self.fk_ctl[fk_index]
                self.controlRelatives[loc_key] = self.fk_ctl[fk_index]
                self.jointRelatives[loc_key] = fk_index
                self.aliasRelatives[loc_key] = fk_index

            last_loc_key = "%s_loc" % (num_ik_ctl - 2)
            self.relatives[last_loc_key] = self.fk_ctl[-1]
            self.controlRelatives[last_loc_key] = self.fk_ctl[-1]
            self.jointRelatives[last_loc_key] = num_fk_ctl - 1
            self.aliasRelatives[last_loc_key] = num_fk_ctl - 1
