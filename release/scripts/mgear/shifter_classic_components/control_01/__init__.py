"""Component Control 01 module"""
import ast
from mgear.shifter import component

from mgear.core import attribute, transform, primitive
from mgear.pymaya import datatypes
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
            ctl_name = ast.literal_eval(
                self.settings["ctlNamesDescription_custom"]
            )[0]
            self.ik_cns = primitive.addTransform(
                self.root, self.getName("ik_cns"), t)

            self.ctl = self.addCtl(self.ik_cns,
                                   ctl_name,
                                   t,
                                   self.color_ik,
                                   self.settings["icon"],
                                   w=self.settings["ctlSize"] * self.size,
                                   h=self.settings["ctlSize"] * self.size,
                                   d=self.settings["ctlSize"] * self.size,
                                   tp=self.parentCtlTag,
                                   guide_loc_ref="root")

            # we need to set the rotation order before lock any rotation axis
            if self.settings["k_ro"]:
                rotOderList = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]
                attribute.setRotOrder(
                    self.ctl, rotOderList[self.settings["default_rotorder"]])

            params = [s for s in
                      ["tx", "ty", "tz", "ro", "rx",
                       "ry", "rz", "sx", "sy", "sz"]
                      if self.settings["k_" + s]]
            attribute.setKeyableAttributes(self.ctl, params)
        if self.settings["joint"]:
            # TODO WIP: add new attr for seeting leaf joint + not build objcts
            if self.settings["leafJoint"]:
                self.jnt_pos.append([t, 0, None, self.settings["uniScale"]])
            else:
                self.jnt_pos.append(
                    {
                        "obj": self.ctl,
                        "name": 0,
                        "guide_relative": "root",
                        "UniScale": self.settings["uniScale"],
                        "leaf_joint": self.settings["addLeafJoint"],
                    }
                )

    def addAttributes(self):
        # Ref
        if self.have_ctl:
            if self.settings["ikrefarray"]:
                ref_names = self.get_valid_alias_list(
                    self.settings["ikrefarray"].split(","))
                if len(ref_names) > 1:
                    self.ikref_att = self.addAnimEnumParam(
                        "ikref",
                        "Ik Ref",
                        0,
                        ref_names)

    def addOperators(self):
        return

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        if self.have_ctl:
            self.relatives["root"] = self.ctl
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
        self.connections["position"] = self.connect_position
        self.connections["point"] = self.connect_point

    def connect_standard(self):
        """standard connection definition for the component"""
        self.connect_standardWithSimpleIkRef()

    def connect_orientation(self):
        """Orient connection definition for the component"""
        self.connect_orientCns()

    def connect_position(self):
        """position connection definition for the component"""
        self.connect_positionCns()

    def connect_point(self):
        """point connection definition for the component"""
        self.connect_pointCns()
