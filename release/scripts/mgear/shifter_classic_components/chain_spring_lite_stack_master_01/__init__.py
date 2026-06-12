"""Component Chain Spring 01 module"""

import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter import component

from mgear.core import applyop, vector, node
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

        # blades computation
        self.normal = self.guide.blades["blade"].z
        self.binormal = self.guide.blades["blade"].x

        self.fk_npo = []
        self.fk_ctl = []
        self.spring_cns = []
        self.spring_aim = []
        self.spring_lvl = []
        self.spring_ref = []
        self.spring_npo = []
        self.spring_target = []

        self.fk_local_out = []
        self.fk_global_out = []
        self.fk_global_ref = []

        parent = self.root
        self.previousTag = self.parentCtlTag
        for i, t in enumerate(transform.getChainTransform(self.guide.apos,
                                                          self.normal,
                                                          self.negate)):
            dist = vector.getDistance(self.guide.apos[i],
                                      self.guide.apos[i + 1])

            # output
            global_t = transform.setMatrixPosition(
                datatypes.Matrix(),
                transform.getPositionFromMatrix(t))
            fk_global_out_npo = primitive.addTransform(
                parent, self.getName("fk%s_global_out_npo" % i), global_t)
            fk_global_out = primitive.addTransform(
                fk_global_out_npo,
                self.getName("fk%s_global_out" % i),
                global_t)
            self.fk_global_out.append(fk_global_out)

            fk_local_out_npo = primitive.addTransform(
                parent, self.getName("fk%s_local_out_npo" % i), t)
            fk_local_out = primitive.addTransform(
                fk_local_out_npo, self.getName("fk%s_local_out" % i), t)
            self.fk_local_out.append(fk_local_out)

            fk_npo = primitive.addTransform(parent,
                                            self.getName("fk%s_npo" % i), t)

            spring_aim = primitive.addTransform(
                fk_npo,
                self.getName("spring%s_aim" % i), t)

            spring_cns = primitive.addTransform(
                fk_npo,
                self.getName("spring%s_cns" % i), t)

            fk_ctl = self.addCtl(
                spring_cns,
                "fk%s_ctl" % i,
                t,
                self.color_fk,
                "cube", w=dist,
                h=self.size * .1,
                d=self.size * .1,
                po=datatypes.Vector(dist * .5 * self.n_factor, 0, 0),
                tp=self.previousTag,
                lp=False)

            self.previousTag = fk_ctl

            t = transform.getTransformFromPos(self.guide.apos[i + 1])
            spring_npo = primitive.addTransform(
                parent, self.getName("spring%s_npo" % i), t)
            spring_target = primitive.addTransform(
                spring_npo, self.getName("spring%s" % i), t)

            parent = fk_ctl

            self.spring_cns.append(spring_cns)
            self.spring_aim.append(spring_aim)

            self.addToGroup(spring_cns, "PLOT")

            self.fk_npo.append(fk_npo)
            self.fk_ctl.append(fk_ctl)
            attribute.setKeyableAttributes(self.fk_ctl, self.tr_params)

            self.spring_target.append(spring_target)

            # fk global ref
            fk_global_ref = primitive.addTransform(
                fk_ctl,
                self.getName("fk%s_global_ref" % i),
                global_t)
            self.fk_global_ref.append(fk_global_ref)
            attribute.setKeyableAttributes(fk_global_ref, [])

        # Chain of deformers -------------------------------
        self.loc = []
        parent = self.root
        for i, t in enumerate(transform.getChainTransform(self.guide.apos,
                                                          self.normal,
                                                          self.negate)):
            loc = primitive.addTransform(parent, self.getName("%s_loc" % i), t)

            self.loc.append(loc)
            self.jnt_pos.append([loc, i])
            parent = loc

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        # Anim -------------------------------------------
        self.aDamping = []
        self.aStiffness = []
        self.aSpring_intensity = self.addAnimParam("spring_intensity",
                                                   "Spring chain intensity",
                                                   "double",
                                                   0,
                                                   0,
                                                   1)
        for i, tar in enumerate(self.spring_target):
            aDamping = self.addAnimParam("damping_%s" % i,
                                         "damping_%s" % i,
                                         "double",
                                         0.5,
                                         0,
                                         1)
            self.aDamping.append(aDamping)

        for i, tar in enumerate(self.spring_target):

            aStiffness = self.addAnimParam(
                "stiffness_%s" % i, "stiffness_%s" % i, "double", 0.5, 0, 1)

            self.aStiffness.append(aStiffness)

        #######################
        # setup Parameters
        #######################
        self.mid_twist_in_att = self.addSetupParam("mid_twist_in",
                                                   "mid_twist_in",
                                                   "double",
                                                   0)

        self.tip_twist_in_att = self.addSetupParam("tip_twist_in",
                                                   "tip_twist_in",
                                                   "double",
                                                   0)

        # wide is Y
        self.mid_wide_in_att = self.addSetupParam("mid_wide_in",
                                                  "mid_wide_in",
                                                  "double",
                                                  1)

        self.tip_wide_in_att = self.addSetupParam("tip_wide_in",
                                                  "tip_wide_in",
                                                  "double",
                                                  1)

        # depth is Z
        self.mid_depth_in_att = self.addSetupParam("mid_depth_in",
                                                   "mid_depth_in",
                                                   "double",
                                                   1)

        self.tip_depth_in_att = self.addSetupParam("tip_depth_in",
                                                   "tip_depth_in",
                                                   "double",
                                                   1)
        # OUT channels
        self.mid_twist_out_att = self.addSetupParam("mid_twist_out",
                                                    "mid_twist_out",
                                                    "double",
                                                    0)

        self.tip_twist_out_att = self.addSetupParam("tip_twist_out",
                                                    "tip_twist_out",
                                                    "double",
                                                    0)

        # wide is Y
        self.mid_wide_out_att = self.addSetupParam("mid_wide_out",
                                                   "mid_wide_out",
                                                   "double",
                                                   1)

        self.tip_wide_out_att = self.addSetupParam("tip_wide_out",
                                                   "tip_wide_out",
                                                   "double",
                                                   1)

        # depth is Z
        self.mid_depth_out_att = self.addSetupParam("mid_depth_out",
                                                    "mid_depth_out",
                                                    "double",
                                                    1)

        self.tip_depth_out_att = self.addSetupParam("tip_depth_out",
                                                    "tip_depth_out",
                                                    "double",
                                                    1)

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

        # spring operators
        # settings aim contraints
        for i, tranCns in enumerate(self.spring_aim):
            if self.negate:
                aimAxis = "-xy"
            else:
                aimAxis = "xy"
            applyop.aimCns(tranCns,
                           self.spring_target[i],
                           aimAxis,
                           2,
                           [0, 1, 0],
                           self.fk_npo[i],
                           False)
            ori_cns = applyop.oriCns(tranCns, self.spring_cns[i])

            springOP = applyop.gear_spring_op(self.spring_target[i])

            blend_node = pm.createNode("pairBlend")

            pm.connectAttr(ori_cns.constraintRotate, blend_node.inRotate2)
            pm.connectAttr(self.aSpring_intensity, blend_node.weight)

            pm.disconnectAttr(ori_cns.constraintRotate,
                              self.spring_cns[i].rotate)

            pm.connectAttr(blend_node.outRotateX, self.spring_cns[i].rotateX)
            pm.connectAttr(blend_node.outRotateY, self.spring_cns[i].rotateY)
            pm.connectAttr(blend_node.outRotateZ, self.spring_cns[i].rotateZ)

            pm.connectAttr(self.aSpring_intensity, springOP + ".intensity")
            pm.connectAttr(self.aDamping[i], springOP + ".damping")
            pm.connectAttr(self.aStiffness[i], springOP + ".stiffness")

            # connect out
            ctl = self.fk_ctl[i]
            out_loc = self.fk_local_out[i]
            applyop.gear_mulmatrix_op(ctl.attr("worldMatrix"),
                                      out_loc.attr("parentInverseMatrix[0]"),
                                      out_loc)

            out_glob = self.fk_global_out[i]
            out_ref = self.fk_global_ref[i]
            applyop.gear_mulmatrix_op(out_ref.attr("worldMatrix"),
                                      out_glob.attr("parentInverseMatrix[0]"),
                                      out_glob)

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""

        self.relatives["root"] = self.loc[0]
        self.controlRelatives["root"] = self.fk_ctl[0]
        self.jointRelatives["root"] = 0
        for i in range(0, len(self.loc) - 1):
            self.relatives["%s_loc" % i] = self.loc[i + 1]
            self.controlRelatives["%s_loc" % i] = self.fk_ctl[i + 1]
            self.jointRelatives["%s_loc" % i] = i + 1
        self.relatives["%s_loc" % (len(self.loc) - 1)] = self.loc[-1]
        self.controlRelatives["%s_loc" % (len(self.loc) - 1)] = self.fk_ctl[-1]
        self.jointRelatives["%s_loc" % (len(self.loc) - 1)] = len(self.loc) - 1
