"""Component Lite Chain 01 module"""

from pymel.core import datatypes

from mgear.shifter import component

from mgear.core import transform, primitive, vector

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
        self.WIP = self.options["mode"]

        rot_offset = [
                self.settings["joint_rot_offset_x"],
                self.settings["joint_rot_offset_y"],
                self.settings["joint_rot_offset_z"],
            ]

        if self.negate and self.settings["overrideNegate"]:
            self.negate = False
            self.n_factor = 1

        if self.settings["overrideNegate"]:
            self.mirror_conf = [0, 0, 1,
                                1, 1, 0,
                                0, 0, 0]
        else:
            self.mirror_conf = [0, 0, 0,
                                0, 0, 0,
                                0, 0, 0]

        # FK controllers ------------------------------------
        self.fk_npo = []
        self.fk_ctl = []

        parent = self.root
        previous_transform = None
        self.previusTag = self.parentCtlTag

        chain_pos = transform.getChainTransform(
            self.guide.apos, self.normal, self.negate)

        for i, t in enumerate(chain_pos):
            if self.settings["neutralpose"] or not previous_transform:
                tnpo = t
            else:
                tnpo = transform.setMatrixPosition(
                    previous_transform,
                    transform.getPositionFromMatrix(t))

            dist = vector.getDistance(self.guide.apos[i], self.guide.apos[i + 1])
            if self.settings["mirrorBehaviour"] and self.negate:
                dist = dist * -1
                rot_offset = [180, 180, 0]
                tnpo = transform.setMatrixScale(t, [-1, -1, -1])

            fk_npo = primitive.addTransform(
                parent, self.getName("fk%s_npo" % i), tnpo)
            fk_ctl = self.addCtl(
                fk_npo,
                "fk%s_ctl" % i,
                tnpo,
                self.color_fk,
                "cube",
                w=dist,
                h=self.size * .1,
                d=self.size * .1,
                po=datatypes.Vector(dist * .5 * self.n_factor, 0, 0),
                tp=self.previusTag,
                mirrorConf=self.mirror_conf)

            self.fk_npo.append(fk_npo)
            self.fk_ctl.append(fk_ctl)
            self.previusTag = fk_ctl
            previous_transform = t
            parent = fk_ctl
            if self.settings["addJoints"]:
                self.jnt_pos.append(
                    {
                        "obj": fk_ctl,
                        "name": i,
                        "newActiveJnt": None,
                        "UniScale": False,
                        "rot_off": rot_offset
                    }
                )

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
        return
        # # Visibilities -------------------------------------

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""

        self.relatives["root"] = self.fk_ctl[0]
        self.controlRelatives["root"] = self.fk_ctl[0]
        self.jointRelatives["root"] = 0
        for i in range(0, len(self.fk_ctl) - 1):
            self.relatives["%s_loc" % i] = self.fk_ctl[i + 1]
            self.controlRelatives["%s_loc" % i] = self.fk_ctl[i + 1]
            self.jointRelatives["%s_loc" % i] = i + 1
            self.aliasRelatives["%s_ctl" % i] = i + 1
        self.relatives["%s_loc" % (len(self.fk_ctl) - 1)] = self.fk_ctl[-1]
        self.controlRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = self.fk_ctl[-1]
        self.jointRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = len(self.fk_ctl) - 1
        self.aliasRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = len(self.fk_ctl) - 1
