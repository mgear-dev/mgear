"""
MIT License

Copyright (c) 2011-2018 Jeremie Passerin, Miquel Campos - from 2018 The mGear-Dev Organization

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import ast
from mgear.shifter import component

from mgear.core import attribute
from mgear.core import transform
from mgear.core import primitive
from mgear.core import applyop
from mgear.core import node
import mgear.pymaya as pm

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

        if self.settings["neutralRotation"]:
            t = transform.getTransformFromPos(self.guide.pos["root"])
        else:
            t = self.guide.tra["root"]
            if self.settings["mirrorBehaviour"] and self.negate:
                scl = [1, 1, -1]
            else:
                scl = [1, 1, 1]
            t = transform.setMatrixScale(t, scl)
        if self.settings["joint"] and self.settings["leafJoint"]:
            pm.displayInfo("Skipping ctl creation, just leaf joint")
            self.have_ctl = False
        else:
            self.have_ctl = True
            self.ik_cns = primitive.addTransform(
                self.root, self.getName("ik_cns"), t
            )
            self.rbf_ctl = []
            rbf_ctl_parent = self.ik_cns
            size_inc = (self.size / 2) / self.settings["rbf_layers"]
            size_add = size_inc
            for i in range(self.settings["rbf_layers"]):

                rbf_ctl = self.addCtl(
                    rbf_ctl_parent,
                    "rbf{}_ctl".format(str(i).zfill(3)),
                    t,
                    self.color_fk,
                    "cubewithpeak",
                    w=self.settings["ctlSize"] * (self.size / 4) + size_add,
                    h=self.settings["ctlSize"] * (self.size / 4) + size_add,
                    d=self.settings["ctlSize"] * (self.size / 4) + size_add,
                    tp=self.parentCtlTag,
                    guide_loc_ref="root",
                    add_2_grp=False,
                )
                size_add += size_inc
                self.rbf_ctl.append(rbf_ctl)
                rbf_ctl_parent = rbf_ctl

            self.rbf_ref = primitive.addTransform(
                self.ik_cns, self.getName("rbf_ref"), t
            )

            self.ctl_npo = primitive.addTransform(
                self.ik_cns, self.getName("npo"), t
            )
            self.jnt_lvl = primitive.addTransform(
                self.ctl_npo, self.getName("jnt_lvl"), t
            )
            ctl_name = ast.literal_eval(
                self.settings["ctlNamesDescription_custom"]
            )[0]

            self.ctl = self.addCtl(
                self.ctl_npo,
                ctl_name,
                t,
                self.color_ik,
                self.settings["icon"],
                w=self.settings["ctlSize"] * self.size,
                h=self.settings["ctlSize"] * self.size,
                d=self.settings["ctlSize"] * self.size,
                tp=self.parentCtlTag,
                guide_loc_ref="root",
            )

            # we need to set the rotation order before lock any rotation axis
            if self.settings["k_ro"]:
                rotOderList = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]
                attribute.setRotOrder(
                    self.ctl, rotOderList[self.settings["default_rotorder"]]
                )

            params = [
                s
                for s in [
                    "tx",
                    "ty",
                    "tz",
                    "ro",
                    "rx",
                    "ry",
                    "rz",
                    "sx",
                    "sy",
                    "sz",
                ]
                if self.settings["k_" + s]
            ]
            attribute.setKeyableAttributes(self.ctl, params)
        if self.settings["joint"]:

            # TODO WIP: add new attr for seeting leaf joint + not build objcts
            if self.settings["leafJoint"]:
                input_transform = t
            else:
                input_transform = self.jnt_lvl

            if self.settings["descriptionName"]:
                jnt_name = self.name
            else:
                jnt_name = "0"
            self.jnt_pos.append(
                {
                    "obj": input_transform,
                    "name": jnt_name,
                    "guide_relative": "root",
                    "UniScale": self.settings["uniScale"],
                }
            )

    def addAttributes(self):
        if self.settings["leafJoint"]:
            return

        self.ctlVis_att = self.addAnimParam("ctl_vis", "Ctl Vis", "bool", True)

        self.rbfVis_att = []
        for i in range(self.settings["rbf_layers"]):
            rbfVis_att = self.addAnimParam(
                "rbf{}_ctl_vis".format(str(i).zfill(3)),
                "RBF {} Ctl Vis".format(str(i).zfill(3)),
                "bool",
                False,
            )
            self.rbfVis_att.append(rbfVis_att)

        # rbf transform multipliers
        self.RBFMult_att = self.addAnimParam("RBFMult", "RBF Mult", "float", 1)

        # Remap multipliers
        self.remap_tx_att = self.addAnimParam(
            "remapTX", "Remap TX", "float", 1
        )
        self.remap_ty_att = self.addAnimParam(
            "remapTY", "Remap TY", "float", 1
        )
        self.remap_tz_att = self.addAnimParam(
            "remapTZ", "Remap TZ", "float", 1
        )

        self.remap_rx_att = self.addAnimParam(
            "remapRX", "Remap RX", "float", 1
        )
        self.remap_ry_att = self.addAnimParam(
            "remapRY", "Remap RY", "float", 1
        )
        self.remap_rz_att = self.addAnimParam(
            "remapRZ", "Remap RZ", "float", 1
        )

        self.remap_sx_att = self.addAnimParam(
            "remapSX", "Remap SX", "float", 1
        )
        self.remap_sy_att = self.addAnimParam(
            "remapSY", "Remap SY", "float", 1
        )
        self.remap_sz_att = self.addAnimParam(
            "remapSZ", "Remap SZ", "float", 1
        )

        # Ref
        if self.have_ctl:
            if self.settings["ikrefarray"]:
                ref_names = self.get_valid_alias_list(
                    self.settings["ikrefarray"].split(",")
                )
                if len(ref_names) > 1:
                    self.ikref_att = self.addAnimEnumParam(
                        "ikref", "Ik Ref", 0, ref_names
                    )

        # SETUP param
        # ctl transform multipliers
        self.ctlTransMult_att = self.addSetupParam(
            "ctlTransMult",
            "Ctl Translate Mult",
            "float",
            self.settings["ctlTransMult"],
        )
        self.ctlRotMult_att = self.addSetupParam(
            "ctlRotMult",
            "Ctl Rotate Mult",
            "float",
            self.settings["ctlRotMult"],
        )
        self.ctlSclMult_att = self.addSetupParam(
            "ctlSclMult",
            "Ctl Scale Mult",
            "float",
            self.settings["ctlSclMult"],
        )

    def addOperators(self):
        if self.settings["leafJoint"]:
            return
        # visibilities
        for shp in self.ctl.getShapes():
            pm.connectAttr(self.ctlVis_att, shp.attr("visibility"))
        for i in range(self.settings["rbf_layers"]):
            for shp in self.rbf_ctl[i].getShapes():
                pm.connectAttr(self.rbfVis_att[i], shp.attr("visibility"))

        # RBF reference transform
        applyop.gear_mulmatrix_op(
            self.rbf_ctl[-1].attr("worldMatrix"),
            self.rbf_ref.attr("parentInverseMatrix[0]"),
            self.rbf_ref,
        )

        # ctl npo RBF
        node.createMulNode(
            [self.rbf_ref.tx, self.rbf_ref.ty, self.rbf_ref.tz],
            [self.RBFMult_att] * 3,
            [self.ctl_npo.tx, self.ctl_npo.ty, self.ctl_npo.tz],
        )
        node.createMulNode(
            [self.rbf_ref.rx, self.rbf_ref.ry, self.rbf_ref.rz],
            [self.RBFMult_att] * 3,
            [self.ctl_npo.rx, self.ctl_npo.ry, self.ctl_npo.rz],
        )

        # ctl multiplier to jnt
        # translate
        mult_node = node.createMulNode(
            [self.ctl.tx, self.ctl.ty, self.ctl.tz],
            [self.ctlTransMult_att] * 3,
        )
        node.createMulNode(
            [mult_node.outputX, mult_node.outputY, mult_node.outputZ],
            [self.remap_tx_att, self.remap_ty_att, self.remap_tz_att],
            [self.jnt_lvl.tx, self.jnt_lvl.ty, self.jnt_lvl.tz],
        )

        # rotate
        mult_node = node.createMulNode(
            [self.ctl.rx, self.ctl.ry, self.ctl.rz],
            [self.ctlRotMult_att] * 3,
        )
        node.createMulNode(
            [mult_node.outputX, mult_node.outputY, mult_node.outputZ],
            [self.remap_rx_att, self.remap_ry_att, self.remap_rz_att],
            [self.jnt_lvl.rx, self.jnt_lvl.ry, self.jnt_lvl.rz],
        )

        # scale
        mult_node = node.createMulNode(
            [self.ctl.sx, self.ctl.sy, self.ctl.sz],
            [self.ctlSclMult_att] * 3,
        )
        node.createMulNode(
            [mult_node.outputX, mult_node.outputY, mult_node.outputZ],
            [self.remap_sx_att, self.remap_sy_att, self.remap_sz_att],
            [self.jnt_lvl.sx, self.jnt_lvl.sy, self.jnt_lvl.sz],
        )

    # =====================================================
    # CONNECTOR
    # =====================================================

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        if self.have_ctl:
            self.relatives["root"] = self.jnt_lvl
            self.controlRelatives["root"] = self.ctl

        else:
            self.relatives["root"] = self.root
            self.controlRelatives["root"] = None

        if self.settings["joint"]:
            self.jointRelatives["root"] = 0
        self.aliasRelatives["root"] = "ctl"

    def addConnection(self):
        """Add more connection definition to the set"""
        self.connections["standard"] = self.connect_standard
        self.connections["orientation"] = self.connect_orientation

    def connect_standard(self):
        """standard connection definition for the component"""
        self.connect_standardWithSimpleIkRef()

    def connect_orientation(self):
        """Orient connection definition for the component"""
        self.connect_orientCns()
