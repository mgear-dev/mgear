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
        self.fk_global_in = []
        self.fk_local_in = []
        self.fk_local_out = []
        self.fk_global_out = []
        self.fk_global_ref = []
        self.fk_ctl = []
        self.tweak_ctl = []
        self.upv_curv_lvl = []
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

            # global input
            global_t = transform.setMatrixPosition(
                datatypes.Matrix(),
                transform.getPositionFromMatrix(t))
            fk_global_npo = primitive.addTransform(
                parent, self.getName("fk%s_global_npo" % i), global_t)
            fk_global_in = primitive.addTransform(
                fk_global_npo, self.getName("fk%s_global_in" % i), global_t)
            self.fk_global_in.append(fk_global_in)

            # local input
            fk_local_npo = primitive.addTransform(
                fk_global_in, self.getName("fk%s_local_npo" % i), tnpo)
            fk_local_in = primitive.addTransform(
                fk_local_npo, self.getName("fk%s_local_in" % i), tnpo)
            self.fk_local_in.append(fk_local_in)

            # output
            fk_global_out_npo = primitive.addTransform(
                parent, self.getName("fk%s_global_out_npo" % i), global_t)
            fk_global_out = primitive.addTransform(
                fk_global_out_npo,
                self.getName("fk%s_global_out" % i),
                global_t)
            self.fk_global_out.append(fk_global_out)

            fk_local_out_npo = primitive.addTransform(
                parent, self.getName("fk%s_local_out_npo" % i), tnpo)
            fk_local_out = primitive.addTransform(
                fk_local_out_npo, self.getName("fk%s_local_out" % i), tnpo)
            self.fk_local_out.append(fk_local_out)

            # fk npo
            fk_npo = primitive.addTransform(
                fk_local_in, self.getName("fk%s_npo" % i), tnpo)
            self.fk_npo.append(fk_npo)

            # ctl
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
                tp=self.previusTag,
                mirrorConf=self.mirror_conf)

            self.fk_ctl.append(fk_ctl)

            # fk global ref
            fk_global_ref = primitive.addTransform(
                fk_ctl,
                self.getName("fk%s_global_ref" % i),
                global_t)
            self.fk_global_ref.append(fk_global_ref)
            attribute.setKeyableAttributes(fk_global_ref, [])

            parent = fk_ctl

            if not self.settings["simpleFK"]:
                tweak_ctl = self.addCtl(
                    fk_ctl,
                    "tweak%s_ctl" % i,
                    t,
                    self.color_ik,
                    "square",
                    w=self.size * .15,
                    h=self.size * .15,
                    d=self.size * .15,
                    ro=datatypes.Vector([0, 0, 1.5708]),
                    tp=self.previusTag,
                    mirrorConf=self.mirror_conf)

                upv_curv_lvl = primitive.addTransform(
                    tweak_ctl, self.getName("upv%s_lvl" % i), t)
                upv_curv_lvl.attr("tz").set(.01)

                self.tweak_ctl.append(tweak_ctl)
                self.upv_curv_lvl.append(upv_curv_lvl)
                tOld = t

            self.previusTag = fk_ctl

        if not self.settings["simpleFK"]:
            # add end control
            tweak_npo = primitive.addTransform(
                fk_ctl, self.getName("tweakEnd_npo"), t)
            tweak_ctl = self.addCtl(
                tweak_npo,
                "tweakEnd_ctl",
                t,
                self.color_ik,
                "square",
                w=self.size * .15,
                h=self.size * .15,
                d=self.size * .15,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=self.previusTag,
                mirrorConf=self.mirror_conf)

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
                    tp=self.previusTag,
                    mirrorConf=self.mirror_conf)

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

            # set keyable attr for tweak controls
            [attribute.setKeyableAttributes(t_ctl, ["tx", "ty", "tz", "rx"])
                for t_ctl in self.tweak_ctl]

            # Curves -------------------------------------------
            self.mst_crv = curve.addCnsCurve(self.root,
                                             self.getName("mst_crv"),
                                             self.tweak_ctl[:],
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

                # self.jnt_pos.append([div_cns, i])
                if self.settings["extraTweak"]:
                    t = transform.getTransform(div_cns)
                    ro_vector = datatypes.Vector([0, 0, 1.5708])
                    tweak_ctl = self.addCtl(div_cns,
                                            "extraTweak%s_ctl" % i,
                                            t,
                                            self.color_fk,
                                            "square",
                                            w=self.size * .08,
                                            d=self.size * .08,
                                            ro=ro_vector,
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
        if not self.settings["simpleFK"]:
            self.ikVis_att = self.addAnimParam("IK_vis",
                                               "IK vis",
                                               "bool",
                                               True,
                                               uihost=vis_host)

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

        self.mid_twist_att = self.addAnimParam("mid_twist",
                                               "Twist Mid",
                                               "double",
                                               0)

        self.tip_twist_att = self.addAnimParam("tip_twist",
                                               "Twist Tip",
                                               "double",
                                               0)

        # wide is Y
        self.mid_wide_att = self.addAnimParam("mid_wide",
                                              "Wide Mid",
                                              "double",
                                              1)

        self.tip_wide_att = self.addAnimParam("tip_wide",
                                              "Wide Tip",
                                              "double",
                                              1)

        # depth is Z
        self.mid_depth_att = self.addAnimParam("mid_depth",
                                               "Depth Mid",
                                               "double",
                                               1)

        self.tip_depth_att = self.addAnimParam("tip_depth",
                                               "Depth Tip",
                                               "double",
                                               1)

        #######################
        # setup Parameters
        #######################
        self.mid_twist_in_att = self.addSetupParam("mid_twist_in",
                                                   "mid_twist_in",
                                                   "double",
                                                   0)

        self.tip_twist_in_att = self.addSetupParam("tip_twist_in",
                                                   "tip_twist_in",
                                                   "double",
                                                   0)

        # wide is Y
        self.mid_wide_in_att = self.addSetupParam("mid_wide_in",
                                                  "mid_wide_in",
                                                  "double",
                                                  1)

        self.tip_wide_in_att = self.addSetupParam("tip_wide_in",
                                                  "tip_wide_in",
                                                  "double",
                                                  1)

        # depth is Z
        self.mid_depth_in_att = self.addSetupParam("mid_depth_in",
                                                   "mid_depth_in",
                                                   "double",
                                                   1)

        self.tip_depth_in_att = self.addSetupParam("tip_depth_in",
                                                   "tip_depth_in",
                                                   "double",
                                                   1)
        # OUT channels
        self.mid_twist_out_att = self.addSetupParam("mid_twist_out",
                                                    "mid_twist_out",
                                                    "double",
                                                    0)

        self.tip_twist_out_att = self.addSetupParam("tip_twist_out",
                                                    "tip_twist_out",
                                                    "double",
                                                    0)

        # wide is Y
        self.mid_wide_out_att = self.addSetupParam("mid_wide_out",
                                                   "mid_wide_out",
                                                   "double",
                                                   1)

        self.tip_wide_out_att = self.addSetupParam("tip_wide_out",
                                                   "tip_wide_out",
                                                   "double",
                                                   1)

        # depth is Z
        self.mid_depth_out_att = self.addSetupParam("mid_depth_out",
                                                    "mid_depth_out",
                                                    "double",
                                                    1)

        self.tip_depth_out_att = self.addSetupParam("tip_depth_out",
                                                    "tip_depth_out",
                                                    "double",
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
        # setup out channels. This channels are pass through for stack
        node.createPlusMinusAverage1D([self.mid_wide_att,
                                       self.mid_wide_in_att,
                                       -1.0],
                                      1,
                                      self.mid_wide_out_att)
        node.createPlusMinusAverage1D([self.mid_depth_att,
                                       self.mid_depth_in_att,
                                       -1.0],
                                      1,
                                      self.mid_depth_out_att)

        node.createPlusMinusAverage1D([self.tip_wide_att,
                                       self.tip_wide_in_att,
                                       -1.0],
                                      1,
                                      self.tip_wide_out_att)
        node.createPlusMinusAverage1D([self.tip_depth_att,
                                       self.tip_depth_in_att,
                                       -1.0],
                                      1,
                                      self.tip_depth_out_att)

        node.createPlusMinusAverage1D([self.mid_twist_att,
                                       self.mid_twist_in_att],
                                      1,
                                      self.mid_twist_out_att)

        node.createPlusMinusAverage1D([self.tip_twist_att,
                                       self.tip_twist_in_att],
                                      1,
                                      self.tip_twist_out_att)

        if not self.settings["simpleFK"]:
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

            step = 1.000 / (self.def_number - 1)
            step_mid = 1.000 / ((self.def_number - 1) / 2.0)
            u = 0.000
            u_mid = 0.000
            pass_mid = False
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

                # Connect scale Wide and Depth
                # wide and Depth
                mid_mul_node = node.createMulNode(
                    [self.mid_wide_att, self.mid_depth_att],
                    [self.mid_wide_in_att, self.mid_depth_in_att])
                mid_mul_node2 = node.createMulNode(
                    [mid_mul_node.outputX, mid_mul_node.outputY],
                    [u_mid, u_mid])
                mid_mul_node3 = node.createMulNode(
                    [mid_mul_node2.outputX, mid_mul_node2.outputY],
                    [dm_node_scl.attr("outputScaleX"),
                     dm_node_scl.attr("outputScaleY")])
                tip_mul_node = node.createMulNode(
                    [self.tip_wide_att, self.tip_depth_att],
                    [self.tip_wide_in_att, self.tip_depth_in_att])
                tip_mul_node2 = node.createMulNode(
                    [tip_mul_node.outputX, tip_mul_node.outputY],
                    [u, u])
                node.createPlusMinusAverage1D(
                    [mid_mul_node3.outputX,
                     1.0 - u_mid,
                     tip_mul_node2.outputX,
                     1.0 - u,
                     -1.0],
                    1,
                    self.div_cns[i].attr("sy"))
                node.createPlusMinusAverage1D(
                    [mid_mul_node3.outputY,
                     1.0 - u_mid,
                     tip_mul_node2.outputY,
                     1.0 - u,
                     -1.0],
                    1,
                    self.div_cns[i].attr("sz"))

                # Connect Twist "cns.frontTwist"
                twist_mul_node = node.createMulNode(
                    [self.mid_twist_att, self.tip_twist_att],
                    [u_mid, u])
                twist_mul_node2 = node.createMulNode(
                    [self.mid_twist_in_att, self.tip_twist_in_att],
                    [u_mid, u])
                node.createPlusMinusAverage1D(
                    [twist_mul_node.outputX,
                     twist_mul_node.outputY,
                     twist_mul_node2.outputX,
                     twist_mul_node2.outputY,
                     ],
                    1,
                    cns.frontTwist)

                # u_mid calc
                if u_mid >= 1.0 or pass_mid:
                    u_mid -= step_mid
                    pass_mid = True
                else:
                    u_mid += step_mid

                if u_mid > 1.0:
                    u_mid = 1.0

                # ensure the tip is never affected byt the mid
                if i == (self.def_number - 1):
                    u_mid = 0.0
                u += step

            if self.settings["keepLength"]:
                # add the safty distance offset
                self.tweakTip_npo.attr("tx").set(self.off_dist)
                # connect vis line ref
                for shp in self.line_ref.getShapes():
                    pm.connectAttr(self.ikVis_att, shp.attr("visibility"))

        # CONNECT STACK
        # master components
        mstr_global = self.settings["masterChainGlobal"]
        mstr_local = self.settings["masterChainLocal"]
        if mstr_global:
            mstr_global = self.rig.components[mstr_global]
        if mstr_local:
            mstr_local = self.rig.components[mstr_local]

        # connect twist and scale
        if mstr_global and mstr_local:
            node.createPlusMinusAverage1D([mstr_global.root.mid_twist_out,
                                           mstr_local.root.mid_twist_out],
                                          1,
                                          self.mid_twist_in_att)
            node.createPlusMinusAverage1D([mstr_global.root.tip_twist_out,
                                           mstr_local.root.tip_twist_out],
                                          1,
                                          self.tip_twist_in_att)
            node.createPlusMinusAverage1D([mstr_global.root.mid_wide_out,
                                           mstr_local.root.mid_wide_out,
                                           -1],
                                          1,
                                          self.mid_wide_in_att)
            node.createPlusMinusAverage1D([mstr_global.root.tip_wide_out,
                                           mstr_local.root.tip_wide_out,
                                           -1],
                                          1,
                                          self.tip_wide_in_att)
            node.createPlusMinusAverage1D([mstr_global.root.mid_depth_out,
                                           mstr_local.root.mid_depth_out,
                                           -1],
                                          1,
                                          self.mid_depth_in_att)
            node.createPlusMinusAverage1D([mstr_global.root.tip_depth_out,
                                           mstr_local.root.tip_depth_out,
                                           -1],
                                          1,
                                          self.tip_depth_in_att)
        elif mstr_local or mstr_global:
            for master_chain in [mstr_local, mstr_global]:
                if master_chain:
                    pm.connectAttr(master_chain.root.mid_twist_out,
                                   self.mid_twist_in_att)
                    pm.connectAttr(master_chain.root.tip_twist_out,
                                   self.tip_twist_in_att)
                    pm.connectAttr(master_chain.root.mid_wide_out,
                                   self.mid_wide_in_att)
                    pm.connectAttr(master_chain.root.tip_wide_out,
                                   self.tip_wide_in_att)
                    pm.connectAttr(master_chain.root.mid_depth_out,
                                   self.mid_depth_in_att)
                    pm.connectAttr(master_chain.root.tip_depth_out,
                                   self.tip_depth_in_att)
        # connect the fk chain ctls
        for e, ctl in enumerate(self.fk_ctl):
            # connect out
            out_loc = self.fk_local_out[e]
            applyop.gear_mulmatrix_op(ctl.attr("worldMatrix"),
                                      out_loc.attr("parentInverseMatrix[0]"),
                                      out_loc)
            out_glob = self.fk_global_out[e]
            out_ref = self.fk_global_ref[e]
            applyop.gear_mulmatrix_op(out_ref.attr("worldMatrix"),
                                      out_glob.attr("parentInverseMatrix[0]"),
                                      out_glob)
            # connect in global
            if mstr_global:
                self.connect_master(mstr_global.fk_global_out,
                                    self.fk_global_in,
                                    e,
                                    self.settings["cnxOffset"])

            # connect in local
            if mstr_local:
                self.connect_master(mstr_local.fk_local_out,
                                    self.fk_local_in,
                                    e,
                                    self.settings["cnxOffset"])

            for shp in ctl.getShapes():
                pm.connectAttr(self.fkVis_att, shp.attr("visibility"))

        for ctl in self.tweak_ctl:
            for shp in ctl.getShapes():
                pm.connectAttr(self.ikVis_att, shp.attr("visibility"))

        if self.settings["extraTweak"]:
            for tweak_ctl in self.extratweak_ctl:
                for shp in tweak_ctl.getShapes():
                    pm.connectAttr(self.tweakVis_att, shp.attr("visibility"))

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
