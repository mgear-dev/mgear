"""Component Chain Spring Gravity 02 module"""

import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component
from mgear.shifter.component import chain_stack

from mgear.core import applyop
from mgear.core import attribute
from mgear.core import primitive
from mgear.core import transform
from mgear.core import vector

# per segment anim params: name, type, default, min, max (v01 order)
SEGMENT_PARAMS = (
    ("damping", "double", 0.5, 0, 1),
    ("stiffness", "double", 0.5, 0, 1),
    ("gravity", "double", 0, 0, 10),
    ("gravity_directionY", "double", -1, -10, 10),
    ("useGround", "bool", 0, 0, 1),
    ("collide_softness", "double", 0, 0, 1),
)

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
        # blades computation
        self.normal = self.guide.blades["blade"].z
        self.binormal = self.guide.blades["blade"].x

        # Mirror behavior for controls
        self.mirrorBehaviour = self.settings["mirrorBehaviour"] and self.negate

        self.fk_npo = []
        self.fk_ctl = []
        self.spring_cns = []
        self.spring_aim = []
        self.spring_target = []

        # stack inputs and outputs
        self.fk_global_in = []
        self.fk_local_in = []
        self.fk_global_out = []
        self.fk_local_out = []
        self.fk_global_ref = []
        self.fk_local_ref = []

        parent = self.root
        self.previousTag = self.parentCtlTag
        chain_t = transform.getChainTransform(self.guide.apos, self.normal, self.negate)
        # local stack frame of chain_stack_01 and lite_chain_stack, which flip
        # the blade normal, so local deltas bend the same way in every chain
        stack_t = transform.getChainTransform(
            self.guide.apos, self.normal * -1, self.negate
        )
        for i, t in enumerate(chain_t):
            dist = vector.getDistance(self.guide.apos[i], self.guide.apos[i + 1])

            tnpo = self._control_matrix(t)
            ctl_dist = dist * -1 if self.mirrorBehaviour else dist

            # global and local inputs, driven by the master chains
            global_t = transform.getTransformFromPos(transform.getPositionFromMatrix(t))
            local_t = stack_t[i]
            fk_global_npo = primitive.addTransform(
                parent, self.getName("fk%s_global_npo" % i), global_t
            )
            fk_global_in = primitive.addTransform(
                fk_global_npo, self.getName("fk%s_global_in" % i), global_t
            )
            fk_local_npo = primitive.addTransform(
                fk_global_in, self.getName("fk%s_local_npo" % i), local_t
            )
            fk_local_in = primitive.addTransform(
                fk_local_npo, self.getName("fk%s_local_in" % i), local_t
            )
            self.fk_global_in.append(fk_global_in)
            self.fk_local_in.append(fk_local_in)

            # outputs, read by the slave chains
            fk_global_out_npo = primitive.addTransform(
                parent, self.getName("fk%s_global_out_npo" % i), global_t
            )
            fk_global_out = primitive.addTransform(
                fk_global_out_npo, self.getName("fk%s_global_out" % i), global_t
            )
            fk_local_out_npo = primitive.addTransform(
                parent, self.getName("fk%s_local_out_npo" % i), local_t
            )
            fk_local_out = primitive.addTransform(
                fk_local_out_npo, self.getName("fk%s_local_out" % i), local_t
            )
            self.fk_global_out.append(fk_global_out)
            self.fk_local_out.append(fk_local_out)

            fk_npo = primitive.addTransform(
                fk_local_in, self.getName("fk%s_npo" % i), tnpo
            )

            spring_aim = primitive.addTransform(
                fk_npo, self.getName("spring%s_aim" % i), tnpo
            )

            spring_cns = primitive.addTransform(
                fk_npo, self.getName("spring%s_cns" % i), tnpo
            )

            fk_ctl = self.addCtl(
                spring_cns,
                "fk%s_ctl" % i,
                tnpo,
                self.color_fk,
                "cube",
                w=ctl_dist,
                h=self.size * 0.1,
                d=self.size * 0.1,
                po=datatypes.Vector(ctl_dist * 0.5 * self.n_factor, 0, 0),
                tp=self.previousTag,
                lp=False,
            )
            self.previousTag = fk_ctl

            fk_global_ref = primitive.addTransform(
                fk_ctl, self.getName("fk%s_global_ref" % i), global_t
            )
            attribute.setKeyableAttributes(fk_global_ref, [])
            self.fk_global_ref.append(fk_global_ref)
            fk_local_ref = primitive.addTransform(
                fk_ctl, self.getName("fk%s_local_ref" % i), local_t
            )
            attribute.setKeyableAttributes(fk_local_ref, [])
            self.fk_local_ref.append(fk_local_ref)

            # the spring goal is under the stack inputs, so it follows the
            # master chains and the spring only adds the lag on top
            t_target = transform.getTransformFromPos(self.guide.apos[i + 1])
            spring_npo = primitive.addTransform(
                fk_npo, self.getName("spring%s_npo" % i), t_target
            )
            spring_target = primitive.addTransform(
                spring_npo, self.getName("spring%s" % i), t_target
            )

            parent = fk_ctl

            self.spring_cns.append(spring_cns)
            self.spring_aim.append(spring_aim)

            self.addToGroup(spring_cns, "PLOT")

            self.fk_npo.append(fk_npo)
            self.fk_ctl.append(fk_ctl)
            attribute.setKeyableAttributes(fk_ctl, self.tr_params)

            self.spring_target.append(spring_target)

        # Tweak end ------------------------------------------
        self.tweakEnd_ctl = None
        if self.settings["tweakEnd"]:
            t_end = transform.setMatrixPosition(
                self._control_matrix(chain_t[-1]), self.guide.apos[-1]
            )
            tweakEnd_npo = primitive.addTransform(
                self.fk_ctl[-1], self.getName("tweakEnd_npo"), t_end
            )
            self.tweakEnd_ctl = self.addCtl(
                tweakEnd_npo,
                "tweakEnd_ctl",
                t_end,
                self.color_ik,
                "square",
                w=self.size * 0.15,
                h=self.size * 0.15,
                d=self.size * 0.15,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=self.previousTag,
            )
            attribute.setKeyableAttributes(self.tweakEnd_ctl)

        # Chain of deformers -------------------------------
        self.loc = []
        self.extratweak_ctl = []
        # objects driving the joints, the tweak controls when they are on
        self.jnt_drivers = []
        parent = self.root
        tagP = self.previousTag
        for i, t in enumerate(chain_t):
            loc = primitive.addTransform(parent, self.getName("%s_loc" % i), t)
            self.loc.append(loc)
            parent = loc

            if self.settings["extraTweak"]:
                tweak_ctl = self.addCtl(
                    loc,
                    "extraTweak%s_ctl" % i,
                    t,
                    self.color_fk,
                    "square",
                    w=self.size * 0.08,
                    d=self.size * 0.08,
                    ro=datatypes.Vector([0, 0, 1.5708]),
                    tp=tagP,
                )
                attribute.setKeyableAttributes(tweak_ctl)
                tagP = tweak_ctl
                self.extratweak_ctl.append(tweak_ctl)
                self.jnt_drivers.append(tweak_ctl)
                self.jnt_pos.append([tweak_ctl, i, None, False])
            else:
                self.jnt_drivers.append(loc)
                self.jnt_pos.append([loc, i])

        self.end_loc = None
        if self.tweakEnd_ctl:
            t_end = transform.setMatrixPosition(chain_t[-1], self.guide.apos[-1])
            self.end_loc = primitive.addTransform(
                self.loc[-1], self.getName("end_loc"), t_end
            )
            self.jnt_drivers.append(self.end_loc)
            self.jnt_pos.append([self.end_loc, len(self.loc)])

    def _control_matrix(self, t):
        """Return the control matrix of a chain transform.

        Args:
            t (Matrix): Chain transform of a segment.

        Returns:
            Matrix: The transform, with a -1 scale for the mirror behavior.
        """
        if self.mirrorBehaviour:
            return transform.setMatrixScale(t, [-1, -1, -1])
        return t

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        # Anim -------------------------------------------
        self.aSpring_intensity = self.addAnimParam(
            "spring_intensity", "Spring chain intensity", "double", 0, 0, 1
        )
        # per segment params, in the v01 order: all segments of each param
        seg_params = []
        for name, att_type, value, min_value, max_value in SEGMENT_PARAMS:
            seg_params.append(
                [
                    self.addAnimParam(
                        "%s_%s" % (name, i),
                        "%s_%s" % (name, i),
                        att_type,
                        value,
                        min_value,
                        max_value,
                    )
                    for i in range(len(self.spring_target))
                ]
            )
        (
            self.aDamping,
            self.aStiffness,
            self.aGravity,
            self.aGravitydirectionY,
            self.ause_ground,
            self.acollide_softness,
        ) = seg_params

        self.blend_local_att = None
        if self.settings["masterChainLocal"]:
            self.blend_local_att = self.addAnimParam(
                "localBlend", "Local Blend", "double", 1, 0, 1
            )
        self.blend_world_att = None
        if self.settings["masterChainGlobal"]:
            self.blend_world_att = self.addAnimParam(
                "worldBlend", "World Blend", "double", 1, 0, 1
            )

        self.tweakVis_att = None
        if self.settings["extraTweak"]:
            self.tweakVis_att = self.addAnimParam(
                "Tweak_vis", "Tweak Vis", "bool", False
            )

        # Setup ------------------------------------------
        # twist, wide and depth stack channels, passed through to the slaves
        self.stack_in_att = []
        self.stack_out_att = []
        for channel, default in chain_stack.STACK_CHANNELS:
            self.stack_in_att.append(
                self.addSetupParam(channel + "_in", channel + "_in", "double", default)
            )
            self.stack_out_att.append(
                self.addSetupParam(
                    channel + "_out", channel + "_out", "double", default
                )
            )

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """

        # Chain of deformers -------------------------------
        for i, loc in enumerate(self.loc):
            pm.parentConstraint(self.fk_ctl[i], loc, maintainOffset=False)
        if self.end_loc:
            pm.parentConstraint(self.tweakEnd_ctl, self.end_loc, maintainOffset=False)

        # spring operators
        # Mirror behavior uses the same axis as the L side, the scale flips it
        aimAxis = "-xy" if self.negate and not self.mirrorBehaviour else "xy"
        for i, tranCns in enumerate(self.spring_aim):
            applyop.aimCns(
                tranCns,
                self.spring_target[i],
                aimAxis,
                2,
                [0, 1, 0],
                self.fk_npo[i],
                False,
            )
            ori_cns = applyop.oriCns(tranCns, self.spring_cns[i])

            springOP = applyop.gear_spring_gravity_op(self.spring_target[i])

            blend_node = pm.createNode("pairBlend")

            pm.connectAttr(ori_cns.constraintRotate, blend_node.inRotate2)
            pm.connectAttr(self.aSpring_intensity, blend_node.weight)

            pm.disconnectAttr(ori_cns.constraintRotate, self.spring_cns[i].rotate)

            pm.connectAttr(blend_node.outRotate, self.spring_cns[i].rotate)

            pm.connectAttr(self.aSpring_intensity, springOP + ".intensity")
            pm.connectAttr(self.aDamping[i], springOP + ".damping")
            pm.connectAttr(self.aStiffness[i], springOP + ".stiffness")
            pm.connectAttr(self.aGravity[i], springOP + ".gravity")
            pm.connectAttr(self.ause_ground[i], springOP + ".use_ground")
            pm.connectAttr(self.acollide_softness[i], springOP + ".collide_softness")
            pm.connectAttr(self.aGravitydirectionY[i], springOP + ".gravity_directionY")

        # Stack outputs ------------------------------------
        # the refs follow the controls in the stack frames
        for refs, outs in (
            (self.fk_local_ref, self.fk_local_out),
            (self.fk_global_ref, self.fk_global_out),
        ):
            for ref, out in zip(refs, outs):
                applyop.gear_mulmatrix_op(
                    ref.attr("worldMatrix"),
                    out.attr("parentInverseMatrix[0]"),
                    out,
                )

        for in_att, out_att in zip(self.stack_in_att, self.stack_out_att):
            pm.connectAttr(in_att, out_att)

        # Stack inputs -------------------------------------
        mstr_local = self.settings["masterChainLocal"]
        mstr_global = self.settings["masterChainGlobal"]
        mstr_local = self.rig.components[mstr_local] if mstr_local else None
        mstr_global = self.rig.components[mstr_global] if mstr_global else None
        offset = self.settings["cnxOffset"]
        for master, out_name, slave_in, blend_att in (
            (mstr_global, "fk_global_out", self.fk_global_in, self.blend_world_att),
            (mstr_local, "fk_local_out", self.fk_local_in, self.blend_local_att),
        ):
            if not master:
                continue
            master_out = getattr(master, out_name)
            for i in range(len(self.fk_ctl)):
                chain_stack.connect_master(master_out, slave_in, i, offset, blend_att)

        # the local master passes its channels first, as it drives the shape
        master = mstr_local or mstr_global
        if master:
            chain_stack.connect_stack_channels(master.root, self.root)

        # Visibility ---------------------------------------
        for tweak_ctl in self.extratweak_ctl:
            for shp in tweak_ctl.getShapes():
                pm.connectAttr(self.tweakVis_att, shp.attr("visibility"))

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        seg_count = len(self.loc)
        self.relatives["root"] = self.jnt_drivers[0]
        self.controlRelatives["root"] = self.fk_ctl[0]
        self.jointRelatives["root"] = 0
        for i in range(seg_count - 1):
            self.relatives["%s_loc" % i] = self.jnt_drivers[i + 1]
            self.controlRelatives["%s_loc" % i] = self.fk_ctl[i + 1]
            self.jointRelatives["%s_loc" % i] = i + 1

        # the tip locator maps to the tweak end, or to the last segment
        tip = "%s_loc" % (seg_count - 1)
        if self.tweakEnd_ctl:
            self.relatives[tip] = self.end_loc
            self.controlRelatives[tip] = self.tweakEnd_ctl
            self.jointRelatives[tip] = seg_count
        else:
            self.relatives[tip] = self.jnt_drivers[-1]
            self.controlRelatives[tip] = self.fk_ctl[-1]
            self.jointRelatives[tip] = seg_count - 1
