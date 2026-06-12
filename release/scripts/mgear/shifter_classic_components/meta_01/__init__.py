"""Component Meta 01 module"""

import mgear.pymaya as pm

from mgear.shifter import component

from mgear.core import transform, primitive, node

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

        self.normal = self.guide.blades["blade"].z
        self.binormal = self.guide.blades["blade"].x

        # Chain of deformers -------------------------------
        self.locList = []
        self.ctlList = []
        self.npoList = []
        parent = self.root

        self.jointList = []
        self.previusTag = self.parentCtlTag
        for i, t in enumerate(transform.getChainTransform2(self.guide.apos,
                                                           self.normal,
                                                           self.negate)):

            lvl = primitive.addTransform(parent, self.getName("%s_lvl" % i), t)
            npo = primitive.addTransform(lvl, self.getName("%s_npo" % i), t)
            loc = primitive.addTransform(npo, self.getName("%s_loc" % i), t)
            jnt_parent = loc

            if self.settings["metaCtl"]:

                if i:
                    guide_loc_ref = "{}_loc".format(str(i - 1))
                else:
                    guide_loc_ref = "root"
                meta_ctl = self.addCtl(loc,
                                       "meta%s_ctl" % i,
                                       t,
                                       self.color_ik,
                                       "cube",
                                       w=self.size * .2,
                                       h=self.size * .2,
                                       d=self.size * .2,
                                       tp=self.previusTag,
                                       guide_loc_ref=guide_loc_ref)

                self.ctlList.append(meta_ctl)
                self.previusTag = meta_ctl
                jnt_parent = meta_ctl

            if self.settings["jointChainCnx"]:
                self.jnt_pos.append([jnt_parent, i])
            else:
                self.jnt_pos.append([jnt_parent, i, "parent_relative_jnt"])

            self.locList.append(loc)
            self.npoList.append(npo)
            if i == len(self.guide.apos) - 1:
                ctl_npo = primitive.addTransform(self.root,
                                                 self.getName("ctl_npo"),
                                                 t)

                self.meta_ctl = self.addCtl(ctl_npo,
                                            "ctl",
                                            t,
                                            self.color_fk,
                                            "cube",
                                            w=self.size * .5,
                                            h=self.size * .5,
                                            d=self.size * .5,
                                            tp=self.parentCtlTag)

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""
        return

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        inc = 1.0 / (len(self.guide.apos) - 1)
        val = 0.0
        for i, loc in enumerate(self.locList):
            blendNode = node.createPairBlend(
                self.npoList[i], self.meta_ctl, blender=val)
            if self.settings["intRotation"]:
                pm.connectAttr(blendNode.attr("outRotate"), loc.attr("rotate"))
            if self.settings["intTranslation"]:
                pm.connectAttr(blendNode.attr("outTranslate"),
                               loc.attr("translate"))
            if self.settings["intScale"]:
                scaleA = [self.meta_ctl.attr("sx"),
                          self.meta_ctl.attr("sy"),
                          self.meta_ctl.attr("sz")]

                scaleB = [self.npoList[i].attr("sx"),
                          self.npoList[i].attr("sy"),
                          self.npoList[i].attr("sz")]

                scaleBlend = node.createBlendNode(scaleA, scaleB, val)
                pm.connectAttr(scaleBlend.attr("output"), loc.attr("scale"))
            val += inc

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""

        self.relatives["root"] = self.locList[0]
        self.jointRelatives["root"] = 0
        self.controlRelatives["root"] = self.meta_ctl
        for i in range(len(self.locList) - 1):
            self.relatives["%s_loc" % i] = self.locList[i + 1]
            self.controlRelatives["%s_loc" % i] = self.meta_ctl
            self.jointRelatives["%s_loc" % i] = i + 1
