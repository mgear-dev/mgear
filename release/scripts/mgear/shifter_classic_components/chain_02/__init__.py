"""Component Chain 01 module"""

import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear import rigbits
from mgear.shifter import component

from mgear.core import node, applyop, vector
from mgear.core import attribute, transform, primitive

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

        self.isFk = self.settings["mode"] != 1
        self.isIk = self.settings["mode"] != 0
        self.isFkIk = self.settings["mode"] == 2

        self.WIP = self.options["mode"]

        # FK controllers ------------------------------------
        if self.isFk:
            self.fk_npo = []
            self.fk_ctl = []
            self.fk_ref = []
            self.fk_off = []
            self.previusTag = self.parentCtlTag

            previous_transform = False
            fk_ctl = None

            self.ik_cns = primitive.addTransform(
                self.root,
                self.getName("ik_cns"),
                transform.getTransformFromPos(self.guide.pos["root"])
            )

            chain_pos = transform.getChainTransform(
                self.guide.apos, self.normal, self.negate
            )

            for i, t in enumerate(chain_pos):
                dist = vector.getDistance(self.guide.apos[i], self.guide.apos[i + 1])
                if self.settings["mirrorBehaviour"] and self.negate:
                    dist = dist * -1

                if self.settings["neutralpose"] or not previous_transform:
                    if self.settings["mirrorBehaviour"] and self.negate:
                        tnpo = transform.setMatrixScale(t, [-1, -1, -1])
                    else:
                        tnpo = t
                else:
                    tnpo = transform.setMatrixPosition(
                        previous_transform, transform.getPositionFromMatrix(t)
                    )

                if i:
                    tref = transform.setMatrixPosition(
                        previous_transform, transform.getPositionFromMatrix(t)
                    )
                    fk_ref = primitive.addTransform(
                        fk_ctl, self.getName("fk%s_ref" % i), tref
                    )
                    self.fk_ref.append(fk_ref)
                else:
                    tref = t
                if self.settings["mirrorBehaviour"] and self.negate:
                    t_ctl = transform.setMatrixScale(t, [-1, -1, -1])
                else:
                    t_ctl = t

                fk_off = primitive.addTransform(
                    self.ik_cns, self.getName("fk%s_off" % i), tref
                )

                fk_npo = primitive.addTransform(
                    fk_off, self.getName("fk%s_npo" % i), tnpo
                )
                fk_ctl = self.addCtl(
                    fk_npo,
                    "fk%s_ctl" % i,
                    t_ctl,
                    self.color_fk,
                    "cube",
                    w=dist,
                    h=self.size * 0.1,
                    d=self.size * 0.1,
                    po=datatypes.Vector(dist * 0.5 * self.n_factor, 0, 0),
                    tp=self.previusTag,
                )

                self.fk_off.append(fk_off)
                self.fk_npo.append(fk_npo)
                self.fk_ctl.append(fk_ctl)
                previous_transform = t_ctl
                self.previusTag = fk_ctl

        # IK controllers ------------------------------------
        if self.isIk:

            normal = vector.getTransposedVector(
                self.normal,
                [self.guide.apos[0], self.guide.apos[1]],
                [self.guide.apos[-2], self.guide.apos[-1]],
            )
            t = transform.getTransformLookingAt(
                self.guide.apos[-2], self.guide.apos[-1], normal, "xy", self.negate
            )
            t = transform.setMatrixPosition(t, self.guide.apos[-1])

            self.ik_cns = primitive.addTransform(self.root, self.getName("ik_cns"), t)
            self.ikcns_ctl = self.addCtl(
                self.ik_cns,
                "ikcns_ctl",
                t,
                self.color_ik,
                "null",
                w=self.size,
                tp=self.parentCtlTag,
            )
            self.ik_ctl = self.addCtl(
                self.ikcns_ctl,
                "ik_ctl",
                t,
                self.color_ik,
                "cube",
                w=self.size * 0.3,
                h=self.size * 0.3,
                d=self.size * 0.3,
                tp=self.ikcns_ctl,
            )
            attribute.setKeyableAttributes(self.ik_ctl, self.t_params)

            v = self.guide.apos[-1] - self.guide.apos[0]
            v = v ^ self.normal
            v.normalize()
            v *= self.size
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
                w=self.size * 0.1,
                tp=self.parentCtlTag,
            )
            attribute.setKeyableAttributes(self.upv_ctl, self.t_params)

            # Chain
            self.chain = primitive.add2DChain(
                self.root,
                self.getName("chain"),
                self.guide.apos,
                self.normal,
                self.negate,
            )
            self.chain[0].attr("visibility").set(self.WIP)

        # Chain of deformers -------------------------------
        self.loc = []
        parent = self.root
        for i, t in enumerate(
            transform.getChainTransform(self.guide.apos, self.normal, self.negate)
        ):
            loc = primitive.addTransform(parent, self.getName("%s_loc" % i), t)

            self.loc.append(loc)
            self.jnt_pos.append([loc, i, None, False])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        # Anim -------------------------------------------
        if self.isFkIk:
            self.blend_att = self.addAnimParam(
                "blend", "Fk/Ik Blend", "double", self.settings["blend"], 0, 1
            )

        if self.isIk:
            self.roll_att = self.addAnimParam("roll", "Roll", "double", 0, -180, 180)

            # Ref
            if self.settings["ikrefarray"]:
                ref_names = self.get_valid_alias_list(
                    self.settings["ikrefarray"].split(",")
                )
                if len(ref_names) > 1:
                    self.ikref_att = self.addAnimEnumParam(
                        "ikref", "Ik Ref", 0, ref_names
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

        # Visibilities -------------------------------------
        if self.isFkIk:
            # fk
            fkvis_node = node.createReverseNode(self.blend_att)

            for fk_ctl in self.fk_ctl:
                for shp in fk_ctl.getShapes():
                    pm.connectAttr(fkvis_node + ".outputX", shp.attr("visibility"))

            # ik
            for shp in self.upv_ctl.getShapes():
                pm.connectAttr(self.blend_att, shp.attr("visibility"))
            for shp in self.ikcns_ctl.getShapes():
                pm.connectAttr(self.blend_att, shp.attr("visibility"))
            for shp in self.ik_ctl.getShapes():
                pm.connectAttr(self.blend_att, shp.attr("visibility"))

        # FK Chain -----------------------------------------
        if self.isFk:
            for off, ref in zip(self.fk_off[1:], self.fk_ref):
                applyop.gear_mulmatrix_op(
                    ref.worldMatrix, off.parentInverseMatrix, off, "rt"
                )
        # IK Chain -----------------------------------------
        if self.isIk:
            self.ikh = primitive.addIkHandle(self.root, self.getName("ikh"), self.chain)
            self.ikh.attr("visibility").set(False)

            # Constraint and up vector
            pm.pointConstraint(self.ik_ctl, self.ikh, maintainOffset=False)
            pm.poleVectorConstraint(self.upv_ctl, self.ikh)

            # TwistTest
            o_list = [
                round(elem, 4) for elem in transform.getTranslation(self.chain[1])
            ] != [round(elem, 4) for elem in self.guide.apos[1]]

            if o_list:
                add_nodeTwist = node.createAddNode(180.0, self.roll_att)
                pm.connectAttr(add_nodeTwist + ".output", self.ikh.attr("twist"))
            else:
                pm.connectAttr(self.roll_att, self.ikh.attr("twist"))

        # Chain of deformers -------------------------------
        for i, loc in enumerate(self.loc):

            if self.settings["mode"] == 0:  # fk only
                if self.settings["chainAiming"] == 1:
                    # Loop until the last one and connect aim constraints from index+1
                    if i < len(self.loc) - 1:
                        node_mtx_cns = applyop.gear_matrix_cns(
                            self.fk_ctl[i], loc, connect_srt="st"
                        )
                        node_mtx_cns.rename("{}_matrixConst".format(loc.shortName()))

                        # create an aimMatrix node
                        aim_matrix_node = pm.createNode("aimMatrix")
                        aim_matrix_node.rename("{}_aimMatrix".format(loc.shortName()))
                        dec_matrix_node = pm.createNode("decomposeMatrix")
                        dec_matrix_node.rename("{}_decomposeMatrix".format(loc.shortName()))

                        # setup with an aimMatrix
                        pm.connectAttr(
                            "{}.worldMatrix[0]".format(self.fk_ctl[i]),
                            "{}.inputMatrix".format(aim_matrix_node),
                        )
                        pm.connectAttr(
                            "{}.worldMatrix[0]".format(self.fk_ctl[i + 1]),
                            "{}.primary.primaryTargetMatrix".format(aim_matrix_node),
                        )

                        mult_mtx = node.createMultMatrixNode(
                            "{}.outputMatrix".format(aim_matrix_node),
                            "{}.parentInverseMatrix".format(loc),
                        )

                        pm.connectAttr(
                            "{}.matrixSum".format(mult_mtx),
                            "{}.inputMatrix".format(dec_matrix_node),
                        )
                        pm.connectAttr(
                            "{}.outputRotate".format(dec_matrix_node),
                            "{}.rotate".format(loc),
                        )
                    else:
                        # Then connect the last in the chain as a parent constraint
                        self.constraint_chain(self.fk_ctl[-1], self.loc[-1])
                else:
                    self.constraint_chain(self.fk_ctl[i], loc)

            elif self.settings["mode"] == 1:  # ik only
                self.constraint_chain(self.chain[i], loc)

            elif self.settings["mode"] == 2:  # fk/ik
                rev_node = node.createReverseNode(self.blend_att)

                # orientation
                cns = pm.parentConstraint(
                    self.fk_ctl[i], self.chain[i], loc, maintainOffset=False
                )
                cns.interpType.set(0)
                weight_att = pm.parentConstraint(cns, query=True, weightAliasList=True)
                pm.connectAttr(rev_node + ".outputX", cns + "." + weight_att[0])
                pm.connectAttr(self.blend_att, cns + "." + weight_att[1])

                # scaling
                blend_node = pm.createNode("blendColors")
                pm.connectAttr(self.chain[i].attr("scale"), blend_node + ".color1")
                pm.connectAttr(self.fk_ctl[i].attr("scale"), blend_node + ".color2")
                pm.connectAttr(self.blend_att, blend_node + ".blender")
                pm.connectAttr(blend_node + ".output", loc + ".scale")

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""

        self.relatives["root"] = self.loc[0]
        self.jointRelatives["root"] = 0

        if not self.isIk:
            self.controlRelatives["root"] = self.fk_ctl[0]
            self.controlRelatives["%s_loc" % (len(self.loc) - 1)] = self.fk_ctl[-1]
        else:
            self.controlRelatives["root"] = self.ik_ctl
            self.controlRelatives["%s_loc" % (len(self.loc) - 1)] = self.ik_ctl

        for i in range(0, len(self.loc) - 1):
            self.relatives["%s_loc" % i] = self.loc[i + 1]
            self.jointRelatives["%s_loc" % i] = i + 1
            self.aliasRelatives["%s_ctl" % i] = i + 1
            if not self.isIk:
                self.controlRelatives["%s_loc" % i] = self.fk_ctl[i + 1]
            else:
                self.controlRelatives["%s_loc" % i] = self.ik_ctl

        self.relatives["%s_loc" % (len(self.loc) - 1)] = self.loc[-1]
        self.jointRelatives["%s_loc" % (len(self.loc) - 1)] = len(self.loc) - 1
        self.aliasRelatives["%s_loc" % (len(self.loc) - 1)] = len(self.loc) - 1

    # @param self
    def addConnection(self):
        """Add more connection definition to the set"""

        self.connections["standard"] = self.connect_standard
        self.connections["orientation"] = self.connect_orientation
        self.connections["parent"] = self.connect_parent

    def connect_orientation(self):
        """orientation connection definition for the component"""
        self.connect_orientCns()

    def connect_standard(self):
        """standard connection definition for the component"""
        self.connect_standardWithSimpleIkRef()

    def connect_parent(self):
        self.connect_standardWithSimpleIkRef()

    def constraint_chain(self, src, dst):
        mat_node = applyop.gear_matrix_cns(src, dst, connect_srt="st")
        mat_node.rename("{}_matrixConst".format(dst.shortName()))
        dec_matrix_node = pm.createNode("decomposeMatrix")
        dec_matrix_node.rename("{}_decomposeMatrix".format(dst.shortName()))

        mult_mtx = node.createMultMatrixNode(
            "{}.worldMatrix[0]".format(src),
            "{}.parentInverseMatrix".format(dst),
        )
        pm.connectAttr(
            "{}.matrixSum".format(mult_mtx),
            "{}.inputMatrix".format(dec_matrix_node),
        )

        pm.connectAttr(
            "{}.outputRotate".format(dec_matrix_node), "{}.rotate".format(dst)
        )
