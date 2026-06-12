"""Component Control 01 module"""

from mgear.shifter import component

from mgear.core import attribute, transform, primitive

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

        self.ik_cns = primitive.addTransform(
            self.root, self.getName("ik_cns"), t)

        self.SDKctl = self.addCtl(self.ik_cns,
                                  "SDK_ctl",
                                  t,
                                  self.color_ik,
                                  "cube",
                                  w=self.settings["ctlSize"] * self.size * 1.35,
                                  h=self.settings["ctlSize"] * self.size * 0.75,
                                  d=self.settings["ctlSize"] * self.size * 0.75,
                                  tp=self.parentCtlTag)

        self.ctl = self.addCtl(self.SDKctl,
                               "ctl",
                               t,
                               self.color_fk,
                               "sphere",
                               w=self.settings["ctlSize"] * self.size,
                               h=self.settings["ctlSize"] * self.size,
                               d=self.settings["ctlSize"] * self.size,
                               tp=self.parentCtlTag)

        # we need to set the rotation order before lock any rotation axis
        if self.settings["k_ro"]:
            rotOderList = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]
            attribute.setRotOrder(
                self.ctl, rotOderList[self.settings["default_rotorder"]])
            attribute.setRotOrder(
                self.SDKctl, rotOderList[self.settings["default_rotorder"]])

        params = [s for s in
                  ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]
                  if self.settings["k_" + s]]
        attribute.setKeyableAttributes(self.ctl, params)
        attribute.setKeyableAttributes(self.SDKctl, params)

        if self.settings["joint"]:
            self.jnt_pos.append([self.ctl, 0, None, self.settings["uniScale"]])

    def addAttributes(self):
        # Ref
        if self.settings["ikrefarray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["ikrefarray"].split(","))
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam(
                    "ikref",
                    "Ik Ref",
                    0,
                    ref_names)

        # Identifiers
        # SDK Box -----------------------
        self.SDK_att = attribute.addAttribute(node=self.SDKctl,
                                              longName="is_SDK",
                                              attributeType="bool",
                                              value=True,
                                              keyable=False)

        self.SDKroot_att = attribute.addAttribute(node=self.SDKctl,
                                                  longName="ctl",
                                                  attributeType="string",
                                                  value="",
                                                  keyable=False)

        # Anim ctl -----------------------
        self.ctl_att = attribute.addAttribute(node=self.ctl,
                                              longName="is_tweak",
                                              attributeType="bool",
                                              value=True,
                                              keyable=False)

        self.ctlroot_att = attribute.addAttribute(node=self.ctl,
                                                  longName="sdk",
                                                  attributeType="string",
                                                  value="",
                                                  keyable=False)

    def addOperators(self):
        # component network
        pm.connectAttr(self.ctl.message, self.SDKroot_att, lock=True)
        pm.connectAttr(self.SDKctl.message, self.ctlroot_att, lock=True)

        if self.settings["customPivot"]:
            pm.xform(self.ctl, pivots=self.guide.pos["pivot"], worldSpace=True)
            pm.xform(self.SDKctl, pivots=self.guide.pos["pivot"], worldSpace=True)

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.ctl
        self.controlRelatives["root"] = self.ctl
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
