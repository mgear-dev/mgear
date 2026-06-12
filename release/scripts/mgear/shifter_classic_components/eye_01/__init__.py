"""Component Eye 01 module"""

from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import attribute, transform, primitive, applyop


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

        t = transform.getTransformFromPos(self.guide.pos["root"])

        self.eyeOver_npo = primitive.addTransform(
            self.root, self.getName("eyeOver_npo"), t)

        self.eyeOver_ctl = self.addCtl(self.eyeOver_npo,
                                       "Over_ctl",
                                       t,
                                       self.color_fk,
                                       "sphere",
                                       w=1 * self.size,
                                       tp=self.parentCtlTag,
                                       guide_loc_ref="root")
        self.eye_npo = primitive.addTransform(self.eyeOver_ctl,
                                              self.getName("eye_npo"),
                                              t)
        self.eyeFK_ctl = self.addCtl(self.eye_npo,
                                     "fk_ctl",
                                     t,
                                     self.color_fk,
                                     "arrow",
                                     w=1 * self.size,
                                     tp=self.eyeOver_ctl)

        # look at
        t = transform.getTransformFromPos(self.guide.pos["look"])
        self.ik_cns = primitive.addTransform(
            self.root, self.getName("ik_cns"), t)

        self.eyeIK_npo = primitive.addTransform(
            self.ik_cns, self.getName("ik_npo"), t)

        self.eyeIK_ctl = self.addCtl(self.eyeIK_npo,
                                     "ik_ctl",
                                     t,
                                     self.color_fk,
                                     "circle",
                                     w=.5 * self.size,
                                     tp=self.eyeFK_ctl,
                                     ro=datatypes.Vector([1.5708, 0, 0]),
                                     guide_loc_ref="look")
        attribute.setKeyableAttributes(self.eyeIK_ctl, self.t_params)

        self.jnt_pos.append([self.eyeFK_ctl, "eye", "parent_relative_jnt"])
        self.jnt_pos.append(
            [self.eyeOver_ctl, "eyeOver", "parent_relative_jnt", False])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

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

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """

        upvDir = self.settings["upVectorDirection"]
        if upvDir == 0:
            upvVec = [1, 0, 0]
        elif upvDir == 1:
            upvVec = [0, 1, 0]
        else:
            upvVec = [0, 0, 1]

        applyop.aimCns(
            self.eye_npo, self.eyeIK_ctl, "zy", 2, upvVec, self.root, False)

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.eyeFK_ctl
        self.relatives["look"] = self.eyeOver_ctl

        self.controlRelatives["root"] = self.eyeFK_ctl
        self.controlRelatives["look"] = self.eyeOver_ctl

        self.jointRelatives["root"] = 0
        self.jointRelatives["look"] = 1

        self.aliasRelatives["root"] = "eye"
        self.aliasRelatives["look"] = "eyeOver"

    def connect_standard(self):
        """standard connection definition for the component"""
        self.connect_standardWithSimpleIkRef()
