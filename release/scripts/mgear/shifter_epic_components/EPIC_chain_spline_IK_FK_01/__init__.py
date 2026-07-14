"""Component Chain 01 module"""

import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import node, applyop, vector
from mgear.core import attribute, transform, primitive, curve

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

        self.isFk = self.settings["mode"] != 1
        self.isIk = self.settings["mode"] != 0
        self.isFkIk = self.settings["mode"] == 2

        self.WIP = self.options["mode"]

        # FK controllers ------------------------------------
        if self.isFk:
            self.fk_npo = []
            self.fk_ctl = []
            self.fk_ref = []
            self.fk_off = []
            t = self.guide.tra["root"]
            self.fk_cns = primitive.addTransform(
                self.root, self.getName("fk_cns"), t)
            parent = self.fk_cns
            tOld = False
            fk_ctl = None
            self.previusTag = self.parentCtlTag
            for i, t in enumerate(transform.getChainTransform(self.guide.apos,
                                                              self.normal,
                                                              self.negate)):
                dist = vector.getDistance(self.guide.apos[i],
                                          self.guide.apos[i + 1])
                if self.settings["neutralpose"] or not tOld:
                    tnpo = t
                else:
                    tnpo = transform.setMatrixPosition(
                        tOld,
                        transform.getPositionFromMatrix(t))
                if i:
                    tref = transform.setMatrixPosition(
                        tOld,
                        transform.getPositionFromMatrix(t))
                    fk_ref = primitive.addTransform(
                        fk_ctl,
                        self.getName("fk%s_ref" % i),
                        tref)
                    self.fk_ref.append(fk_ref)
                else:
                    tref = t
                fk_off = primitive.addTransform(
                    parent, self.getName("fk%s_off" % i), tref)
                fk_npo = primitive.addTransform(
                    fk_off, self.getName("fk%s_npo" % i), tnpo)
                fk_ctl = self.addCtl(
                    fk_npo,
                    "fk%s_ctl" % i,
                    t,
                    self.color_fk,
                    "cube",
                    w=dist,
                    h=self.size * .1,
                    d=self.size * .1,
                    po=datatypes.Vector(dist * .5 * self.n_factor, 0, 0),
                    tp=self.previusTag)

                self.fk_off.append(fk_off)
                self.fk_npo.append(fk_npo)
                self.fk_ctl.append(fk_ctl)
                tOld = t
                self.previusTag = fk_ctl

        # IK controllers ------------------------------------
        if self.isIk:

            normal = vector.getTransposedVector(
                self.normal,
                [self.guide.apos[0], self.guide.apos[1]],
                [self.guide.apos[-2], self.guide.apos[-1]])
            t = transform.getTransformLookingAt(self.guide.apos[-2],
                                                self.guide.apos[-1],
                                                normal,
                                                "xy",
                                                self.negate)
            t = transform.setMatrixPosition(t, self.guide.apos[-1])

            self.ik_cns = primitive.addTransform(self.root,
                                                 self.getName("ik_cns"),
                                                 t)
            # Plain structural group (not a control) - just organizes the
            # spline IK internals under ik_cns, not meant to be animated.
            self.ikcns_grp = primitive.addTransform(
                self.ik_cns, self.getName("ikcns_grp"), t)

            # Spline IK curves -----------------------------------
            # The curve that actually drives the ikSplineSolver is built
            # directly through every guide position (one CV per guide
            # locator) as a degree-1 (linear) curve. Degree matters here:
            # a degree-3 curve treats these positions as B-spline control
            # vertices, which the curve does NOT pass through except at
            # the two ends - only a polyline (degree 1) is guaranteed to
            # retrace every guide point exactly, matching the discrete
            # per-segment look-at orientation add2DChain/getChainTransform
            # already used to build the FK chain and self.chain.
            ik_nb = self.settings["ikNb"]
            self.ik_crv = curve.addCurve(
                self.ikcns_grp, self.getName("ik_crv"),
                [list(p) for p in self.guide.apos],
                False, 1)
            self.ik_crv.attr("visibility").set(False)

            # Compute good rest CV positions for an ikNb-CV curve by
            # rebuilding a throwaway duplicate of the dense curve (this
            # only needs to exist long enough to read its CVs - the real
            # wrap curve is built fresh below).
            wrap_degree = min(3, ik_nb - 1)
            tmp_wrap_crv = pm.duplicate(
                self.ik_crv, n=self.getName("ikWrapTmp_crv"))[0]
            pm.rebuildCurve(
                tmp_wrap_crv,
                ch=False,
                replaceOriginal=True,
                rebuildType=0,
                keepRange=0,
                keepControlPoints=False,
                keepEndPoints=True,
                keepTangents=True,
                spans=(ik_nb - wrap_degree),
                degree=wrap_degree,
                tolerance=0.001)

            # IK controls, evenly spaced by arc length along the chain --
            # (independent of the wrap curve's CVs, which are wherever
            # rebuildCurve put them, not necessarily evenly spaced).
            ik_positions = curve.get_uniform_world_positions_on_curve(
                self.ik_crv, ik_nb)
            ik_transforms = transform.getChainTransform(
                ik_positions, self.normal, self.negate)
            ik_transforms.append(transform.setMatrixPosition(
                ik_transforms[-1], ik_positions[-1]))

            wrap_shape = tmp_wrap_crv.getShape()
            cv_rest_positions = []
            for i in range(ik_nb):
                pos = pm.xform("{}.cv[{}]".format(wrap_shape, i),
                               q=True, ws=True, t=True)
                # Guard against whatever pm.xform hands back here (tuple,
                # extra/odd-typed elements, etc.) so datatypes.Vector always
                # gets exactly 3 plain floats.
                cv_rest_positions.append(
                    [float(pos[0]), float(pos[1]), float(pos[2])])
            pm.delete(tmp_wrap_crv)

            # Guard against duplicate/rebuildCurve flipping the curve's
            # parametric direction. If Maya's CV[0] actually landed near
            # the tip instead of the root, every control needs to bind to
            # the OPPOSITE CV index than a naive 1:1 mapping would assume -
            # otherwise the last (tip) control ends up wired to the CV
            # nearest the root (which barely needs to move), while the CV
            # that should follow the tip stays wired to the first control
            # instead. Check empirically which way it goes, and remap the
            # control->CV-index correspondence accordingly (NOT just the
            # rest-position list - the correspondence used when wiring
            # gear_curvecns_op must match too).
            cv0_v = datatypes.Vector(*cv_rest_positions[0])
            root_v = datatypes.Vector(
                ik_positions[0].x, ik_positions[0].y, ik_positions[0].z)
            tip_v = datatypes.Vector(
                ik_positions[-1].x, ik_positions[-1].y, ik_positions[-1].z)
            first_to_root = (cv0_v - root_v).length()
            first_to_tip = (cv0_v - tip_v).length()
            cvs_reversed = first_to_tip < first_to_root

            self.ik_ctl = []
            self.ik_npo = []
            cv_drivers = [None] * ik_nb
            self.previusTag = self.parentCtlTag
            for i, ik_t in enumerate(ik_transforms):
                ik_npo = primitive.addTransform(
                    self.ikcns_grp, self.getName("ik%s_npo" % i), ik_t)
                self.ik_npo.append(ik_npo)

                ik_ctl = self.addCtl(
                    ik_npo,
                    "ik%s_ctl" % i,
                    ik_t,
                    self.color_ik,
                    "cube",
                    w=self.size * .15,
                    h=self.size * .15,
                    d=self.size * .15,
                    tp=self.previusTag)

                # IK controls only position the spline curve; axial twist is
                # driven by the dedicated "twist" attribute, so expose
                # translate only.
                attribute.setKeyableAttributes(ik_ctl, self.t_params)

                self.ik_ctl.append(ik_ctl)
                self.previusTag = ik_ctl

                # Driver for this CV: parented under the control but
                # positioned at the wrap curve's rebuilt rest CV location,
                # so the constant offset between an evenly-spaced control
                # and its (not evenly-spaced) CV is baked in via ordinary
                # DAG parenting - not a skinCluster/wire bind-pose cache.
                # A skinCluster's bindPreMatrix is captured once and can
                # go stale relative to a component's final position once
                # it's parented deep in a character hierarchy, which is
                # what was actually causing the double transformation
                # (disabling inheritsTransform doesn't touch a deformer's
                # internal bind-pose cache, which is why that didn't fix
                # it here). A live, ordinary matrix connection has no such
                # cache to go stale.
                #
                # The first/last controls are a special case: arc-length
                # sampling already puts them exactly at guide.apos[0]/[-1]
                # - the same positions as the real chain's first/last
                # joints - so their drivers use that exact position
                # directly instead of the rebuilt curve's approximation
                # (which only exists to make interior CVs approximate the
                # guide shape; the endpoints don't need approximating).
                cv_index = (ik_nb - 1 - i) if cvs_reversed else i
                if i == 0:
                    cv_pos = self.guide.apos[0]
                elif i == len(ik_transforms) - 1:
                    cv_pos = self.guide.apos[-1]
                else:
                    cv_pos = datatypes.Vector(*cv_rest_positions[cv_index])
                cv_m = transform.setMatrixPosition(ik_t, cv_pos)
                cv_driver = primitive.addTransform(
                    ik_ctl, self.getName("ikCvDriver%s" % i), cv_m)
                cv_drivers[cv_index] = cv_driver

            # The real wrap curve, built FRESH (never touched by
            # rebuildCurve) and immediately bound to the CV drivers via
            # curve.addCnsCurve - the exact same helper (and pattern:
            # fresh curve + immediate gear_curvecns_op) mgear uses
            # everywhere else for "curve driven by N controls". Applying
            # gear_curvecns_op to a curve that had already been through
            # duplicate+rebuildCurve first (the previous approach) isn't
            # a pattern used anywhere else in mgear and was the likely
            # reason the last CV wasn't responding correctly.
            self.ik_wrap_crv = curve.addCnsCurve(
                self.ikcns_grp, self.getName("ikWrap_crv"),
                cv_drivers, wrap_degree)
            self.ik_wrap_crv.attr("visibility").set(False)

            # Twist reference transforms for the ikSplineSolver's advanced
            # twist (wired in addOperators). These must be oriented to
            # match self.chain's own start/end bind tangent exactly, NOT
            # ik_ctl[0]/[-1]'s own orientation - the ikNb controls are
            # sampled independently from the dense per-joint chain, so
            # their tangent generally differs from self.chain[0]/[-1]'s
            # actual orientation. Feeding that mismatched orientation
            # straight into dWorldUpMatrix biased the twist calculation,
            # which is what caused the extra rotation on the first joint
            # once this component was parented under another (its own
            # world orientation no longer canceled the mismatch out).
            # Building these under ik_ctl[0]/[-1] keeps a baked, zero-error
            # offset at rest while still following control rotation.
            dense_transforms = transform.getChainTransform(
                self.guide.apos, self.normal, self.negate)
            dense_transforms.append(transform.setMatrixPosition(
                dense_transforms[-1], self.guide.apos[-1]))

            # Parented under the (static) ik_npo, NOT the IK controls, so the
            # solver's base twist is independent of user twist. All user twist
            # is driven explicitly by the per-control "twist" attribute layer
            # (see addOperators), which avoids double-counting at the ends.
            self.ik_twist_start_ref = primitive.addTransform(
                self.ik_npo[0], self.getName("ikTwistStart_ref"),
                dense_transforms[0])
            self.ik_twist_end_ref = primitive.addTransform(
                self.ik_npo[-1], self.getName("ikTwistEnd_ref"),
                dense_transforms[-1])

            # A wire deformer relays the wrap curve's shape onto the dense
            # curve. Since the wrap curve hasn't moved from its rebuilt
            # rest shape yet, the wire's base shape == current shape, so
            # this contributes zero deformation at rest.
            ik_wire = pm.wire(
                self.ik_crv,
                w=self.ik_wrap_crv,
                n=self.getName("ikWire"),
                groupWithBase=False,
                envelope=1.0)[0]

            # Without an explicit dropoff distance, Maya's default falls
            # short of the curve's full length, so influence (and control)
            # quietly cuts off before reaching the tip. Base it on the
            # curve's own length so it scales correctly with chain size.
            dense_length = pm.arclen(self.ik_crv)
            pm.setAttr(
                "{}.dropoffDistance[0]".format(ik_wire),
                dense_length * 10)

            # Chain (real joints, driven by the spline ikHandle in
            # addOperators). Kept identical to the previous rotate-plane
            # setup so translation always stays on the chain's local X
            # (bone) axis only.
            self.chain = primitive.add2DChain(self.root,
                                              self.getName("chain"),
                                              self.guide.apos,
                                              self.normal,
                                              self.negate)
            self.chain[0].attr("visibility").set(self.WIP)

            # Twist layer: a twist_ref leaf under each chain joint. The IK
            # deform target is this node (not the raw chain joint), so its
            # rotateX - driven per IK control in addOperators - adds axial
            # twist on top of the solver's curve-following, without moving the
            # bone off its primary axis.
            self.twist_ref = []
            for i, jnt in enumerate(self.chain):
                twist_ref = primitive.addTransform(
                    jnt, self.getName("%s_twist_ref" % i),
                    transform.getTransform(jnt))
                self.twist_ref.append(twist_ref)

        # Chain of deformers -------------------------------
        self.loc = []
        parent = self.root
        for i, t in enumerate(transform.getChainTransform(self.guide.apos,
                                                          self.normal,
                                                          self.negate)):
            loc = primitive.addTransform(parent, self.getName("%s_loc" % i), t)

            self.loc.append(loc)
            # self.jnt_pos.append([loc, i, None, False])

            jnt_name = "_".join([self.name, str(i + 1).zfill(2)])
            if i:
                guide_relative_name = "{}_loc".format(str(i - 1))
            else:
                guide_relative_name = "root"
            self.jnt_pos.append(
                {
                    "obj": loc,
                    "name": jnt_name,
                    "guide_relative": guide_relative_name,
                }
            )

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        # Anim -------------------------------------------
        if self.isFkIk:
            self.blend_att = self.addAnimParam(
                "blend", "Fk/Ik Blend", "double", self.settings["blend"], 0, 1)

        if self.isIk:
            self.roll_att = self.addAnimParam(
                "roll", "Roll", "double", 0, -180, 180)

            self.stretch_att = self.addAnimParam(
                "stretch", "Stretch", "double", 1, 0, 1)

            # A single "twist" handle on every IK control. Twisting one
            # control twists the chain joints nearest it, reaching zero at the
            # neighbouring controls (width = "twistFalloff") - so the first
            # control twists the base, the last the tip, an interior control
            # the middle, each without disturbing the far ends. Wired to the
            # twist_ref layer in addOperators (NOT the ikHandle, which would
            # give an end-weighted ramp).
            self.ik_twist_att = [
                self.addAnimParam(
                    "twist", "Twist", "double", 0, -360, 360, uihost=ctl)
                for ctl in self.ik_ctl]

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

        # Visibilities -------------------------------------
        if self.isFkIk:
            # fk
            fkvis_node = node.createReverseNode(self.blend_att)

            for fk_ctl in self.fk_ctl:
                for shp in fk_ctl.getShapes():
                    pm.connectAttr(fkvis_node + ".outputX",
                                   shp.attr("visibility"))

            # ik
            for ik_ctl in self.ik_ctl:
                for shp in ik_ctl.getShapes():
                    pm.connectAttr(self.blend_att, shp.attr("visibility"))

        # FK Chain -----------------------------------------
        if self.isFk:
            for off, ref in zip(self.fk_off[1:], self.fk_ref):
                applyop.gear_mulmatrix_op(
                    ref.worldMatrix, off.parentInverseMatrix, off, "rt")
        # IK Chain -----------------------------------------
        if self.isIk:
            # Real ikSplineSolver handle riding the control-driven curve.
            # Using a real joint chain + native spline solver (instead of
            # a motion-path/matrix-decompose rig) guarantees translation
            # never leaves the chain's local X (bone) axis.
            ikh_name = pm.ikHandle(
                n=self.getName("ikh"),
                sj=self.chain[0],
                ee=self.chain[-1],
                sol="ikSplineSolver",
                ccv=False,
                curve=self.ik_crv)[0]
            self.ikh = pm.PyNode(ikh_name)
            self.root.addChild(self.ikh)
            self.ikh.attr("visibility").set(False)

            # Roll
            pm.connectAttr(self.roll_att, self.ikh.attr("roll"))

            # Twist is handled per IK control by the twist_ref layer below,
            # not the ikHandle (which would give an end-weighted ramp).

            # Advanced twist - first/last IK control orientation drives
            # the twist along the length of the chain. Same dWorldUpType/
            # dWorldUpAxis convention as mgear's own EPIC_arm_02/leg_02
            # (also X-forward, Z-up "xz" chains).
            self.ikh.attr("dTwistControlEnable").set(True)
            self.ikh.attr("dWorldUpType").set(4)  # Object Rotation Up (Start/End)
            self.ikh.attr("dWorldUpAxis").set(3)
            self.ikh.attr("dWorldUpVectorZ").set(1.0)
            self.ikh.attr("dWorldUpVectorY").set(0.0)
            self.ikh.attr("dWorldUpVectorEndZ").set(1.0)
            self.ikh.attr("dWorldUpVectorEndY").set(0.0)
            if self.negate:
                self.ikh.attr("dForwardAxis").set(1)

            pm.connectAttr(self.ik_twist_start_ref.attr("worldMatrix"),
                           self.ikh.attr("dWorldUpMatrix"))
            pm.connectAttr(self.ik_twist_end_ref.attr("worldMatrix"),
                           self.ikh.attr("dWorldUpMatrixEnd"))

            # Stretch - single axis only (chain's local X/bone length),
            # scaled uniformly by the live curve-length ratio.
            curve_info = pm.arclen(self.ik_crv, ch=True)
            rest_length = curve_info.attr("arcLength").get()
            ratio_node = node.createDivNode(
                curve_info.attr("arcLength"), rest_length)
            stretch_blend = node.createBlendNode(
                ratio_node + ".outputX", 1.0, self.stretch_att)

            for jnt in self.chain[1:]:
                rest_tx = jnt.attr("tx").get()
                node.createMulNode(
                    stretch_blend + ".outputR", rest_tx, jnt.attr("tx"))

            # Per-control twist distribution ----------------------------
            # Each chain joint's twist_ref.rx is a sum of every IK control's
            # "twist" attribute weighted by an eased TENT (hat) falloff: a
            # control's influence is 1 at its own position and drops to
            # exactly 0 at its neighbouring controls (radius = twistFalloff x
            # control spacing). So the middle control twists only the middle
            # and reaches zero at the base and tip controls - the ends do NOT
            # move. The weights are additive, and at twistFalloff = 1 they sum
            # to 1, so an equal twist on all controls gives a uniform roll.
            M = len(self.ik_ctl)
            N = len(self.chain)
            falloff = max(self.settings["twistFalloff"], 1e-4)
            p_ctl = [i / float(M - 1) for i in range(M)] if M > 1 else [0.0]
            spacing = 1.0 / (M - 1) if M > 1 else 1.0
            radius = falloff * spacing

            for j in range(N):
                p_j = j / float(N - 1) if N > 1 else 0.0

                if M == 1:
                    pm.connectAttr(self.ik_twist_att[0],
                                   self.twist_ref[j].attr("rx"))
                    continue

                pma = pm.createNode(
                    "plusMinusAverage", n=self.getName("twist%s_pma" % j))
                pma.attr("operation").set(1)  # sum
                idx = 0
                for i in range(M):
                    d = abs(p_j - p_ctl[i])
                    if d >= radius:
                        continue
                    t = d / radius
                    # eased tent: 1 at the control, 0 at the neighbour control
                    w = 1.0 - (3.0 * t * t - 2.0 * t * t * t)
                    if w < 0.001:
                        continue
                    mul = node.createMulNode(self.ik_twist_att[i], w)
                    pm.connectAttr(mul + ".outputX",
                                   pma.attr("input1D[%d]" % idx))
                    idx += 1

                pm.connectAttr(pma.attr("output1D"),
                               self.twist_ref[j].attr("rx"))

        # Chain of deformers -------------------------------
        for i, loc in enumerate(self.loc):

            if self.settings["mode"] == 0:  # fk only
                pm.parentConstraint(self.fk_ctl[i], loc, maintainOffset=False)
                pm.connectAttr(self.fk_ctl[i] + ".scale", loc + ".scale")

            elif self.settings["mode"] == 1:  # ik only
                pm.parentConstraint(
                    self.twist_ref[i], loc, maintainOffset=False)

            elif self.settings["mode"] == 2:  # fk/ik

                rev_node = node.createReverseNode(self.blend_att)

                # orientation
                cns = pm.parentConstraint(
                    self.fk_ctl[i], self.twist_ref[i], loc,
                    maintainOffset=False)
                cns.interpType.set(0)
                weight_att = pm.parentConstraint(
                    cns, query=True, weightAliasList=True)
                pm.connectAttr(rev_node + ".outputX", cns + "." + weight_att[0])
                pm.connectAttr(self.blend_att, cns + "." + weight_att[1])

                # scaling
                blend_node = pm.createNode("blendColors")
                pm.connectAttr(self.chain[i].attr("scale"),
                               blend_node + ".color1")
                pm.connectAttr(self.fk_ctl[i].attr("scale"),
                               blend_node + ".color2")
                pm.connectAttr(self.blend_att, blend_node + ".blender")
                pm.connectAttr(blend_node + ".output", loc + ".scale")

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""

        self.relatives["root"] = self.loc[0]
        self.jointRelatives["root"] = 0

        if not self.isIk:
            self.controlRelatives["root"] = self.fk_ctl[0]
            self.controlRelatives["%s_loc" % (len(self.loc) - 1)] = self.fk_ctl[-1]
        else:
            self.controlRelatives["root"] = self.ik_ctl[0]
            self.controlRelatives["%s_loc" % (len(self.loc) - 1)] = self.ik_ctl[-1]

        for i in range(0, len(self.loc) - 1):
            self.relatives["%s_loc" % i] = self.loc[i + 1]
            self.jointRelatives["%s_loc" % i] = i + 1
            self.aliasRelatives["%s_ctl" % i] = i + 1
            if not self.isIk:
                self.controlRelatives["%s_loc" % i] = self.fk_ctl[i + 1]
            else:
                # proportionally map each deformer division to the
                # nearest IK control (counts are independent: ikNb vs
                # number of guide locators).
                ik_idx = min(
                    int(round((i + 1) * (len(self.ik_ctl) - 1) /
                              float(len(self.loc) - 1))),
                    len(self.ik_ctl) - 1)
                self.controlRelatives["%s_loc" % i] = self.ik_ctl[ik_idx]

        self.relatives["%s_loc" % (len(self.loc) - 1)] = self.loc[-1]
        self.jointRelatives["%s_loc" % (len(self.loc) - 1)] = len(self.loc) - 1
        self.aliasRelatives["%s_loc" % (len(self.loc) - 1)] = len(self.loc) - 1

    # @param self
    def addConnection(self):
        """Add more connection definition to the set"""

        self.connections["standard"] = self.connect_standard
        self.connections["orientation"] = self.connect_orientation
        self.connections["parent"] = self.connect_parent

    def connect_orientation(self):
        """orientation connection definition for the component"""
        self.connect_orientCns()

    def connect_standard(self):
        """standard connection definition for the component"""
        self.connect_standardWithSimpleIkRef()

    def connect_parent(self):
        self.connect_standardWithSimpleIkRef()
