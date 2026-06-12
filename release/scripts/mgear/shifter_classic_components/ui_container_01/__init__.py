"""
Component UI Container 01 module
"""
import math

import mgear.pymaya as pm
import mgear.pymaya.datatypes as dt

from mgear.shifter import component
from mgear.core import attribute, primitive


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
        t = self.guide.tra["root"]

        # The border needs to fit the ctl range of motion
        size = self.settings["ctlSize"]
        margin = self.settings["margin"]

        self.ctl = None
        if self.settings["addController"]:
            self.ctl = self.addCtl(self.root,
                                   "ctl", t,
                                   self.color_ik, self.settings["icon"],
                                   d=size,
                                   h=size,
                                   w=size,
                                   tp=self.parentCtlTag,
                                   ro=dt.Vector(math.radians(90), 0, 0))
            self.ctl.scale.set([self.size, self.size, self.size])
            attribute.setKeyableAttributes(self.ctl, ["tx", "ty", "tz",
                                                      "rx", "ry", "rz",
                                                      "sx", "sy", "sz"])
        else:
            self.ctl = primitive.addTransform(self.root,
                                              self.getName("cns"), t)
            self.ctl.scale.set([self.size, self.size, self.size])
            attribute.setKeyableAttributes(self.ctl, [])

        self.border = self.addCtl(self.ctl,
                                  "border", t,
                                  self.color_ik, "square",
                                  w=size + margin,
                                  d=size + margin,
                                  tp=self.parentCtlTag,
                                  ro=dt.Vector(math.radians(90), 0, 0))
        border_shape = self.border.getShape()
        border_shape.overrideDisplayType.set(2)  # Set display to reference
        attribute.setKeyableAttributes(self.border, [])

    def finalize(self):
        """
        This runs after all the connections are made and the
        hierarchy is built.
        """
        children = self.border.getChildren(type="transform")
        if children:
            bbox = pm.exactWorldBoundingBox(children)
            # Update border to encapsulate the ui elements
            border_shape = self.border.getShape()
            margin = self.settings["margin"]

            cvs = [  # BL, BR, TR, TL, BL
                dt.Vector(bbox[0] - margin, bbox[1] - margin, bbox[2]),
                dt.Vector(bbox[3] + margin, bbox[1] - margin, bbox[2]),
                dt.Vector(bbox[3] + margin, bbox[4] + margin, bbox[2]),
                dt.Vector(bbox[0] - margin, bbox[4] + margin, bbox[2]),
                dt.Vector(bbox[0] - margin, bbox[1] - margin, bbox[2]),
            ]

            # Set cvs and update the shape.
            border_shape.setCVs(cvs, "world")
            border_shape.updateCurve()
        # Run default finalize logic.
        super(Component, self).finalize()

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.border
        self.controlRelatives["root"] = self.border
        self.aliasRelatives["root"] = "ctl"

    def addConnection(self):
        """Add more connection definition to the set"""
        self.connections["standard"] = self.connect_standard
