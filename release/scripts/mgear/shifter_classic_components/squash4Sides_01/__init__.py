"""Component Squash 4 Sides 01 module"""

import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import attribute, transform, primitive, node, vector

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

        ctlSize = vector.getDistance(
            self.guide.apos[0], self.guide.apos[1]) / 3.0

        t_root = self.guide.tra["root"]
        t_root = transform.setMatrixScale(t_root)

        self.ik_cns = primitive.addTransform(
            self.root, self.getName("ik_cns"), t_root)

        t = transform.setMatrixPosition(t_root, self.guide.pos["top"])

        self.top_npo = primitive.addTransform(
            self.ik_cns, self.getName("top_npo"), t)

        self.top_ctl = self.addCtl(self.top_npo,
                                   "top_ctl",
                                   t,
                                   self.color_ik,
                                   "arrow",
                                   w=ctlSize,
                                   ro=datatypes.Vector(1.5708, 1.5708, 0),
                                   tp=self.parentCtlTag)

        attribute.setKeyableAttributes(self.top_ctl, ["ty"])

        t = transform.setMatrixPosition(t_root, self.guide.pos["bottom"])
        self.bottom_npo = primitive.addTransform(
            self.top_npo, self.getName("bottom_npo"), t)

        self.bottom_npo.rz.set(180)
        self.bottom_ctl = self.addCtl(self.bottom_npo,
                                      "bottom_ctl",
                                      t,
                                      self.color_ik,
                                      "arrow",
                                      w=ctlSize,
                                      ro=datatypes.Vector(1.5708, 1.5708, 0),
                                      tp=self.parentCtlTag)

        self.bottom_ctl.rz.set(0)
        attribute.setKeyableAttributes(self.bottom_ctl, ["ty"])
        self.bottom_pivot = primitive.addTransform(
            self.bottom_npo,
            self.getName("bottom_pivot"),
            transform.getTransform(self.top_ctl))

        t = transform.setMatrixPosition(t_root, self.guide.pos["ext"])
        self.ext_npo = primitive.addTransform(
            self.bottom_pivot, self.getName("ext_npo"), t)

        self.ext_npo.rz.set(-90)
        self.ext_ctl = self.addCtl(self.ext_npo,
                                   "ext_ctl",
                                   t,
                                   self.color_ik,
                                   "arrow",
                                   w=ctlSize,
                                   ro=datatypes.Vector(1.5708, 1.5708, 0),
                                   tp=self.parentCtlTag)

        self.ext_ctl.rz.set(0)
        attribute.setKeyableAttributes(self.ext_ctl, ["ty"])

        t = transform.setMatrixPosition(t_root, self.guide.pos["int"])
        self.int_npo = primitive.addTransform(
            self.ext_npo, self.getName("int_npo"), t)

        self.int_npo.rz.set(180)
        self.int_ctl = self.addCtl(self.int_npo,
                                   "int_ctl",
                                   t,
                                   self.color_ik,
                                   "arrow",
                                   w=ctlSize,
                                   ro=datatypes.Vector(1.5708, 1.5708, 0),
                                   tp=self.parentCtlTag)

        self.int_ctl.rz.set(0)
        attribute.setKeyableAttributes(self.int_ctl, ["ty"])

        self.int_pivot = primitive.addTransform(
            self.int_npo,
            self.getName("int_pivot"),
            transform.getTransform(self.ext_ctl))

        self.anchor = primitive.addTransform(
            self.int_pivot,
            self.getName("int_npo"),
            transform.getTransform(self.ik_cns))

        if self.settings["joint"]:
            self.jnt_pos.append([self.anchor, 0, None, False])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        self.volume_att = self.addAnimParam(
            "volume", "Volume", "double", 1, 0, 1)

        # Ref
        if self.settings["ikrefarray"]:
            ref_names = self.settings["ikrefarray"].split(",")
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam(
                    "ikref",
                    "Ik Ref",
                    0,
                    self.settings["ikrefarray"].split(","))

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        pairs = [[self.top_ctl, self.bottom_npo, 1, 2],
                 [self.bottom_ctl, self.bottom_pivot, 2, 1],
                 [self.ext_ctl, self.int_npo, 3, 4],
                 [self.int_ctl, self.int_pivot, 4, 3]]

        for pair in pairs:
            d = vector.getDistance(self.guide.apos[pair[2]],
                                   self.guide.apos[pair[3]])

            sum_node = node.createPlusMinusAverage1D([d, pair[0].ty])
            mul_node = node.createMulNode(pair[0].ty, self.volume_att)
            sum2_node = node.createPlusMinusAverage1D([d, mul_node.outputX])
            mul2_node = node.createDivNode(
                [sum2_node.output1D, sum_node.output1D, sum2_node.output1D],
                [d, d, d])

            sum3D_node = pm.createNode("plusMinusAverage")
            sum3D_node.attr("operation").set(2)
            sum3D_node.input3D[0].input3Dx.set(2)
            sum3D_node.input3D[0].input3Dz.set(2)
            mul2_node.outputX >> sum3D_node.input3D[1].input3Dx
            mul2_node.outputZ >> sum3D_node.input3D[1].input3Dz
            sum3D_node.output3D.output3Dx >> pair[1].sx
            mul2_node.outputY >> pair[1].sy
            sum3D_node.output3D.output3Dx >> pair[1].sz

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.anchor
        self.relatives["top"] = self.anchor
        self.relatives["bottom"] = self.anchor
        self.relatives["int"] = self.anchor
        self.relatives["ext"] = self.anchor

        self.controlRelatives["root"] = self.parentCtlTag
        self.controlRelatives["top"] = self.top_ctl
        self.controlRelatives["bottom"] = self.bottom_ctl
        self.controlRelatives["int"] = self.int_ctl
        self.controlRelatives["ext"] = self.ext_ctl

        if self.settings["joint"]:
            self.jointRelatives["root"] = 0
            self.jointRelatives["top"] = 0
            self.jointRelatives["bottom"] = 0
            self.jointRelatives["int"] = 0
            self.jointRelatives["ext"] = 0

    def connect_standard(self):
        self.connect_standardWithSimpleIkRef()
