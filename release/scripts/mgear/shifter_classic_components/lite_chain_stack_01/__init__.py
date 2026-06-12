"""Component chain FK spline 01 module"""

import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import transform, primitive, vector, applyop
from mgear.core import attribute

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

            self.previusTag = fk_ctl

            if self.settings["addJoints"]:
                self.jnt_pos.append([fk_ctl, i, None, False])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""
        self.fkVis_att = self.addAnimParam("FK_vis",
                                           "FK vis",
                                           "bool",
                                           True)

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """

        # CONNECT STACK
        # master components
        mstr_global = self.settings["masterChainGlobal"]
        mstr_local = self.settings["masterChainLocal"]
        if mstr_global:
            mstr_global = self.rig.components[mstr_global]
        if mstr_local:
            mstr_local = self.rig.components[mstr_local]

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
