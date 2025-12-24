"""
Shifter component rig class.
"""

#############################################
# GLOBAL
#############################################
import re

# Maya
from maya import cmds

# pymaya
import mgear.pymaya as pm
from mgear.pymaya import datatypes
from mgear.pymaya import versions

# mgear
import mgear
from mgear.core import primitive, vector, transform, curve
from mgear.core import attribute, applyop, node, icon

from mgear.shifter import naming

#############################################
# COMPONENT
#############################################


class Main(object):
    """Main component class

    Attributes:
        rig (Rig): The parent Rig of this component.
        guide (ComponentGuide): The guide for this component.

    """

    steps = [
        "Objects",
        "Properties",
        "Operators",
        "Connect",
        "Joints",
        "Finalize",
    ]

    local_params = ("tx", "ty", "tz", "rx", "ry", "rz", "ro", "sx", "sy", "sz")
    t_params = ("tx", "ty", "tz")
    r_params = ("rx", "ry", "rz", "ro")
    s_params = ("sx", "sy", "sz")
    tr_params = ("tx", "ty", "tz", "rx", "ry", "rz", "ro")
    rs_params = ("rx", "ry", "rz", "ro", "sx", "sy", "sz")
    x_axis = datatypes.Vector(1, 0, 0)
    y_axis = datatypes.Vector(0, 1, 0)
    z_axis = datatypes.Vector(0, 0, 1)

    def __init__(self, rig, guide):

        # --------------------------------------------------
        # Main Objects
        self.rig = rig
        self.guide = guide

        self.options = self.rig.options
        self.model = self.rig.model
        self.settings = self.guide.values
        self.setupWS = self.rig.setupWS

        self.WIP = self.options["mode"]

        self.name = self.settings["comp_name"]
        self.side = self.settings["comp_side"]
        self.index = self.settings["comp_index"]

        # Init relative ref mapping for custom IK spaces
        self.relatives_map_upv = {}
        self.relatives_map = {}

        # --------------------------------------------------
        # Shortcut to useful settings
        self.size = self.guide.size

        if self.settings["Override_Color"]:
            if self.settings["Use_RGB_Color"]:
                self.color_fk = self.settings["RGB_fk"]
                self.color_ik = self.settings["RGB_ik"]
            else:
                self.color_fk = self.settings["color_fk"]
                self.color_ik = self.settings["color_ik"]
        else:
            if self.options["Use_RGB_Color"]:
                self.color_fk = self.options[self.side + "_RGB_fk"]
                self.color_ik = self.options[self.side + "_RGB_ik"]
            else:
                self.color_fk = self.options[self.side + "_color_fk"]
                self.color_ik = self.options[self.side + "_color_ik"]

        self.negate = self.side == "R"
        if self.negate:
            self.n_sign = "-"
            self.n_factor = -1
        else:
            self.n_sign = ""
            self.n_factor = 1

        # --------------------------------------------------
        # Builder init
        self.groups = {}  # Dictionary of groups
        self.subGroups = {}  # Dictionary of subGroups
        self.controlers = []  # List of all the controllers of the component

        # --------------------------------------------------
        # Connector init
        self.connections = {}
        self.connections["standard"] = self.connect_standard

        self.relatives = {}
        self.jointRelatives = {}  # joint relatives mapping for auto connection
        self.controlRelatives = {}
        self.aliasRelatives = {}  # alias names for pretty names on combo box

        # in some situation we need to decouple the relative and the host UI
        self.hostRelatives = {}

        # --------------------------------------------------
        # Joint positions init
        # jnt_pos is a list of lists [Joint position object + name +  optional
        # flag "parent_jnt_org" or object fullName ]
        self.jnt_pos = []
        self.jointList = []

        self.bindPlanes = self.rig.bindPlanes
        self.combinedBindPlanes = self.rig.combinedBindPlanes

        self.transform2Lock = []

        # Data collector
        self.build_data = {}

        # --------------------------------------------------
        # Step
        self.stepMethods = [
            getattr(self, "step_0{}".format(i))
            for i in range(len(self.steps))
        ]

    # =====================================================
    # BUILDING STEP
    # =====================================================

    def step_00(self):
        """Step 00.

        PreScript, initial Hierarchy, create objects and set the connection
        relation.
        """
        self.preScript()
        self.initialHierarchy()
        self.initControlTag()
        self.addObjects()
        self.setRelation()
        return

    def step_01(self):
        """Step 01.

        Get the properties host, create parameters and set layout and logic.
        """
        self.getHost()
        self.config_bind_planes()
        self.validateProxyChannels()
        self.addFullNameParam()
        self.addAttributes()
        self.set_ui_host_components_controls()
        return

    def step_02(self):
        """
        Step 02. Apply all the operators.
        """
        self.addOperators()
        return

    def step_03(self):
        """
        Step 03. Connect the component to the rest of the rig.
        """
        self.initConnector()
        self.addConnection()
        self.connect()
        self.postConnect()
        return

    def step_04(self):
        """
        Step 04. Joint structure creation.
        """
        self.jointStructure()
        return

    def step_05(self):
        """
        Step 05. Finalize the component and post Script.
        """
        self.finalize()
        self.postScript()
        self.collect_build_data()
        return

    # =========================================
    # Creation methods
    def preScript(self):
        """
        Execute an external .py file, before the rig building.
        """
        return

    def initialHierarchy(self):
        """
        Create the inital structure for the rig.

        """
        # Root
        self.root = primitive.addTransformFromPos(
            self.model, self.getName("root"), self.guide.pos["root"]
        )
        self.addToGroup(self.root, names=["componentsRoots"])

        # infos
        attribute.addAttribute(
            self.root, "componentType", "string", self.guide.compType
        )
        attribute.addAttribute(
            self.root, "componentName", "string", self.guide.compName
        )
        attribute.addAttribute(
            self.root,
            "componentVersion",
            "string",
            str(self.guide.version)[1:-1],
        )
        attribute.addAttribute(
            self.root, "componentAuthor", "string", self.guide.author
        )
        attribute.addAttribute(
            self.root, "componentURL", "string", self.guide.url
        )
        attribute.addAttribute(
            self.root, "componentEmail", "string", self.guide.email
        )

        self.compCtl = self.root.addAttr("compCtl", at="message", m=1)

        # joint --------------------------------
        if self.options["joint_rig"]:
            self.component_jnt_org = self.rig.jnt_org
            # The initial assigment of the active jnt and the parent relative
            # jnt is the same, later will be updated base in the user options
            self.active_jnt = self.component_jnt_org
            self.parent_relative_jnt = self.component_jnt_org

        return

    def addObjects(self):
        """This method creates the objects of the component.

        Note:
            REIMPLEMENT. This method should be reimplemented in each component.

        """
        return

    def config_bind_planes(self):
        """This method combine the bind planes."""

        # we process the combine bind planes with the first component
        if not self.combinedBindPlanes:
            for k in self.bindPlanes:
                if len(self.bindPlanes[k]) >= 2:
                    combined_mesh = pm.polyUnite(
                        self.bindPlanes[k],
                        ch=False,
                        mergeUVSets=True,
                        name="{}_bindPlane".format(k),
                    )
                    if (
                        isinstance(combined_mesh, list)
                        and len(combined_mesh) >= 1
                    ):
                        combined_mesh = combined_mesh[0]

                else:
                    combined_mesh = self.bindPlanes[k][0]
                if not self.WIP:
                    combined_mesh.visibility.set(False)
                pm.parent(combined_mesh, self.setupWS)
                self.combinedBindPlanes[k] = combined_mesh

    def addJoint(
        self,
        obj=None,
        name=None,
        newActiveJnt=None,
        UniScale=False,
        segComp=False,
        gearMulMatrix=False,
        rot_off=None,
        vanilla_nodes=False,
        leaf_joint=False,
        guide_relative=None,
        data_contracts=None,
        preBind_relative=None,
        neutral_rot=True,
    ):
        """Add joint as child of the active joint or under driver object.

        This method uses the matrix contraint mgear_solver. If vanilla_nodes is
        set True, it will be bypass and sue the old method

        Args:
            obj (dagNode): The input driver object for the joint.
            name (str): The joint name.
            newActiveJnt (bool or dagNode): If a joint is pass, this joint will
                be the active joint and parent of the newly created joint.
            UniScale (bool): Connects the joint scale with the Z axis for a
                unifor scalin, if set Falsewill connect with each axis
                separated.
            segComp (bool): Set True or False the segment compensation in the
                joint..
            gearMulMatrix (bool): Use the custom gear_multiply matrix node, if
                False will use Maya's default mulMatrix node.
            rot_off (list, optional): offset in degrees for XYZ rotation
            vanilla_nodes (bool, optional): Description
            leaf_joint (bool, optional): If true will create a child joint as
                a leaf joint to  imput the scale. This option is meant for games
            guide_relative (str, optional): Guide locator name that define joint
                position

        No Longer Returned:
            dagNode: The newly created joint.

        """

        # using the old method to connect joints
        if vanilla_nodes:
            return self.addJoint_vanilla(
                obj,
                name,
                newActiveJnt=newActiveJnt,
                UniScale=UniScale,
                segComp=segComp,
                gearMulMatrix=gearMulMatrix,
            )
        else:
            return self._addJoint(
                obj,
                name,
                newActiveJnt=newActiveJnt,
                UniScale=UniScale,
                segComp=segComp,
                rot_off=rot_off,
                leaf_joint=leaf_joint,
                guide_relative=guide_relative,
                data_contracts=data_contracts,
                preBind_relative=preBind_relative,
                neutral_rot=neutral_rot,
            )

    def _addJoint(
        self,
        obj=None,
        name=None,
        newActiveJnt=None,
        UniScale=False,
        segComp=False,
        rot_off=None,
        leaf_joint=False,
        guide_relative=None,
        data_contracts=None,
        preBind_relative=None,
        neutral_rot=True,
    ):
        """Add joint as child of the active joint or under driver object.

        This method uses the matrix contraint mgear_solver. If vanilla_nodes is
        set True, it will be bypass and sue the old method

        Args:
            obj (dagNode): The input driver object for the joint.
            name (str): The joint name.
            newActiveJnt (bool or dagNode): If a joint is pass, this joint will
                be the active joint and parent of the newly created joint.
            UniScale (bool): Connects the joint scale with the Z axis for a
                unifor scalin, if set Falsewill connect with each axis
                separated.
            segComp (bool): Set True or False the segment compensation in the
                joint..
            rot_off (list, optional): offset in degrees for XYZ rotation
            leaf_joint (bool, optional): If true will create a child joint as
                a leaf joint to  imput the scale. This option is meant for games
            guide_relative (str, optional): Guide locator name tha define joint
                position
            preBind_relative (dagNode): if the argument is set will create a
                message connection to track the prebind reference of the joint
                to use in the skinning prebind matrix (like Doritos technique ;) .


        Deleted Parameters:
            dagNode: The newly created joint.

        """
        # force SSC override
        if self.options["force_SSC"]:
            segComp = True

        if not rot_off:
            rot_off = [
                self.settings["joint_rot_offset_x"],
                self.settings["joint_rot_offset_y"],
                self.settings["joint_rot_offset_z"],
            ]
        customName = self.getCustomJointName(len(self.jointList))

        if self.options["joint_rig"]:
            if newActiveJnt:
                self.active_jnt = newActiveJnt
            rule_name = self.getName(
                str(name),
                rule=self.options["joint_name_rule"],
                ext="jnt",
                letter_case=self.options["joint_description_letter_case"],
            )
            # check that the name is a valid Maya name
            if rule_name[0] in "0123456789":
                pm.displayWarning(
                    "Name: {} starts with number and is not".format(rule_name)
                    + " a valid Maya name. Component name prefix"
                    + " will be added"
                )
                rule_name = self.name + rule_name

            # use existing joint - prefer cached lookup over pm.ls() for speed
            cached_custom = self.rig.getCachedJoint(customName) if customName else None
            cached_rule = self.rig.getCachedJoint(rule_name)

            if cached_custom and self.options["connect_joints"]:
                jnt = cached_custom
                keep_off = True
            elif cached_rule and self.options["connect_joints"]:
                jnt = cached_rule
                keep_off = True
            else:
                if isinstance(obj, datatypes.Matrix):
                    t = obj
                else:
                    t = transform.getTransform(obj)
                jnt = primitive.addJoint(
                    self.active_jnt, customName or rule_name, t
                )
                keep_off = False

            # check if already have connections
            # for example Mehahuman twist joint already have connections
            if not attribute.has_in_connections(jnt):
                # Disconnect inversScale for better preformance
                if isinstance(self.active_jnt, pm.nodetypes.Joint):
                    try:
                        pm.disconnectAttr(
                            self.active_jnt.scale, jnt.inverseScale
                        )

                    except RuntimeError:
                        # This handle the situation where we have in between
                        # joints transformation due a negative scaling
                        if not isinstance(jnt, pm.nodetypes.Joint):
                            pm.ungroup(jnt.getParent())
                # All new jnts are the active by default
                self.active_jnt = jnt

                use_cns_connection = False
                if keep_off:
                    # if jnt.rotate.get() != (0, 0, 0):
                    if not all(component == 0 for component in jnt.rotate.get()):
                        pm.displayInfo(f"Joint {jnt.name()} has non-zero rotations, We will use Constraints to connect: {jnt.rotate.get()}")
                        use_cns_connection = True
                    if isinstance(obj, datatypes.Matrix):
                        driver = None
                        jnt.setMatrix(obj, worldSpace=True)
                    else:
                        driver = primitive.addTransform(
                            obj, name=obj.name() + "_cnx_off"
                        )
                        transform.matchWorldTransform(jnt, driver)
                        rot_off = [0, 0, 0]

                else:
                    if isinstance(obj, datatypes.Matrix):
                        driver = None
                        jnt.setMatrix(obj, worldSpace=True)

                    else:
                        driver = obj
                        rot_off = rot_off

                if use_cns_connection and self.options["connect_joints"]:
                    # coonnect jnt to driver using parent contraint and scale
                    # and mantain offset
                    pm.parentConstraint(
                        driver, jnt, maintainOffset=True, weight=1
                    )
                    pm.scaleConstraint(
                        driver, jnt, maintainOffset=True, weight=1
                    )
                    cns_m = None

                elif driver:
                    # if segComp:
                    #     # if segment compensation is active we handle the scale
                    #     # outside of the gear matrix contraint
                    #     srt = "rt"
                    #     mulmat_node = node.createMultMatrixNode(
                    #         driver.worldMatrix, self.root.worldInverseMatrix
                    #     )
                    #     dm_node = node.createDecomposeMatrixNode(
                    #         mulmat_node.matrixSum
                    #     )
                    #     # check if there is negative scaling and compensate
                    #     invert_scale = []
                    #     for v in dm_node.outputScale.get():
                    #         if v < 0:
                    #             invert_scale.append(-1.0)
                    #         else:
                    #             invert_scale.append(1.0)
                    #     if -1.0 in invert_scale:
                    #         node.createMulNode(
                    #             [
                    #                 dm_node.outputScaleX,
                    #                 dm_node.outputScaleY,
                    #                 dm_node.outputScaleZ,
                    #             ],
                    #             invert_scale,
                    #             [jnt.sx, jnt.sy, jnt.sz],
                    #         )
                    #         # if negative scaling we need to inver rotation
                    #         # directions in X and Y
                    #         srt = "t"
                    #     else:
                    #         pm.connectAttr(dm_node.outputScale, jnt.s)

                    # else:
                    #     srt = "srt"
                    # cns_m = applyop.gear_matrix_cns(
                    #     driver, jnt, rot_off=rot_off, connect_srt=srt
                    # )
                    if self.options["joint_worldOri"]:
                        driver = primitive.addTransformFromPos(
                            driver,
                            name=obj.name() + "_world_ori",
                            pos=transform.getTranslation(driver),
                        )

                    cns_m = applyop.gear_matrix_cns(
                        driver, jnt, rot_off=rot_off, connect_srt="srt"
                    )

                    # # if negative scaling we need to invert rotation directions
                    # # in X and Y after the constraint matrix is created
                    # if srt == "t":
                    #     node.createMulNode(
                    #         [
                    #             cns_m.rotateX,
                    #             cns_m.rotateY,
                    #             cns_m.rotateZ,
                    #         ],
                    #         [-1, -1, 1],
                    #         [jnt.rx, jnt.ry, jnt.rz],
                    #     )

                    # invert negative scaling in Joints. We only inver Z axis,
                    # so is the only axis that we are checking
                    if jnt.scaleZ.get() < 0:
                        cns_m.scaleMultZ.set(-1.0)
                        cns_m.rotationMultX.set(-1.0)
                        cns_m.rotationMultY.set(-1.0)

                    # if unifor scale is False by default. It can be forced
                    # using uniScale arg or set from the ui
                    if self.options["force_uniScale"]:
                        UniScale = True
                    if UniScale:
                        attribute.disconnect_inputs(jnt, ["scale"])
                        pm.connectAttr(cns_m.scaleZ, jnt.sx)
                        pm.connectAttr(cns_m.scaleZ, jnt.sy)
                        pm.connectAttr(cns_m.scaleZ, jnt.sz)

                    # leaf joint
                    if leaf_joint and not UniScale:
                        leaf_joint_name = "leaf_" + jnt.name()
                        cached_leaf = self.rig.getCachedJoint(leaf_joint_name)
                        if cached_leaf and self.options["connect_joints"]:
                            leaf_jnt = cached_leaf
                        else:
                            leaf_jnt = primitive.addJoint(
                                jnt, "leaf_" + jnt.name(), t
                            )
                            leaf_jnt.attr("radius").set(1.5)
                            leaf_jnt.attr("overrideEnabled").set(1)
                            leaf_jnt.attr("overrideColor").set(13)
                            leaf_jnt.rotate.set([0, 0, 0])
                        # create and connect message to track the leaf joint relation
                        if not jnt.hasAttr("leaf_joint"):
                            pm.addAttr(
                                jnt, ln="leaf_joint", at="message", m=True
                            )
                        pm.connectAttr(leaf_jnt.message, jnt.leaf_joint)
                        self.addToGroup(leaf_jnt, "deformers")
                        # connect scale
                        jnt.disconnectAttr("scale")
                        jnt.disconnectAttr("shear")
                        pm.connectAttr(cns_m.scale, leaf_jnt.scale)
                        pm.connectAttr(cns_m.shear, leaf_jnt.shear)

                    if preBind_relative:
                        pm.addAttr(
                            jnt, ln="preBind_relative", at="message", m=False
                        )
                        pm.connectAttr(
                            preBind_relative.message, jnt.preBind_relative
                        )

                else:
                    cns_m = None

                # Segment scale compensate on/Off
                # TODO: before was always off to avoid issues with the
                # global scale. Confirm there is no conflicts
                jnt.setAttr("segmentScaleCompensate", segComp)

                if not keep_off and neutral_rot:
                    # setting the joint orient compensation in order to
                    # have clean rotation channels
                    jnt.setAttr("jointOrient", 0, 0, 0)
                    if cns_m:
                        m = cns_m.drivenRestMatrix.get()
                    else:
                        driven_m = pm.getAttr(jnt + ".parentInverseMatrix[0]")
                        m = t * driven_m
                        jnt.rotate.set([0, 0, 0])
                        if jnt.scaleZ.get() < 0:
                            jnt.scaleZ.set(1)
                    tm = datatypes.TransformationMatrix(m)
                    r = datatypes.degrees(tm.getRotation())
                    jnt.jointOrient.set([r[0], r[1], r[2]])
                elif not neutral_rot:
                    jnt.setAttr("jointOrient", 0, 0, 0)
                    driven_m = pm.getAttr(jnt + ".parentInverseMatrix[0]")
                    m = t * driven_m
                    tm = datatypes.TransformationMatrix(m)
                    r = datatypes.degrees(tm.getRotation())
                    jnt.rotate.set([r[0], r[1], r[2]])

                # set not keyable
                attribute.setNotKeyableAttributes(jnt)

        else:
            jnt = primitive.addJoint(
                obj,
                customName or self.getName(str(name) + "_jnt"),
                transform.getTransform(obj),
            )
            pm.connectAttr(self.rig.jntVis_att, jnt.attr("visibility"))
            attribute.lockAttribute(jnt)

        self.addToGroup(jnt, "deformers")

        if guide_relative:
            if not jnt.hasAttr("guide_relative"):
                attribute.addAttribute(jnt, "guide_relative", "string")
            jnt.guide_relative.set(
                "{}_{}".format(self.fullName, guide_relative)
            )

        if data_contracts:
            if not jnt.hasAttr("data_contracts"):
                attribute.addAttribute(jnt, "data_contracts", "string")
            jnt.data_contracts.set(data_contracts)

        # # add comp type  metadata
        # if not jnt.hasAttr("comp_type"):
        #     attribute.addAttribute(jnt, "comp_type", "string")
        # jnt.comp_type.set(self.settings["comp_type"])
        return jnt

    # old method to allow the joint creation using Maya default nodes
    def addJoint_vanilla(
        self,
        obj=None,
        name=None,
        newActiveJnt=None,
        UniScale=False,
        segComp=False,
        gearMulMatrix=False,
    ):
        """Add joint as child of the active joint or under driver object.

        NOTE:
        This is the old way to connect joint before the matrix constraint node
        was added to mgear_solvers.

        We keep this method in case we want to create rigs using only maya
        default (vanilla maya) nodes

        Args:
            obj (dagNode): The input driver object for the joint.
            name (str): The joint name.
            newActiveJnt (bool or dagNode): If a joint is pass, this joint will
                be the active joint and parent of the newly created joint.
            UniScale (bool): Connects the joint scale with the Z axis for a
                unifor scalin, if set Falsewill connect with each axis
                separated.
            segComp (bool): Set True or False the segment compensation in the
                joint..
            gearMulMatrix (bool): Use the custom gear_multiply matrix node, if
                False will use Maya's default mulMatrix node.

        Returns:
            dagNode: The newly created joint.

        """

        customName = self.getCustomJointName(len(self.jointList))

        if self.options["joint_rig"]:
            if newActiveJnt:
                self.active_jnt = newActiveJnt

            jnt = primitive.addJoint(
                self.active_jnt,
                customName or self.getName(str(name) + "_jnt"),
                transform.getTransform(obj),
            )

            # Disconnect inversScale for better preformance
            if isinstance(self.active_jnt, pm.nodetypes.Joint):
                try:
                    pm.disconnectAttr(self.active_jnt.scale, jnt.inverseScale)

                except RuntimeError:
                    # This handle the situation where we have in between joints
                    # transformation due a negative scaling
                    pm.ungroup(jnt.getParent())
            # All new jnts are the active by default
            self.active_jnt = jnt
            if gearMulMatrix:
                mulmat_node = applyop.gear_mulmatrix_op(
                    obj + ".worldMatrix", jnt + ".parentInverseMatrix"
                )
                dm_node = node.createDecomposeMatrixNode(
                    mulmat_node + ".output"
                )
                m = mulmat_node.attr("output").get()
            else:
                mulmat_node = node.createMultMatrixNode(
                    obj + ".worldMatrix", jnt + ".parentInverseMatrix"
                )
                dm_node = node.createDecomposeMatrixNode(
                    mulmat_node + ".matrixSum"
                )
                m = mulmat_node.attr("matrixSum").get()
            pm.connectAttr(dm_node + ".outputTranslate", jnt + ".t")
            pm.connectAttr(dm_node + ".outputRotate", jnt + ".r")
            # TODO: fix squash stretch solver to scale the joint uniform
            # the next line cheat the uniform scaling only fo X or Y axis
            # oriented joints
            if self.options["force_uniScale"]:
                UniScale = True

            # invert negative scaling in Joints. We only inver Z axis, so is
            # the only axis that we are checking
            if dm_node.attr("outputScaleZ").get() < 0:
                mul_nod_invert = node.createMulNode(
                    dm_node.attr("outputScaleZ"), -1
                )
                out_val = mul_nod_invert.attr("outputX")
            else:
                out_val = dm_node.attr("outputScaleZ")

            # connect scaling
            if UniScale:
                pm.connectAttr(out_val, jnt + ".sx")
                pm.connectAttr(out_val, jnt + ".sy")
                pm.connectAttr(out_val, jnt + ".sz")
            else:
                pm.connectAttr(dm_node.attr("outputScaleX"), jnt + ".sx")
                pm.connectAttr(dm_node.attr("outputScaleY"), jnt + ".sy")
                pm.connectAttr(out_val, jnt + ".sz")
                pm.connectAttr(dm_node + ".outputShear", jnt + ".shear")

            # Segment scale compensate Off to avoid issues with the global
            # scale
            jnt.setAttr("segmentScaleCompensate", segComp)

            jnt.setAttr("jointOrient", 0, 0, 0)

            # setting the joint orient compensation in order to have clean
            # rotation channels
            jnt.jointOrient.set(jnt.rotate.get())

            im = m.inverse()

            if gearMulMatrix:
                mul_nod = applyop.gear_mulmatrix_op(
                    mulmat_node.attr("output"), im, jnt, "r"
                )
                dm_node2 = mul_nod.output.listConnections()[0]
            else:
                mul_nod = node.createMultMatrixNode(
                    mulmat_node.attr("matrixSum"), im, jnt, "r"
                )
                dm_node2 = mul_nod.matrixSum.listConnections()[0]

            # if jnt.attr("sz").get() < 0:
            if dm_node.attr("outputScaleZ").get() < 0:
                # if negative scaling we have to negate some axis for rotation
                neg_rot_node = pm.createNode("multiplyDivide")
                pm.setAttr(neg_rot_node + ".operation", 1)
                pm.connectAttr(
                    dm_node2.outputRotate, neg_rot_node + ".input1", f=True
                )
                for v, axis in zip([-1, -1, 1], "XYZ"):
                    pm.setAttr(neg_rot_node + ".input2" + axis, v)
                pm.connectAttr(neg_rot_node + ".output", jnt + ".r", f=True)

            # set not keyable
            attribute.setNotKeyableAttributes(jnt)

        else:
            jnt = primitive.addJoint(
                obj,
                customName or self.getName(str(name) + "_jnt"),
                transform.getTransform(obj),
            )
            pm.connectAttr(self.rig.jntVis_att, jnt.attr("visibility"))
            attribute.lockAttribute(jnt)

        self.addToGroup(jnt, "deformers")

        # This is a workaround due the evaluation problem with compound attr
        # TODO: This workaround, should be removed onces the evaluation issue
        # is fixed
        # github issue: Shifter: Joint connection: Maya evaluation Bug #210
        # Using cmds for connection operations
        jnt_name = jnt.name()
        dm = cmds.listConnections(f"{jnt_name}.r", p=True, type="decomposeMatrix")
        if dm:
            dm_node = dm[0].split(".")[0]
            cmds.disconnectAttr(dm[0], f"{jnt_name}.r")
            cmds.connectAttr(f"{dm_node}.outputRotateX", f"{jnt_name}.rx")
            cmds.connectAttr(f"{dm_node}.outputRotateY", f"{jnt_name}.ry")
            cmds.connectAttr(f"{dm_node}.outputRotateZ", f"{jnt_name}.rz")

        dm = cmds.listConnections(f"{jnt_name}.t", p=True, type="decomposeMatrix")
        if dm:
            dm_node = dm[0].split(".")[0]
            cmds.disconnectAttr(dm[0], f"{jnt_name}.t")
            cmds.connectAttr(f"{dm_node}.outputTranslateX", f"{jnt_name}.tx")
            cmds.connectAttr(f"{dm_node}.outputTranslateY", f"{jnt_name}.ty")
            cmds.connectAttr(f"{dm_node}.outputTranslateZ", f"{jnt_name}.tz")

        return jnt

    def getNormalFromPos(self, pos):
        """
        Get the normal vector from 3 positions.

        Args:
            pos (list of vectors): List of 3 vectors.

        Returns:
            vector: The 3 vectors plane normal.

        """
        if len(pos) < 3:
            mgear.log(
                "%s : Not enough references to define normal" % self.fullName,
                mgear.sev_error,
            )

        return vector.getPlaneNormal(pos[0], pos[1], pos[2])

    def getBiNormalFromPos(self, pos):
        """
        Get the binormal vector from 3 positions.

        Args:
            pos (list of vectors): List of 3 vectors.

        Returns:
            vector: The 3 vectors plane binormal.

        """
        if len(pos) < 3:
            mgear.log(
                "%s : Not enough references to define binormal"
                % self.fullName,
                mgear.sev_error,
            )

        return vector.getPlaneBiNormal(pos[0], pos[1], pos[2])

    def addCtl(
        self,
        parent,
        name,
        m,
        color,
        iconShape,
        tp=None,
        lp=True,
        mirrorConf=[0, 0, 0, 0, 0, 0, 0, 0, 0],
        guide_loc_ref=None,
        add_2_grp=True,
        **kwargs
    ):
        """
        Create the control and apply the shape, if this is alrealdy stored
        in the guide controllers grp.

        Args:
            parent (dagNode): The control parent
            name (str): The control name.
            m (matrix): The transfromation matrix for the control.
            color (int or list of float): The color for the control in index or
                RGB.
            iconShape (str): The controls default shape.
            tp (dagNode): Tag Parent Control object to connect as a parent
                controller
            lp (bool): Lock the parent controller channels
            kwargs (variant): Other arguments for the iconShape type variations

        Returns:
            dagNode: The Control.

        """
        if "degree" not in kwargs:
            kwargs["degree"] = 1

        # remove the _ctl hardcoded in component name
        if name.endswith("_ctl"):
            name = name[:-4]
        # in some situation the name will be only ctl and should be removed
        # for example control_01
        if name.endswith("ctl"):
            name = name[:-3]

        # NOTE: this is a dirty workaround to keep backwards compatibility on
        # control_01 and other component where the description of the cotrol
        # was just the ctl suffix.
        rule = self.options["ctl_name_rule"]
        source_rule = rule
        if not name:
            rule = rule.replace(r"_{description}_", "_")
            rule = rule.replace(r"{description}", "")
            # Adjust leading underscores
            leading_underscores = (
                len(re.match(r"^_+", source_rule).group(0))
                if re.match(r"^_+", source_rule)
                else 0
            )
            new_leading_underscores = (
                len(re.match(r"^_+", rule).group(0))
                if re.match(r"^_+", rule)
                else 0
            )
            while new_leading_underscores > leading_underscores:
                rule = rule[1:]
                new_leading_underscores -= 1

            # Adjust trailing underscores
            trailing_underscores = (
                len(re.match(r"_+$", source_rule).group(0))
                if re.match(r"_+$", source_rule)
                else 0
            )
            new_trailing_underscores = (
                len(re.match(r"_+$", rule).group(0))
                if re.match(r"_+$", rule)
                else 0
            )
            while new_trailing_underscores > trailing_underscores:
                rule = rule[:-1]
                new_trailing_underscores -= 1

        fullName = self.getName(
            name,
            rule=rule,
            ext="ctl",
            letter_case=self.options["ctl_description_letter_case"],
        )

        bufferName = fullName + "_controlBuffer"
        if bufferName in self.rig.guide.controllers:
            ctl_ref = self.rig.guide.controllers[bufferName]
            ctl = primitive.addTransform(parent, fullName, m)
            color = curve.get_color(ctl_ref)
            for shape in ctl_ref.getShapes():
                ctl.addChild(shape, shape=True, add=True)
                pm.rename(shape, fullName + "Shape")
            icon.setcolor(ctl, color)
        else:
            ctl = icon.create(parent, fullName, m, color, iconShape, **kwargs)

        # add metadata attirbutes.
        attribute.addAttribute(ctl, "isCtl", "bool", keyable=False)
        attribute.addAttribute(ctl, "uiHost", "string", keyable=False)
        ctl.addAttr("uiHost_cnx", at="message", multi=False)
        # set the control Role for complex components. If the component is
        # of type control_01  the control role will default to
        # a generic name "ctl"
        if not name:
            role_name = "ctl"
        else:
            role_name = name
        attribute.addAttribute(
            ctl, "ctl_role", "string", keyable=False, value=role_name
        )

        # locator reference for quick guide matching
        # TODO: this is a temporal implementation. We should store the full
        # guide data in future iterations
        if guide_loc_ref:
            attribute.addAttribute(
                ctl,
                "guide_loc_ref",
                "string",
                keyable=False,
                value=guide_loc_ref,
            )

        # mgear name. This keep track of the default shifter name. This naming
        # system ensure that each control has a unique id. Tools like mirror or
        # flip pose can use it to track symmetrical controls
        attribute.addAttribute(
            ctl,
            "shifter_name",
            "string",
            keyable=False,
            value=self.getName(name) + "_ctl",
        )
        attribute.addAttribute(
            ctl, "side_label", "string", keyable=False, value=self.side
        )
        attribute.addAttribute(
            ctl,
            "L_custom_side_label",
            "string",
            keyable=False,
            value=self.options["side_left_name"],
        )
        attribute.addAttribute(
            ctl,
            "R_custom_side_label",
            "string",
            keyable=False,
            value=self.options["side_right_name"],
        )
        attribute.addAttribute(
            ctl,
            "C_custom_side_label",
            "string",
            keyable=False,
            value=self.options["side_center_name"],
        )

        attribute.addEnumAttribute(
            ctl,
            "rotate_order",
            0,
            ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx"),
            keyable=False,
        )

        # create the attributes to handlde mirror and symetrical pose
        attribute.add_mirror_config_channels(ctl, mirrorConf)
        if add_2_grp:
            if self.settings["ctlGrp"]:
                ctlGrp = self.settings["ctlGrp"]
                self.addToGroup(ctl, ctlGrp, "controllers")
            else:
                ctlGrp = "controllers"
                self.addToGroup(ctl, ctlGrp)

            # lock the control parent attributes if is not a control
            if parent not in self.groups[ctlGrp] and lp:
                self.transform2Lock.append(parent)

        # Set the control shapes isHistoricallyInteresting
        # Use cmds for faster shape operations
        ctl_name = ctl.name()
        shapes = cmds.listRelatives(ctl_name, shapes=True, fullPath=True) or []
        maya_version = versions.current()
        for shape in shapes:
            cmds.setAttr(f"{shape}.isHistoricallyInteresting", False)
            # connecting the always draw shapes on top to global attribute
            if maya_version >= 20220000:
                cmds.connectAttr(
                    self.rig.ctlXRay_att.name(), f"{shape}.alwaysDrawOnTop"
                )

        # set controller tag
        if versions.current() >= 201650:
            try:
                oldTag = pm.PyNode(ctl.name() + "_tag")

                if not oldTag.controllerObject.connections():
                    # NOTE:  The next line is comment out. Because this will
                    # happend alot since core does't clean
                    # controller tags after deleting the control Object of the
                    # tag. This have been log to Autodesk.
                    # If orphane tags are found, it will be clean in silence.
                    # pm.displayWarning(
                    #     "Orphane Tag: %s  will be delete and created new for: %s"
                    #     % (oldTag.name(), ctl.name())
                    # )
                    pm.delete(oldTag)

            except:
                pass

            self.add_controller_tag(ctl, tp)
        self.controlers.append(ctl)

        # connect control message to root
        ni = attribute.get_next_available_index(self.root.compCtl)
        pm.connectAttr(
            ctl.message, self.root.attr("compCtl[{}]".format(str(ni)))
        )

        ctl.addAttr("compRoot", at="message", m=False)
        self.root.message >> ctl.compRoot

        return ctl

    def add_controller_tag(self, ctl, tagParent):
        self.rig.add_controller_tag(ctl, tagParent)

    def addToGroup(self, objects, names=["hidden"], parentGrp=None):
        """Add the object in a collection for later group creation.

        Args:
            objects (dagNode or list of dagNode): Object to put in the group.
            names (str or list of str): Names of the groups to create.
        """

        if not isinstance(names, list):
            names = [names]

        if not isinstance(objects, list):
            objects = [objects]

        for name in names:
            self.groups.setdefault(name, []).extend(objects)

            if parentGrp:
                subgrp = self.subGroups.setdefault(parentGrp, [])
                if name not in subgrp:
                    subgrp.append(name)

    def add_match_ref(self, ctl, parent, name, cnx=True):
        """Add maching reference transform. This is use to track the positions
        to perform IK/FK matching

        Args:
            ctl (dagNode): Description
            parent (dagNode): Description
            name (str): Description
            cnx (bool, optional): If true will create the message attr and
                conexion

        Returns:
            dagNode: match transform node
        """
        # create match
        if self.WIP:
            add_match = primitive.addLocator
        else:
            add_match = primitive.addTransform
        match = add_match(
            parent, self.getName(name), transform.getTransform(ctl)
        )

        # add match attr and connection to the control
        if cnx:
            ctl.addAttr("match_ref", at="message", multi=False)
            pm.connectAttr(match.message, ctl.match_ref)

        return match

    # =====================================================
    # PROPERTY
    # =====================================================

    def getHost(self):
        """Get the host for the properties"""
        comp_relative = self.rig.findComponent(self.settings["ui_host"])
        if comp_relative and comp_relative.hostRelatives:
            hostRelatives = comp_relative.hostRelatives
            relative_name = self.rig.getRelativeName(self.settings["ui_host"])
            if relative_name in hostRelatives:
                self.uihost = hostRelatives[relative_name]
            else:
                pm.displayWarning(
                    "Host relative name {} not found".format(relative_name)
                )
                self.uihost = self.rig.findRelative(self.settings["ui_host"])
        else:
            self.uihost = self.rig.findRelative(self.settings["ui_host"])

    def set_ui_host_components_controls(self):
        """Set a list of all controls that are common to the ui host
        and the message connections

        Also, set the value of the control ui host. this should be set after
        all the objects are created. So can't be set when the ctl is created
        because maybe the ui host doesn't exist yet

        """

        # adds the attribute - cache existing attrs for faster lookup
        uihost_name = self.uihost.name()
        existing_attrs = set(cmds.listAttr(uihost_name) or [])

        idx = 0
        if self.options["classicChannelNames"]:
            attrName = self.getName(f"id{idx}_ctl")
            while attrName in existing_attrs:
                idx += 1
                attrName = self.getName(f"id{idx}_ctl")

        else:
            attrName = self.getAttrName(f"id{idx}_ctl")
            while attrName in existing_attrs:
                idx += 1
                attrName = self.getAttrName(f"id{idx}_ctl")
        attr_cnx_name = attrName + "_cnx"
        self.uihost.addAttr(attr_cnx_name, at="message", m=1)

        # creates a usable string list and message connections
        # Build string list efficiently with join instead of += concatenation
        ctl_names = []
        for e, ctl in enumerate(self.controlers):
            ctl_names.append(ctl.name())
            pm.connectAttr(ctl.message, self.uihost.attr(attr_cnx_name)[e])
            ctl.uiHost.set(uihost_name)
            pm.connectAttr(self.uihost.message, ctl.uiHost_cnx)
        controls_string = ",".join(ctl_names) + ","

        attribute.addAttribute(
            node=self.uihost,
            longName=attrName,
            attributeType="string",
            keyable=False,
            value=controls_string,
        )

    def validateProxyChannels(self):
        """Check the Maya version to determinate if we can use proxy channels

        Also check user setting on the guide.
        This feature is available from 2016.5

        """

        if versions.current() >= 201650 and self.options["proxyChannels"]:
            self.validProxyChannels = True
        else:
            self.validProxyChannels = False

    def addAttributes(self):
        """This method add the attributes of the component.

        Note:
            REIMPLEMENT. This method should be reimplemented in each component.

        """
        return

    def addFullNameParam(self):
        """Add a parameter to the animation property.

        Note that animatable and keyable are True per default.

        """

        # attr = self.addAnimEnumParam("", "", 0, ["---------------"] )
        if self.options["classicChannelNames"]:
            attr = self.addAnimEnumParam(
                self.getName(), "__________", 0, [self.getName()]
            )
        else:
            if self.options["attrPrefixName"]:
                name = self.name
            else:
                name = self.guide.compName
            attr = self.addAnimEnumParam(name, "__________", 0, [name])

        return attr

    def addAnimParam(
        self,
        longName,
        niceName,
        attType,
        value,
        minValue=None,
        maxValue=None,
        keyable=True,
        readable=True,
        storable=True,
        writable=True,
        uihost=None,
        exactName=False,
    ):
        """Add a parameter to the animation property.

        Note that animatable and keyable are True per default.

        Args:
            longName (str): The attribute name.
            niceName (str): The attribute nice name. (optional)
            attType (str): The Attribute Type.Exp:'string', 'bool', 'long', etc
            value (float or int): The default value.
            minValue (float or int): minimum value. (optional)
            maxValue (float or int): maximum value. (optional)
            keyable (bool): Set if the attribute is keyable or not. (optional)
            readable (bool): Set if the attribute is readable or not.(optional)
            storable (bool): Set if the attribute is storable or not.(optional)
            writable (bool): Set if the attribute is writable or not.(optional)
            uihost (dagNode): Optional uihost, if none self.uihost will be use
            exactName (bool): if true will use the attr name without prefix
                            from the component name or instance name.(optional)

        Returns:
            pm.Attribute: A pymaya `Attribute` wrapper of the new attribute.

        """
        if not uihost:
            uihost = self.uihost

        if self.options["classicChannelNames"]:
            attr = attribute.addAttribute(
                uihost,
                self.getName(longName),
                attType,
                value,
                niceName,
                None,
                minValue=minValue,
                maxValue=maxValue,
                keyable=keyable,
                readable=readable,
                storable=storable,
                writable=writable,
            )
        else:
            if exactName:
                attr_name = longName
            else:
                attr_name = self.getAttrName(longName)

            if uihost.hasAttr(attr_name):
                attr = uihost.attr(attr_name)
            else:
                attr = attribute.addAttribute(
                    uihost,
                    attr_name,
                    attType,
                    value,
                    niceName,
                    None,
                    minValue=minValue,
                    maxValue=maxValue,
                    keyable=keyable,
                    readable=readable,
                    storable=storable,
                    writable=writable,
                )

        return attr

    # Add a parameter to the animation property.\n
    # Note that animatable and keyable are True per default.
    # @param self
    def addAnimEnumParam(
        self,
        longName,
        niceName,
        value,
        enum=[],
        keyable=True,
        readable=True,
        storable=True,
        writable=True,
        uihost=None,
        exactName=False,
    ):
        """Add a parameter to the animation property.

        Note that animatable and keyable are True per default.

        Args:
            longName (str): The attribute name.
            niceName (str): The attribute nice name. (optional)
            attType (str): The Attribute Type. Exp: 'string', 'bool', etc..
            value (float or int): The default value.
            enum (list of str): The list of elements in the enumerate control
            keyable (bool): Set if the attribute is keyable or not. (optional)
            readable (bool): Set if the attribute is readable or not.(optional)
            storable (bool): Set if the attribute is storable or not.(optional)
            writable (bool): Set if the attribute is writable or not.(optional)
            uihost (dagNode): Optional uihost, if none self.uihost will be use

        Returns:
            str: The long name of the new attribute

        """

        if not uihost:
            uihost = self.uihost

        if exactName:
            attr_name = longName
        else:
            attr_name = self.getAttrName(longName)

        if self.options["classicChannelNames"]:
            attr = attribute.addEnumAttribute(
                uihost,
                self.getName(longName),
                value,
                enum,
                niceName,
                None,
                keyable=keyable,
                readable=readable,
                storable=storable,
                writable=writable,
            )
        else:
            if uihost.hasAttr(attr_name):
                attr = uihost.attr(attr_name)
            else:
                attr = attribute.addEnumAttribute(
                    uihost,
                    attr_name,
                    value,
                    enum,
                    niceName,
                    None,
                    keyable=keyable,
                    readable=readable,
                    storable=storable,
                    writable=writable,
                )

        return attr

    def addSetupParam(
        self,
        longName,
        niceName,
        attType,
        value,
        minValue=None,
        maxValue=None,
        keyable=True,
        readable=True,
        storable=True,
        writable=True,
    ):
        """Add a parameter to the setup property.
        Note that animatable and keyable are False per default.

        Args:
            longName (str): The attribute name.
            niceName (str): The attribute nice name. (optional)
            attType (str): The Attribute Type. Exp: 'string', 'bool', etc..
            value (float or int): The default value.
            minValue (float or int): minimum value. (optional)
            maxValue (float or int): maximum value. (optional)
            keyable (bool): Set if the attribute is keyable or not.(optional)
            readable (bool): Set if the attribute is readable or not.(optional)
            storable (bool): Set if the attribute is storable or not.(optional)
            writable (bool): Set if the attribute is writable or not.(optional)

        Returns:
            str: The long name of the new attribute

        """
        attr = attribute.addAttribute(
            self.root,
            longName,
            attType,
            value,
            niceName,
            None,
            minValue=minValue,
            maxValue=maxValue,
            keyable=keyable,
            readable=readable,
            storable=storable,
            writable=writable,
        )

        return attr

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """This method add the operators of the component.

        Note:
            REIMPLEMENT. This method should be reimplemented in each component.

        """
        return

    # =====================================================
    # CONNECTOR
    # =====================================================

    def addConnection(self):
        """Add more connection definition to the set.

        Note:
            REIMPLEMENT. This method should be reimplemented in each component.
            Only if you need to use an new connection (not the standard).

        """
        return

    def setRelation(self):
        """Set the relation beetween object from guide to rig.

        Note:
            REIMPLEMENT. This method should be reimplemented in each component.

        """
        for name in self.guide.objectNames:
            self.relatives[name] = self.root
            self.controlRelatives[name] = self.global_ctl

    def getRelation(self, name):
        """Return the relational object from guide to rig.

        Args:
            name (str): Local name of the guide object.

        Returns:
            dagNode: The relational object.

        """
        if name not in self.relatives:
            mgear.log(
                "Can't find reference for object : "
                + self.fullName
                + "."
                + name,
                mgear.sev_error,
            )
            return False
        return self.relatives[name]

    def getControlRelation(self, name):
        """Return the relational object from guide to rig.

        Args:
            name (str): Local name of the guide object.

        Returns:
            dagNode: The relational object.

        """
        if name not in self.controlRelatives:
            mgear.log(
                "Control tag relative: Can't find reference for "
                " object : " + self.fullName + "." + name,
                mgear.sev_error,
            )
            return False

        return self.controlRelatives[name]

    def get_alias_relation(self, name, comp_relative, fullName=True):
        """Return the relational name alias from guide to rig.

        If not alias name has been set, this function will return the original
        guide reference name.

        Args:
            name (str): Local name of the guide object.
            comp_relative (obj): relative component
            fullName (bool, optional): if True will return the component name with alias

        Returns:
            str: Space alias name.

        """
        comp_name = self.rig.getComponentName(name)
        rel_name = self.rig.getRelativeName(name)
        if rel_name not in comp_relative.aliasRelatives:
            return name

        if fullName:
            return "{}_{}".format(
                comp_name, comp_relative.aliasRelatives[rel_name]
            )
        else:
            return comp_relative.aliasRelatives[rel_name]

    def get_valid_ref_list(self, ref_list):
        """Returns the purged list of ref_list

        If the component doesn't exist will skip it

        Args:
            ref_list (list): Initial references names list

        Returns:
            list: Purged relatives list
        """
        return self._get_valid_array_list(ref_list)[1]

    def get_valid_alias_list(self, ref_list, fullName=True):
        """Returns the alias list of valid components

        If the component doesn't exist will skip it

        Args:
            ref_list (list): Initial references names list

        Returns:
            list: Alias names list
        """
        return self._get_valid_array_list(ref_list, fullName=fullName)[0]

    def _get_valid_array_list(self, array_list, fullName=True):
        """Returns the alias list of valid components and the purged array_list

        If the component doesn't exist will skip it

        Args:
            ref_list (list): Initial references names list

        Returns:
            list of list: Alias names list and purged relatives list
        """
        alias_list = [[], []]
        for rn in array_list:
            comp_relative = self.rig.findComponent(rn)
            if comp_relative:
                o_name = self.get_alias_relation(
                    rn, comp_relative, fullName=fullName
                )
                alias_list[0].append(o_name)
                alias_list[1].append(rn)
            else:
                pm.displayWarning(
                    "While connecting reference array {}"
                    " was not found. This will be skipped. But"
                    " you should check your guides "
                    "configuration".format(rn)
                )

        return alias_list

    def initControlTag(self):
        """Initialice the control tag parent.

        The controllers tag are a new feature from Maya 2016.5 and up.
        Helps to stablish realtions with a custom walkpick.
        Also tells core how to evaluate the control properly on parallel
        evaluation

        """
        self.parentCtlTag = None
        if versions.current() >= 201650:
            parent_name = "none"
            if self.guide.parentComponent is not None:
                parent_name = self.guide.parentComponent.getName(
                    self.guide.parentLocalName
                )
            self.parentCtlTag = self.rig.findControlRelative(parent_name)

    def initConnector(self):
        """Initialize the connections

        Initialize the connections beetween the component and his parent
        component.

        """
        parent_name = "none"
        if self.guide.parentComponent is not None:
            parent_name = self.guide.parentComponent.getName(
                self.guide.parentLocalName
            )
        self.parent = self.rig.findRelative(parent_name)
        self.parent_comp = self.rig.findComponent(parent_name)

    def connect(self):
        """Connect the component

        Connect the component to the rest of the rig using the defined
        connection.

        """

        if self.settings["connector"] not in self.connections:
            # mgear.log("Unable to connect object", mgear.sev_error)
            # return False
            pm.displayWarning(
                "Connector of type: {}, not found. Falling back "
                "to standard connector".format(self.settings["connector"])
            )
            self.settings["connector"] = "standard"
        try:
            self.connections[self.settings["connector"]]()
            return True
        except AttributeError:
            return False

    def connect_standard(self):
        """Standard Connection

        Standard connection definition. This is a simple parenting of the root.

        """
        self.parent.addChild(self.root)

    def connect_standardWithIkRef(self):
        """Standard IK Connection

        Standard connection definition with ik and upv references.

        """
        self.parent.addChild(self.root)

        # Set the Ik Reference
        self.connectRef(self.settings["ikrefarray"], self.ik_cns)
        self.connectRef(self.settings["upvrefarray"], self.upv_cns, True)

    def connect_orientCns(self):
        """Connection with ori cns

        Connection definition using orientation constraint.

        """

        self.parent.addChild(self.root)

        refArray = self.settings["ikrefarray"]

        if refArray:
            ref_names = self.get_valid_ref_list(refArray.split(","))
            if len(ref_names) == 1:
                ref = self.rig.findRelative(ref_names[0])
                pm.parent(self.ik_cns, ref)
            else:
                ref = []
                for ref_name in ref_names:
                    ref.append(self.rig.findRelative(ref_name))

                ref.append(self.ik_cns)
                cns_node = pm.orientConstraint(*ref, maintainOffset=True)
                cns_attr_names = pm.orientConstraint(
                    cns_node, query=True, weightAliasList=True
                )
                cns_attr = []
                for cname in cns_attr_names:
                    cns_attr.append("{}.{}".format(cns_node, cname))

                for i, attr in enumerate(cns_attr):
                    pm.setAttr(attr, 1.0)
                    node_name = pm.createNode("condition")
                    pm.connectAttr(self.ikref_att, node_name + ".firstTerm")
                    pm.setAttr(node_name + ".secondTerm", i)
                    pm.setAttr(node_name + ".operation", 0)
                    pm.setAttr(node_name + ".colorIfTrueR", 1)
                    pm.setAttr(node_name + ".colorIfFalseR", 0)
                    pm.connectAttr(node_name + ".outColorR", attr)

    def connect_orientCns2(self):
        """Connection with ori cns

        Connection definition using orientation constraint.
        maintainOffset flag is not working correctly.
        In connect_orientCns2 we add an extra transform as reference to avoid
        offsets

        """

        self.parent.addChild(self.root)
        mtx = self.ik_cns.getMatrix(worldSpace=True)

        refArray = self.settings["ikrefarray"]

        if refArray:
            ref_names = self.get_valid_ref_list(refArray.split(","))
            if len(ref_names) == 1:
                ref = self.rig.findRelative(ref_names[0])
                pm.parent(self.ik_cns, ref)
            else:
                ref = []
                for ref_name in ref_names:
                    ref.append(self.rig.findRelative(ref_name))

                # ref.append(self.ik_cns)
                ref_off = []
                for r in ref:
                    cns_off = primitive.addTransform(
                        r,
                        r.name() + "_offset",
                        m=mtx,
                    )
                    ref_off.append(cns_off)
                ref_off.append(self.ik_cns)
                cns_node = pm.orientConstraint(*ref_off, maintainOffset=False)
                cns_attr_names = pm.orientConstraint(
                    cns_node, query=True, weightAliasList=True
                )
                cns_attr = []
                for cname in cns_attr_names:
                    cns_attr.append("{}.{}".format(cns_node, cname))

                for i, attr in enumerate(cns_attr):
                    pm.setAttr(attr, 1.0)
                    node_name = pm.createNode("condition")
                    pm.connectAttr(self.ikref_att, node_name + ".firstTerm")
                    pm.setAttr(node_name + ".secondTerm", i)
                    pm.setAttr(node_name + ".operation", 0)
                    pm.setAttr(node_name + ".colorIfTrueR", 1)
                    pm.setAttr(node_name + ".colorIfFalseR", 0)
                    pm.connectAttr(node_name + ".outColorR", attr)

    def connect_standardWithSimpleIkRef(self):
        """Standard connection definition with simple IK reference."""

        self.parent.addChild(self.root)

        # Set the Ik Reference
        self.connectRef(self.settings["ikrefarray"], self.ik_cns)

    def connect_averageParentCns(self):
        """
        Connection definition using average parent constraint.
        """
        self.parent.addChild(self.root)

        refArray = self.settings["ikrefarray"]

        if refArray:
            ref_names = self.get_valid_ref_list(refArray.split(","))
            if len(ref_names) == 1:
                ref = self.rig.findRelative(ref_names[0])
                pm.parent(self.ik_cns, ref)
            else:
                ref = []
                for ref_name in ref_names:
                    ref.append(self.rig.findRelative(ref_name))

                ref.append(self.ik_cns)
                cns_node = pm.parentConstraint(*ref, maintainOffset=True)
                cns_attr = pm.parentConstraint(
                    cns_node, query=True, weightAliasList=True
                )

                for i, attr in enumerate(cns_attr):
                    pm.setAttr(attr, 1.0)

    def connectRef(
        self,
        refArray,
        cns_obj,
        upVAttr=None,
        init_refNames=False,
        st=None,
        sr=None,
    ):
        """Connect the cns_obj to a multiple object using parentConstraint.

        Args:
            refArray (list of dagNode): List of driver objects
            cns_obj (dagNode): The driven object.
            upVAttr (bool): Set if the ref Array is for IK or Up vector
            init_refNames (bool, optional): Nice name for the references menu
            st (None, optional): skipTranslate
            sr (None, optional): skipRotate
        """
        if refArray:
            # mtx = cns_obj.getMatrix(worldSpace=True)
            if upVAttr:
                relatives_map = self.relatives_map_upv
            else:
                relatives_map = self.relatives_map

            if upVAttr and not init_refNames:
                # we only can perform name validation if the init_refnames are
                # provided in a separated list. This check ensures backwards
                # copatibility
                ref_names = refArray.split(",")
            else:
                ref_names = self.get_valid_ref_list(refArray.split(","))

            if not ref_names:
                # return if the not ref_names list
                return
            elif len(ref_names) == 1:
                ref = self.rig.findRelative(ref_names[0], relatives_map)
                pm.parent(cns_obj, ref)
            else:
                ref = []
                for ref_name in ref_names:
                    # handle special case for full mirror behavior negating
                    # scaleY axis to -1
                    # this is needed because parent constraining  doesn't handle
                    # scaling and the maintain offset will not work properly
                    if cns_obj.sy.get() < 0:
                        original_trans = self.rig.findRelative(
                            ref_name, relatives_map
                        )
                        ref_trans_name = (
                            cns_obj.getName()
                            + "_"
                            + original_trans.getName()
                            + "_space_ref"
                        )

                        # check if already exist - use cmds for faster lookup
                        if cmds.objExists(ref_trans_name):
                            ref_trans = pm.PyNode(ref_trans_name)
                        else:
                            ref_trans = primitive.addTransform(
                                original_trans,
                                ref_trans_name,
                            )
                            transform.matchWorldTransform(cns_obj, ref_trans)
                        ref.append(ref_trans)
                    else:
                        ref.append(
                            self.rig.findRelative(ref_name, relatives_map)
                        )
                ref.append(cns_obj)
                if not st:
                    st = "none"
                if not sr:
                    sr = "none"
                cns_node = pm.parentConstraint(
                    *ref, maintainOffset=True, st=st
                )
                cns_attr_names = pm.parentConstraint(
                    cns_node, query=True, weightAliasList=True
                )
                cns_attr = []
                for cname in cns_attr_names:
                    cns_attr.append("{}.{}".format(cns_node, cname))

                # ensure there is not offset generated with the constraint
                # due to the precision rounding
                # if mtx != cns_obj.getMatrix(worldSpace=True):
                #     cns_off = primitive.addTransform(
                #         cns_obj.getParent(),
                #         cns_obj.name() + "_offset",
                #         m=mtx,
                #     )
                #     attribute.move_input_connections(
                #         cns_obj, cns_off, type_filter="parentConstraint"
                #     )
                #     attribute.move_output_connections(
                #         cns_obj, cns_off, type_filter="parentConstraint"
                #     )
                #     pm.parent(cns_obj, cns_off)
                #     pm.parent(cns_node, cns_off)
                #     cns_obj.setMatrix(mtx, worldSpace=True)
                # check if the ref Array is for IK or Up vector
                try:
                    if upVAttr:
                        oAttr = self.upvref_att
                    else:
                        oAttr = self.ikref_att

                except AttributeError:
                    oAttr = None

                if oAttr:
                    for i, attr in enumerate(cns_attr):
                        node_name = pm.createNode("condition")
                        pm.connectAttr(oAttr, node_name + ".firstTerm")
                        pm.setAttr(node_name + ".secondTerm", i)
                        pm.setAttr(node_name + ".operation", 0)
                        pm.setAttr(node_name + ".colorIfTrueR", 1)
                        pm.setAttr(node_name + ".colorIfFalseR", 0)
                        pm.connectAttr(node_name + ".outColorR", attr)
                return ref

    def connectRef2(
        self,
        refArray,
        cns_obj,
        in_attr,
        init_ref=False,
        skipTranslate=False,
        init_refNames=False,
    ):
        """Connect the cns_obj to a multiple object using parentConstraint.

        Args:
            refArray (string): List of driver objects divided by ",".
            cns_obj (dagNode): The driven object.
            in_attr (attr): The attribute to connect the switch
            init_ref (list of dagNode): Set the initial default ref connections
            skipTranslate (bool): if True will skip the translation connections
            init_refNames (list of str, optional): Set initial default names
                for the initial default connections

        """
        if refArray:
            # mtx = cns_obj.getMatrix(worldSpace=True)
            if init_refNames:
                # we only can perform name validation if the init_refnames are
                # provided in a separated list. This check ensures backwards
                # copatibility
                ref_names = self.get_valid_ref_list(refArray.split(","))
            else:
                ref_names = refArray.split(",")
            if len(ref_names) == 1 and not init_refNames:
                ref = self.rig.findRelative(ref_names[0])
                pm.parent(cns_obj, ref)
            else:
                if init_refNames:
                    ref_names = ref_names + init_refNames
                ref = []
                for ref_name in ref_names:
                    rrn = self.rig.findRelative(ref_name)
                    rgn = self.rig.findRelative("return the global ctl")
                    if rrn != rgn:
                        ref.append(self.rig.findRelative(ref_name))
                if init_ref:
                    ref = init_ref + ref
                ref.append(cns_obj)
                if skipTranslate:
                    cns_node = pm.parentConstraint(
                        *ref,
                        maintainOffset=True,
                        skipTranslate=["x", "y", "z"]
                    )
                else:
                    cns_node = pm.parentConstraint(*ref, maintainOffset=True)
                cns_attr_names = pm.parentConstraint(
                    cns_node, query=True, weightAliasList=True
                )
                cns_attr = []
                for cname in cns_attr_names:
                    cns_attr.append("{}.{}".format(cns_node, cname))

                # ensure there is not offset generated with the constraint
                # due to the precision rounding
                # if mtx != cns_obj.getMatrix(worldSpace=True):
                #     cns_off = primitive.addTransform(
                #         cns_obj.getParent(),
                #         cns_obj.name() + "_offset",
                #         m=mtx,
                #     )
                #     attribute.move_input_connections(
                #         cns_obj, cns_off, type_filter="parentConstraint"
                #     )
                #     attribute.move_output_connections(
                #         cns_obj, cns_off, type_filter="parentConstraint"
                #     )
                #     pm.parent(cns_obj, cns_off)
                #     pm.parent(cns_node, cns_off)
                #     cns_obj.setMatrix(mtx, worldSpace=True)

                for i, attr in enumerate(cns_attr):
                    node_name = pm.createNode("condition")
                    pm.connectAttr(in_attr, node_name + ".firstTerm")
                    pm.setAttr(node_name + ".secondTerm", i)
                    pm.setAttr(node_name + ".operation", 0)
                    pm.setAttr(node_name + ".colorIfTrueR", 1)
                    pm.setAttr(node_name + ".colorIfFalseR", 0)
                    pm.connectAttr(node_name + ".outColorR", attr)

                return ref

    def connect_standardWithRotRef(self, refArray, cns_obj):
        """Connect the cns_obj to a multiple object

        Connect the cns_obj to a multiple object using parentConstraint, but
        skipping translation connection.

        Args:
            refArray (list of dagNode): List of driver objects
            cns_obj (dagNode): The driven object.

        """
        if refArray:
            ref_names = self.get_valid_ref_list(refArray.split(","))
            if len(ref_names) >= 1:
                ref = []
                for ref_name in ref_names:
                    ref.append(self.rig.findRelative(ref_name))

                ref.append(cns_obj)
                cns_node = pm.parentConstraint(
                    *ref, maintainOffset=True, skipTranslate=["x", "y", "z"]
                )
                cns_attr_names = pm.parentConstraint(
                    cns_node, query=True, weightAliasList=True
                )
                cns_attr = []
                for cname in cns_attr_names:
                    cns_attr.append("{}.{}".format(cns_node, cname))
                for i, attr in enumerate(cns_attr):
                    node_name = pm.createNode("condition")
                    pm.connectAttr(self.ref_att, node_name + ".firstTerm")
                    pm.setAttr(node_name + ".secondTerm", i)
                    pm.setAttr(node_name + ".operation", 0)
                    pm.setAttr(node_name + ".colorIfTrueR", 1)
                    pm.setAttr(node_name + ".colorIfFalseR", 0)
                    pm.connectAttr(node_name + ".outColorR", attr)

    def postConnect(self):
        """Post connection actions.

        Note:
            REIMPLEMENT. This method should be reimplemented in each component.

        """
        return

    # =====================================================
    # JOINTS STRUCTURE
    # =====================================================
    def jointStructure(self):
        """Build the Joint structure

        Handle the building of the joint structure, when we select jnt_org
        option.

        """
        # get parent component joint
        if self.settings["useIndex"] and self.parent_comp.jointList:
            try:
                self.active_jnt = self.parent_comp.jointList[
                    self.settings["parentJointIndex"]
                ]
            except Exception:
                pm.displayWarning(
                    "The parent component for: %s don't have "
                    "any joint with the index: %s."
                    % (self.fullName, str(self.settings["parentJointIndex"]))
                )
        else:

            # Inform the user that useIndex ins not possible to use
            if self.settings["useIndex"] and not self.parent_comp.jointList:
                pm.displayWarning(
                    "Parent Component doesn't have joints."
                    " Using last active_jnt. Index parenting omitted"
                )

            parent_name = "none"
            if self.guide.parentComponent is not None:
                parent_name = self.guide.parentComponent.getName(
                    self.guide.parentLocalName
                )

            relative_name = self.rig.getRelativeName(parent_name)

            oParent_comp = self.parent_comp
            while oParent_comp:
                try:
                    self.active_jnt = oParent_comp.jointList[
                        oParent_comp.jointRelatives[relative_name]
                    ]
                    # when we search  in the parent component for a active jnt
                    # we also store it for later retrive
                    self.parent_relative_jnt = self.active_jnt
                    break
                except Exception:
                    if oParent_comp.parent_comp:
                        pgpc = oParent_comp.guide.parentComponent
                        parent_name = pgpc.getName(
                            oParent_comp.guide.parentLocalName
                        )
                        relative_name = oParent_comp.rig.getRelativeName(
                            parent_name
                        )
                    else:
                        pm.displayInfo(
                            "The parent components for: %s don't have joint "
                            "List in any of them use the root off guide."
                            % self.fullName
                        )

                    oParent_comp = oParent_comp.parent_comp

        # Joint creation
        for jpo in self.jnt_pos:

            # NOTE: using a list was a mitake. Adding support for a kwargs dict
            if isinstance(jpo, list):
                if len(jpo) >= 3 and self.options["joint_rig"]:
                    if jpo[2] == "component_jnt_org":
                        newActiveJnt = self.component_jnt_org
                    elif jpo[2] == "parent_relative_jnt":
                        # this option force the active jnt always to the parent
                        # relative jnt.
                        # If None the active jnt will be updated to the latest in
                        # each jnt creation
                        newActiveJnt = self.parent_relative_jnt
                    else:
                        try:
                            # here jpo[2] is also the string name of the jnt inside
                            # the component. IE: "root"
                            newActiveJnt = self.jointList[
                                self.jointRelatives[jpo[2]]
                            ]

                        except Exception:
                            if jpo[2]:
                                pm.displayWarning(
                                    "Joint Structure creation: "
                                    "The object %s can't be found. Joint parent is"
                                    " NONE for %s, from %s"
                                    % (jpo[2], jpo[0], self.fullName)
                                )
                            newActiveJnt = None
                else:
                    newActiveJnt = None
                # Handle the uniform scale
                if len(jpo) >= 4 and self.options["joint_rig"]:
                    uniScale = jpo[3]
                else:
                    uniScale = False

                # TODO: handle rotation offset and vanilla nodes connection
                # handle the matrix node connection

                # Defaults to use Maya multiply Matrix node
                if len(jpo) >= 5 and self.options["joint_rig"]:
                    gearMulMatrix = jpo[4]
                else:
                    gearMulMatrix = False

                self.jointList.append(
                    self.addJoint(
                        jpo[0],
                        jpo[1],
                        newActiveJnt,
                        uniScale,
                        gearMulMatrix=gearMulMatrix,
                    )
                )
            elif isinstance(jpo, dict):
                if "newActiveJnt" in jpo:
                    if jpo["newActiveJnt"] == "component_jnt_org":
                        jpo["newActiveJnt"] = self.component_jnt_org
                    elif jpo["newActiveJnt"] == "parent_relative_jnt":
                        # this option force the active jnt always to the parent
                        # relative jnt.
                        # If None the active jnt will be updated to the latest in
                        # each jnt creation
                        jpo["newActiveJnt"] = self.parent_relative_jnt
                    elif isinstance(jpo["newActiveJnt"], int):
                        jpo["newActiveJnt"] = self.jointList[
                            jpo["newActiveJnt"]
                        ]
                    else:
                        try:
                            # here jpo["newActiveJnt"] is also the string name
                            # of the jnt inside the component. IE: "root"
                            jpo["newActiveJnt"] = self.jointList[
                                self.jointRelatives[jpo["newActiveJnt"]]
                            ]

                        except Exception:
                            if jpo["newActiveJnt"]:
                                pm.displayWarning(
                                    "Joint Structure creation: "
                                    "The object %s can't be found. Joint parent is"
                                    " NONE for %s, from %s"
                                    % (
                                        jpo["newActiveJnt"],
                                        jpo["obj"],
                                        self.fullName,
                                    )
                                )
                            jpo["newActiveJnt"] = None

                self.jointList.append(self.addJoint(**jpo))

        # Set joint radius using cmds for better performance
        radiusValue = self.options["joint_radius"]
        for jnt in self.jointList:
            cmds.setAttr(f"{jnt.name()}.radius", radiusValue)

    # =====================================================
    # FINALIZE
    # =====================================================
    def finalize(self):
        """Finalize and clean the rig builing."""
        # locking the attributes for all the ctl parents that are not ctl
        # itself.
        for t in self.transform2Lock:
            attribute.lockAttribute(t)

        return

    def postScript(self):
        """
        Execute an external .py file, after the rig building.
        """

        return

    def collect_build_data(self):

        # helper function to convert the transforms obj to a str name
        def store_relative_names(relative_dict):
            result = {}
            for key, relative in relative_dict.items():
                if isinstance(relative, pm.nodetypes.Transform):
                    result[key] = relative.name()
                else:
                    result[key] = None
            return result

        self.build_data["FullName"] = self.fullName
        self.build_data["Name"] = self.name
        self.build_data["Type"] = self.guide.type
        self.build_data["Side"] = self.side
        self.build_data["Index"] = self.index

        temp_dict = {}
        for k in self.guide.tra:
            temp_dict[k] = self.guide.tra[k].get()
        self.build_data["guideTransforms"] = temp_dict

        self.build_data["DataContracts"] = []
        self.build_data["Joints"] = []
        self.build_data["Controls"] = []
        self.build_data["Ik"] = []
        self.build_data["Twist"] = []
        self.build_data["Squash"] = []
        self.build_data["Settings"] = self.settings
        settings_dict = self.guide.get_guide_template_dict()
        # print("settings_dict>>>>")
        # print(settings_dict)
        self.build_data["Settings"]["RGB_fk"] = settings_dict["param_values"]["RGB_fk"]
        self.build_data["Settings"]["RGB_ik"] = settings_dict["param_values"]["RGB_ik"]
        # print('self.build_data["Settings"]')
        # print(self.build_data["Settings"])
        # print(self.settings)
        self.build_data["relatives"] = store_relative_names(self.relatives)
        self.build_data["jointRelatives"] = self.jointRelatives
        self.build_data["controlRelatives"] = store_relative_names(
            self.controlRelatives
        )
        self.build_data["aliasRelatives"] = self.aliasRelatives
        if self.guide.parentComponent:
            self.build_data[
                "parent_fullName"
            ] = self.guide.parentComponent.fullName
            self.build_data["parent_localName"] = self.guide.parentLocalName
        else:
            self.build_data["parent_fullName"] = None
            self.build_data["parent_localName"] = None

        # joints
        for j in self.jointList:
            jnt_dict = {}
            jnt_dict["Name"] = j.name()

            # if j.hasAttr("comp_type"):
            #     jnt_dict["comp_type"] = j.comp_type.get()
            # else:
            #     jnt_dict["comp_type"] = ""

            jnt_dict.update(self.gather_transform_info(j))
            self.build_data["Joints"].append(jnt_dict)
            if j.hasAttr("data_contracts"):
                for dc in j.data_contracts.get().split(","):
                    # check if the Data contract indentifier type is a valid
                    # data contract
                    if dc not in self.build_data:
                        pm.displayWarning(
                            "{} is not a valid Data Contract Key".format(dc)
                        )
                        continue
                    # populate component active data contracts list
                    if dc not in self.build_data["DataContracts"]:
                        self.build_data["DataContracts"].append(dc)
                    # add joint Name to the corresponding data contract list
                    self.build_data[dc].append(j.name())

        # controls
        for c in self.controlers:
            ctl_dict = {}
            ctl_dict["Name"] = c.name()
            ctl_dict["Role"] = c.ctl_role.get()
            ctl_dict["Shape"] = curve.collect_curve_data(c)
            ctl_dict.update(self.gather_transform_info(c))
            self.build_data["Controls"].append(ctl_dict)

    def gather_transform_info(self, obj):
        """Gather the world transfromation information for Rotation and
        Translation

        Args:
            obj_list (PyNode Dag list): List of transforms to gather the info

        Returns:
            dict: Rotation and translation dict
        """
        trans_info = {}

        world_position = obj.getTranslation(space="world")
        temp_dict_position = {}
        temp_dict_position["x"] = world_position.x
        temp_dict_position["y"] = world_position.y
        temp_dict_position["z"] = world_position.z
        trans_info["WorldPosition"] = temp_dict_position

        temp_dict_rotation = {}
        world_rotation = obj.getRotation(space="world")
        temp_dict_rotation["x"] = world_rotation.x
        temp_dict_rotation["y"] = world_rotation.y
        temp_dict_rotation["z"] = world_rotation.z
        trans_info["WorldRotation"] = temp_dict_rotation

        world_matrix = obj.getMatrix(worldSpace=True)
        tm = pm.datatypes.TransformationMatrix(world_matrix)
        qw = tm.getRotationQuaternion()
        trans_info["QuaternionWorldRotation"] = qw

        trans_info["RotationOrder"] = obj.ro.get()

        return trans_info

    # =====================================================
    # MISC
    # =====================================================

    def getName(
        self,
        name="",
        side=None,
        rule=None,
        ext=None,
        letter_case=0,
        short_name=False,
    ):
        """Return the name for component element

        Args:
            name (str): The name to concatenate to component name. (Optional)
            side (str): The side (Optional).
            rule (None, optional): Description
            ext (None, optional): Description
            letter_case (int, optional): Description
            short_name (bool, optional): will return the short name without
                side and index

        Returns:
            str: The name.

        """

        if side is None:
            side = self.side

        name = str(name)

        if rule and ext:

            # get side
            if ext == "jnt":
                if side == "L":
                    side = self.options["side_joint_left_name"]
                elif side == "R":
                    side = self.options["side_joint_right_name"]
                elif side == "C":
                    side = self.options["side_joint_center_name"]
            elif ext == "ctl":
                if side == "L":
                    side = self.options["side_left_name"]
                elif side == "R":
                    side = self.options["side_right_name"]
                elif side == "C":
                    side = self.options["side_center_name"]

            # get extension
            if ext == "jnt":
                ext = self.options["joint_name_ext"]
                padding = self.options["joint_index_padding"]
            elif ext == "ctl":
                ext = self.options["ctl_name_ext"]
                padding = self.options["ctl_index_padding"]

            # description letter case
            name = naming.letter_case_solve(name, letter_case)

            values = {
                "component": self.name,
                "side": side,
                "index": str(self.index),
                "padding": padding,
                "description": name,
                "extension": ext,
            }
            return naming.name_solve(rule, values)
        else:
            if name:
                if short_name:
                    return "_".join([self.name, name])
                else:
                    return "_".join([self.name, side + str(self.index), name])
            else:
                return self.fullName

    def getAttrName(self, longName):
        """Get the attribute name depending of the prefix configuration

        Args:
            longName (str): Long Name

        Returns:
            str: attribute name
        """
        if self.options["attrPrefixName"]:
            return self.getName(longName, short_name=True)
        else:

            return self.getCompName(longName)

    def getCustomJointName(self, jointIndex):
        """Get user-specified custom name for a joint.

        Args:
            jointIndex (int): Joint within the component.

        Returns:
            str: User-specified name if one exists. Otherwise empty string.

        """
        names = self.guide.values["joint_names"].split(",")
        if len(names) > jointIndex:
            return names[jointIndex].strip()
        return ""

    def getCompName(self, name=""):
        """Return the component type name

        Args:
            name (str): The name to concatenate to the component name.
        Returns:
            str: The name.

        """

        return "_".join([self.guide.compName, name])

    # =====================================================
    # PROPERTIES
    # =====================================================

    def getFullName(self):
        """return the fullname of the component"""
        return self.guide.fullName

    def getType(self):
        """return the type of the component"""
        return self.guide.type

    fullName = property(getFullName)
    type = property(getType)


# Backwards compatibility alias
MainComponent = Main
