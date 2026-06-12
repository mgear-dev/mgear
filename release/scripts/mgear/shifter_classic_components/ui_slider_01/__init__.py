"""Component UI Slider 01 module"""
import math

import mgear.pymaya as pm
import mgear.pymaya.datatypes as dt

from mgear.shifter import component
from mgear.core import attribute, transform, primitive


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
        if self.settings["mirrorBehaviour"] and self.negate:
            scl = [1, 1, -1]
        else:
            scl = [1, 1, 1]
        t = transform.setMatrixScale(t, scl)

        # The border needs to fit the ctl range of motion
        size = self.settings["ctlSize"]

        minX = -1 if self.settings["tx_negative"] else 0
        maxX = 1 if self.settings["tx_positive"] else 0
        minY = -1 if self.settings["ty_negative"] else 0
        maxY = 1 if self.settings["ty_positive"] else 0

        margin = 0.1 * self.size

        border_offset = dt.Vector(minX + maxX, minY + maxY) * 0.5

        self.border = self.addCtl(self.root,
                                  "border", t,
                                  self.color_ik, "square",
                                  w=size + (maxX - minX) + margin,
                                  d=size + (maxY - minY) + margin,
                                  tp=self.parentCtlTag,
                                  po=border_offset,
                                  ro=dt.Vector(math.radians(90), 0, 0))
        border_shape = self.border.getShape()
        border_shape.overrideDisplayType.set(2)  # Set display to reference

        self.ctl = self.addCtl(self.border,
                               "ctl", t,
                               self.color_ik, self.settings["icon"],
                               d=size,
                               h=size,
                               w=size,
                               tp=self.parentCtlTag,
                               ro=dt.Vector(math.radians(90), 0, 0))

        self.border.scale.set([self.size, self.size, self.size])

        params = [s for s in ["tx", "ty"]
                  if self.settings[s + "_negative"] or self.settings[s + "_positive"]]
        attribute.setKeyableAttributes(self.ctl, params)
        attribute.setKeyableAttributes(self.border, [])

        tx_limit = [minX, maxX]
        ty_limit = [minY, maxY]

        pm.transformLimits(self.ctl, tx=tx_limit, etx=[1, 1])
        pm.transformLimits(self.ctl, ty=ty_limit, ety=[1, 1])

    def addAttributes(self):
        return

    def addOperators(self):
        return

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.ctl
        self.controlRelatives["root"] = self.ctl
        self.aliasRelatives["root"] = "ctl"

    def addConnection(self):
        """Add more connection definition to the set"""
        self.connections["standard"] = self.connect_standard
