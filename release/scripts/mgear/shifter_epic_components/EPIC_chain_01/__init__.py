"""Component Lite Chain 01 module"""

from mgear.pymaya import datatypes

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

        if self.negate and self.settings["overrideNegate"]:
            self.negate = False
            self.n_factor = 1

        if self.settings["overrideNegate"]:
            self.mirror_conf = [0, 0, 1, 1, 1, 0, 0, 0, 0]
        else:
            self.mirror_conf = [0, 0, 0, 0, 0, 0, 0, 0, 0]

        # FK controllers ------------------------------------
        self.fk_npo = []
        self.fk_ctl = []
        t = self.guide.tra["root"]

        parent = self.root
        tOld = False
        fk_ctl = None
        self.previusTag = self.parentCtlTag
        for i, t in enumerate(
            transform.getChainTransform(
                self.guide.apos, self.normal, self.negate
            )
        ):
            dist = vector.getDistance(
                self.guide.apos[i], self.guide.apos[i + 1]
            )
            if self.settings["neutralpose"] or not tOld:
                tnpo = t
            else:
                tnpo = transform.setMatrixPosition(
                    tOld, transform.getPositionFromMatrix(t)
                )

            fk_npo = primitive.addTransform(
                parent, self.getName("fk%s_npo" % i), tnpo
            )
            fk_ctl = self.addCtl(
                fk_npo,
                "fk%s_ctl" % i,
                t,
                self.color_fk,
                "cube",
                w=dist,
                h=self.size * 0.1,
                d=self.size * 0.1,
                po=datatypes.Vector(dist * 0.5 * self.n_factor, 0, 0),
                tp=self.previusTag,
                mirrorConf=self.mirror_conf,
            )

            self.fk_npo.append(fk_npo)
            self.fk_ctl.append(fk_ctl)
            tOld = t
            self.previusTag = fk_ctl
            parent = fk_ctl
            if self.settings["addJoints"]:
                if i:
                    guide_relative_name = "{}_loc".format(str(i - 1))
                else:
                    guide_relative_name = "root"
                if self.settings["descriptionName"]:
                    jnt_name = "_".join([self.name, str(i + 1).zfill(2)])
                else:
                    jnt_name = str(i)
                self.jnt_pos.append(
                    {
                        "obj": fk_ctl,
                        "name": jnt_name,
                        "guide_relative": guide_relative_name,
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
        self.controlRelatives["%s_loc" % (len(self.fk_ctl) - 1)] = self.fk_ctl[
            -1
        ]
        self.jointRelatives["%s_loc" % (len(self.fk_ctl) - 1)] = (
            len(self.fk_ctl) - 1
        )
        self.aliasRelatives["%s_loc" % (len(self.fk_ctl) - 1)] = (
            len(self.fk_ctl) - 1
        )
