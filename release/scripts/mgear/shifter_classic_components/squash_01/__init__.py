"""Component Squash 01 module"""

import mgear.pymaya as pm
import mgear.pymaya.datatypes as dt

from mgear.shifter import component

from mgear.core import primitive, transform, applyop, attribute, node, vector

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

        t = transform.getTransformLookingAt(
            self.guide.apos[0],
            self.guide.apos[1],
            self.normal,
            axis="yx",
            negate=self.negate,
        )
        self.ctl_npo = primitive.addTransform(
            self.root, self.getName("ctl_npo"), t
        )
        self.ctl = self.addCtl(
            self.ctl_npo,
            "base_ctl",
            t,
            self.color_ik,
            "square",
            w=1.0,
            tp=self.parentCtlTag,
        )

        self.ref_base = primitive.addTransform(
            self.ctl, self.getName("ref_base"), t
        )
        self.in_SDK = primitive.addTransform(
            self.ref_base, self.getName("in_SDK"), t
        )

        t = transform.setMatrixPosition(t, self.guide.apos[1])

        self.ik_cns = primitive.addTransform(
            self.ctl, self.getName("ik_cns"), t
        )
        self.squash_npo = primitive.addTransform(
            self.ik_cns, self.getName("squash_npo"), t
        )
        self.squash_ctl = self.addCtl(
            self.squash_npo,
            "squash_ctl",
            t,
            self.color_ik,
            "crossarrow",
            w=1.0,
            ro=dt.Vector(1.5708, 0, 0),
            tp=self.ctl,
        )

        attribute.setKeyableAttributes(self.squash_ctl, ["tx", "ty", "tz"])

        self.ref_squash = primitive.addTransform(
            self.squash_ctl, self.getName("ref_squash"), t
        )

        self.div_cns = []

        div_cns = primitive.addTransform(self.root, self.getName("div0_loc"))

        self.div_cns.append(div_cns)
        self.jnt_pos.append([div_cns, 0, None, False])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        # Ref
        if self.settings["ikrefarray"]:
            ref_names = self.settings["ikrefarray"].split(",")
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam(
                    "ikref",
                    "Ik Ref",
                    0,
                    self.settings["ikrefarray"].split(","),
                )

        # setup param
        self.squashX_att = self.addSetupParam(
            "squashX",
            "Squash X Mult",
            "double",
            self.settings["squashX"],
            0,
            1,
        )
        self.squashY_att = self.addSetupParam(
            "squashY",
            "Squash Y Mult",
            "double",
            self.settings["squashY"],
            0,
            1,
        )
        self.squashZ_att = self.addSetupParam(
            "squashZ",
            "Squash Z Mult",
            "double",
            self.settings["squashZ"],
            0,
            1,
        )

        self.stretchX_att = self.addSetupParam(
            "stretchX",
            "Stretch X Mult",
            "double",
            self.settings["stretchX"],
            0,
            1,
        )
        self.stretchY_att = self.addSetupParam(
            "stretchY",
            "Stretch Y Mult",
            "double",
            self.settings["stretchY"],
            0,
            1,
        )
        self.stretchZ_att = self.addSetupParam(
            "stretchZ",
            "Stretch Z Mult",
            "double",
            self.settings["stretchZ"],
            0,
            1,
        )

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators/Solvers, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        applyop.aimCns(
            self.ref_base,
            self.squash_ctl,
            axis="yx",
            wupType=2,
            wupVector=[1, 0, 0],
            wupObject=self.ctl,
            maintainOffset=False,
        )
        applyop.aimCns(
            self.ref_squash,
            self.ctl,
            axis="-yx",
            wupType=2,
            wupVector=[1, 0, 0],
            wupObject=self.squash_ctl,
            maintainOffset=False,
        )
        bIncrement = 1.0
        blend = 0
        for i, div_cns in enumerate(self.div_cns):
            intMatrix = applyop.gear_intmatrix_op(
                self.in_SDK.attr("worldMatrix"),
                self.ref_squash.attr("worldMatrix"),
                blend,
            )

            applyop.gear_mulmatrix_op(
                intMatrix.attr("output"),
                div_cns.attr("parentInverseMatrix[0]"),
                div_cns,
            )

            blend = blend + bIncrement

        d = vector.getDistance(self.guide.apos[0], self.guide.apos[1])
        dist_node = node.createDistNode(self.squash_ctl, self.ctl)

        rootWorld_node = node.createDecomposeMatrixNode(
            self.ctl.attr("worldMatrix")
        )

        div_node = node.createDivNode(
            dist_node + ".distance", rootWorld_node + ".outputScaleY"
        )

        div_node = node.createDivNode(div_node + ".outputX", d)
        rev_node = node.createReverseNode(div_node + ".outputX")
        add_node = pm.createNode("plusMinusAverage")

        add_node.input1D[0].set(1.0)
        rev_node.outputX >> add_node.input1D[1]

        # div_node.outputX >> self.ref_base.scaleY
        # add_node.output1D >> self.ref_base.scaleX
        # add_node.output1D >> self.ref_base.scaleZ

        self.conditional_scale_multiplier(
            div_node.outputX,
            div_node.outputX,
            self.stretchX_att,
            self.squashX_att,
            self.ref_base.scaleX,
        )
        self.conditional_scale_multiplier(
            div_node.outputX,
            add_node.output1D,
            self.stretchY_att,
            self.squashY_att,
            self.ref_base.scaleY,
        )
        self.conditional_scale_multiplier(
            div_node.outputX,
            div_node.outputX,
            self.stretchZ_att,
            self.squashZ_att,
            self.ref_base.scaleZ,
        )

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.ref_base
        self.relatives["squash"] = self.ref_squash

        self.controlRelatives["root"] = self.ctl
        self.controlRelatives["squash"] = self.squash_ctl

        for i in range(0, len(self.div_cns) - 1):
            self.relatives["%s_loc" % i] = self.div_cns[i + 1]
            self.jointRelatives["%s_loc" % i] = i + 1
        self.relatives["%s_loc" % (len(self.div_cns) - 1)] = self.div_cns[-1]
        jnt_rel_len = len(self.div_cns) - 1
        self.jointRelatives["%s_loc" % (len(self.div_cns) - 1)] = jnt_rel_len

    def connect_standard(self):
        """standard connection definition for the component"""
        self.connect_standardWithSimpleIkRef()

    # helper
    def conditional_scale_multiplier(
        self, cond_attr, driver_attr, attrA, attrB, output_value
    ):
        """
        Adjusts the output value to be 1 when driver_attr is 1.0, and uses attrA or attrB
        to multiply based on the difference from 1.0 when driver_attr changes.

        Args:
            driver_attr (pm.Attribute): The driving attribute.
            attrA (pm.Attribute): Attribute to multiply with if driver_attr differs from 1.0.
            attrB (pm.Attribute): Attribute to multiply with if driver_attr differs from 1.0.
            output_value (pm.Attribute): The attribute to receive the final scaled value.
        """
        # Create necessary nodes
        condition_node = pm.createNode("condition")
        multiply_node_a = pm.createNode("multiplyDivide")
        multiply_node_b = pm.createNode("multiplyDivide")
        plus_minus_node = pm.createNode("plusMinusAverage")
        subtract_node = pm.createNode("plusMinusAverage")

        # Setup subtract node to calculate difference from 1.0
        subtract_node.operation.set(2)  # Subtract operation
        subtract_node.input1D[0].set(1.0)
        driver_attr >> subtract_node.input1D[1]

        # Setup condition node
        cond_attr >> condition_node.firstTerm
        condition_node.secondTerm.set(1)
        condition_node.operation.set(4)  # Less than

        # Connect subtract node to multiply nodes
        subtract_node.output1D >> multiply_node_a.input1X
        attrA >> multiply_node_a.input2X
        subtract_node.output1D >> multiply_node_b.input1X
        attrB >> multiply_node_b.input2X

        # Connect multiply nodes to condition node
        multiply_node_a.outputX >> condition_node.colorIfFalseR
        multiply_node_b.outputX >> condition_node.colorIfTrueR

        # Setup plusMinusAverage node
        plus_minus_node.operation.set(1)  # Sum operation
        plus_minus_node.input1D[0].set(1.0)
        condition_node.outColorR >> plus_minus_node.input1D[1]

        # Connect plusMinusAverage node to output value
        plus_minus_node.output1D >> output_value
