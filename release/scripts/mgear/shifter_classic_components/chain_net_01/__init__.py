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

        if self.settings["overrideNegate"]:
            self.mirror_conf = [0, 0, 1,
                                1, 1, 0,
                                0, 0, 0]
        else:
            self.mirror_conf = [0, 0, 0,
                                0, 0, 0,
                                0, 0, 0]

        # FK controllers ------------------------------------
        self.fk_npo = []
        self.fk_a_in = []
        self.fk_b_in = []
        self.fk_ctl = []
        self.ik_a_in = []
        self.ik_b_in = []
        self.ik_ctl = []
        self.upv_curv_lvl = []
        t = self.guide.tra["root"]

        parent = self.root
        tOld = False
        fk_ctl = None
        self.previusTag = self.parentCtlTag
        self.previusTagIk = self.parentCtlTag
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

            # fk npo
            fk_npo = primitive.addTransform(
                parent, self.getName("fk%s_npo" % i), tnpo)
            self.fk_npo.append(fk_npo)
            fk_a_in = primitive.addTransform(
                fk_npo, self.getName("fk%s_a_in" % i), tnpo)
            self.fk_a_in.append(fk_a_in)
            fk_b_in = primitive.addTransform(
                fk_a_in, self.getName("fk%s_b_in" % i), tnpo)
            self.fk_b_in.append(fk_b_in)

            # ctl
            fk_ctl = self.addCtl(
                fk_b_in,
                "fk%s_ctl" % i,
                t,
                self.color_fk,
                "cube",
                w=self.dist,
                h=self.size * .1,
                d=self.size * .1,
                po=datatypes.Vector(self.dist * .5 * self.n_factor, 0, 0),
                tp=self.previusTag,
                mirrorConf=self.mirror_conf)

            self.fk_ctl.append(fk_ctl)
            self.previusTag = fk_ctl

            parent = fk_ctl

            ik_a_in = primitive.addTransform(
                fk_ctl, self.getName("ik%s_a_in" % i), tnpo)
            self.ik_a_in.append(ik_a_in)
            ik_b_in = primitive.addTransform(
                ik_a_in, self.getName("ik%s_b_in" % i), tnpo)
            self.ik_b_in.append(ik_b_in)

            ik_ctl = self.addCtl(
                ik_b_in,
                "ik%s_ctl" % i,
                t,
                self.color_ik,
                "square",
                w=self.size * .15,
                h=self.size * .15,
                d=self.size * .15,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=self.previusTagIk,
                mirrorConf=self.mirror_conf)

            self.ik_ctl.append(ik_ctl)

            self.previusTagIk = ik_ctl

            if not self.settings["onlyMaster"]:

                upv_curv_lvl = primitive.addTransform(
                    ik_ctl, self.getName("upv%s_lvl" % i), t)
                upv_curv_lvl.attr("tz").set(.01)

                self.upv_curv_lvl.append(upv_curv_lvl)
                tOld = t

        # add end control
        ik_npo = primitive.addTransform(
            fk_ctl, self.getName("ikEnd_npo"), t)
        ik_a_in = primitive.addTransform(
            ik_npo, self.getName("ikEnd_a_in"), t)
        self.ik_a_in.append(ik_a_in)
        ik_b_in = primitive.addTransform(
            ik_a_in, self.getName("ikEnd_b_in"), t)
        self.ik_b_in.append(ik_b_in)
        ik_ctl = self.addCtl(
            ik_b_in,
            "ikEnd_ctl",
            t,
            self.color_ik,
            "square",
            w=self.size * .15,
            h=self.size * .15,
            d=self.size * .15,
            ro=datatypes.Vector([0, 0, 1.5708]),
            tp=self.previusTagIk,
            mirrorConf=self.mirror_conf)

        self.previusTagIk = ik_ctl

        if not self.settings["onlyMaster"]:
            upv_curv_lvl = primitive.addTransform(
                ik_ctl, self.getName("upvEnd_lvl"), t)
            upv_curv_lvl.attr("tz").set(.01)
            self.upv_curv_lvl.append(upv_curv_lvl)

        if self.negate:
            self.off_dist = self.dist * -1
        else:
            self.off_dist = self.dist
        ik_npo.attr("tx").set(self.off_dist)

        self.ik_ctl.append(ik_ctl)

        # add length offset control if keep length
        # This option will be added only if keep length is active
        if self.settings["keepLength"]:
            self.ikTip_npo = primitive.addTransform(
                ik_ctl, self.getName("ikTip_npo"), t)
            ik_a_in = primitive.addTransform(
                self.ikTip_npo, self.getName("ikTip_a_in"), t)
            self.ik_a_in.append(ik_a_in)
            ik_b_in = primitive.addTransform(
                ik_a_in, self.getName("ikTip_b_in"), t)
            self.ik_b_in.append(ik_b_in)
            ik_ctl = self.addCtl(
                ik_b_in,
                "ikTip_ctl",
                t,
                self.color_fk,
                "square",
                w=self.size * .1,
                h=self.size * .1,
                d=self.size * .1,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=self.previusTagIk,
                mirrorConf=self.mirror_conf)
            if not self.settings["onlyMaster"]:
                upv_curv_lvl = primitive.addTransform(
                    ik_ctl, self.getName("upvTip_lvl"), t)
                upv_curv_lvl.attr("tz").set(.01)
                self.upv_curv_lvl.append(upv_curv_lvl)

            # move to align with the parent
            self.ikTip_npo.attr("tx").set(0)

            self.ik_ctl.append(ik_ctl)

            # add visual reference
            self.line_ref = icon.connection_display_curve(
                self.getName("visualRef"),
                [self.ikTip_npo.getParent(), ik_ctl])

        # set keyable attr for controls
        [attribute.setKeyableAttributes(t_ctl,
                                        ["tx", "ty", "tz", "rx", "ry", "rz"])
            for t_ctl in self.ik_ctl + self.fk_ctl]

        # Curves -------------------------------------------
        if not self.settings["onlyMaster"]:
            self.mst_crv = curve.addCnsCurve(self.root,
                                             self.getName("mst_crv"),
                                             self.ik_ctl[:],
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

            if self.settings["overrideJntNb"]:
                self.def_number = self.settings["jntNb"]
            else:
                self.def_number = len(self.guide.apos)

            if self.settings["extraTweak"]:
                tagP = self.parentCtlTag
                self.extraik_ctl = []

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

                # self.jnt_pos.append([div_cns, i])
                if self.settings["extraTweak"]:
                    t = transform.getTransform(div_cns)
                    ro_vector = datatypes.Vector([0, 0, 1.5708])
                    ik_ctl = self.addCtl(div_cns,
                                         "extraTweak%s_ctl" % i,
                                         t,
                                         self.color_fk,
                                         "square",
                                         w=self.size * .08,
                                         d=self.size * .08,
                                         ro=ro_vector,
                                         tp=tagP)
                    attribute.setKeyableAttributes(ik_ctl)

                    tagP = ik_ctl
                    self.extraik_ctl.append(ik_ctl)
                    self.jnt_pos.append([ik_ctl, i, None, False])
                else:
                    self.jnt_pos.append([div_cns, i])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        # set the optionl host for visibility controls
        if self.settings["visHost"]:
            vis_host = self.rig.findRelative(self.settings["visHost"])
        else:
            vis_host = None

        self.fkVis_att = self.addAnimParam("FK_vis",
                                           "FK vis",
                                           "bool",
                                           True,
                                           uihost=vis_host)
        self.ikVis_att = self.addAnimParam("IK_vis",
                                           "IK vis",
                                           "bool",
                                           True,
                                           uihost=vis_host)

        if not self.settings["onlyMaster"]:
            self.bias_att = self.addAnimParam("bias",
                                              "masterBias",
                                              "float",
                                              self.settings["bias"],
                                              0,
                                              1,
                                              uihost=self.fk_ctl[0])
            if self.settings["keepLength"]:
                self.length_ratio_att = self.addAnimParam("length_ratio",
                                                          "Length Ratio",
                                                          "float",
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

        if not self.settings["onlyMaster"]:
            dm_node_scl = node.createDecomposeMatrixNode(self.root.worldMatrix)
            if self.settings["keepLength"]:
                arclen_node = pm.arclen(self.mst_crv, ch=True)
                alAttr = pm.getAttr(arclen_node + ".arcLength")
                ration_node = node.createMulNode(self.length_ratio_att,
                                                 alAttr)

                pm.addAttr(self.mst_crv, ln="length_ratio", k=True, w=True)
                node.createDivNode(arclen_node.arcLength,
                                   ration_node.outputX,
                                   self.mst_crv.length_ratio)

                div_node_scl = node.createDivNode(self.mst_crv.length_ratio,
                                                  dm_node_scl.outputScaleX)

            u = 0.000
            step = 1.000 / (self.def_number - 1)

            for i in range(self.def_number):
                cnsUpv = applyop.pathCns(self.upv_cns[i],
                                         self.upv_crv,
                                         cnsType=False,
                                         u=u,
                                         tangent=False)

                cns = applyop.pathCns(
                    self.div_cns[i], self.mst_crv, False, u, True)

                # Connecting the scale for scaling compensation
                # for axis, AX in zip("xyz", "XYZ"):
                for axis, AX in zip("x", "X"):
                    pm.connectAttr(
                        dm_node_scl.attr("outputScale{}".format(AX)),
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

        # CONNECT STACK
        # master components
        mstr_a = self.settings["masterChainA"]
        mstr_b = self.settings["masterChainB"]
        if mstr_b:
            mstr_b = self.rig.components[mstr_b]
        if mstr_a:
            mstr_a = self.rig.components[mstr_a]

        # connect the  chain ctls
        for e, ctl in enumerate(self.fk_ctl):

            # connect in B
            if mstr_b:
                self.connect_master(mstr_b.fk_ctl,
                                    self.fk_b_in,
                                    e,
                                    self.settings["cnxOffset"])

            # connect in A
            if mstr_a:
                self.connect_master(mstr_a.fk_ctl,
                                    self.fk_a_in,
                                    e,
                                    self.settings["cnxOffset"],
                                    True)

            for shp in ctl.getShapes():
                pm.connectAttr(self.fkVis_att, shp.attr("visibility"))

        for e, ctl in enumerate(self.ik_ctl):
            if mstr_b:
                self.connect_master(mstr_b.ik_ctl,
                                    self.ik_b_in,
                                    e,
                                    self.settings["cnxOffset"])
            if mstr_a:
                self.connect_master(mstr_a.ik_ctl,
                                    self.ik_a_in,
                                    e,
                                    self.settings["cnxOffset"],
                                    True)
            for shp in ctl.getShapes():
                pm.connectAttr(self.ikVis_att, shp.attr("visibility"))

        if self.settings["extraTweak"] and not self.settings["onlyMaster"]:
            for ik_ctl in self.extraik_ctl:
                for shp in ik_ctl.getShapes():
                    pm.connectAttr(self.tweakVis_att, shp.attr("visibility"))

    def connect_master(self, mstr_out, slave_in, idx, offset, rev_bias=False):
        """Connect master and slave chain

        Args:
            mstr_out (list): List of master outputs
            slave_in (list): List of slave inputs
            idx (int): Input index
            offset (int): Offset for the mastr ouput index
            rev_bias (bool): reverse bias value from 0 to 1
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
        if rev_bias:
            bias = node.createReverseNode(self.bias_att).outputX
        else:
            bias = self.bias_att
        for srt in ["rotate", "translate"]:
            m_node = node.createMulNode([m_out.attr(srt + "X"),
                                         m_out.attr(srt + "Y"),
                                         m_out.attr(srt + "Z")],
                                        [bias, bias, bias],
                                        [s_in.attr(srt + "X"),
                                         s_in.attr(srt + "Y"),
                                         s_in.attr(srt + "Z")])
            # pm.connectAttr(m_out.attr(srt), s_in.attr(srt))

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
        self.relatives["%s_loc" % (len(self.fk_ctl) - 1)] = self.fk_ctl[-1]
        self.controlRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = self.fk_ctl[-1]
        self.jointRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = len(self.fk_ctl) - 1
        self.aliasRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = len(self.fk_ctl) - 1
