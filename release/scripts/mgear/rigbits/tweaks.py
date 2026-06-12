"""Rigbits tweaks rig module"""

import mgear.pymaya as pm
from mgear.pymaya import datatypes
from maya import cmds

from mgear.core import skin, primitive, icon, transform, attribute
from mgear.core import applyop
from mgear.core import meshNavigation as mesh_navi
from mgear.rigbits import rivet, blendShapes
from mgear.core import node


def resetJntLocalSRT(jnt):
    """Reset the local SRT and jointOrient of a joint

    Args:
        jnt (joint): The joint to reset the local SRT
    """
    for axis in "XYZ":
        pm.setAttr(jnt + ".jointOrient" + axis, 0)
        pm.setAttr(jnt + ".rotate" + axis, 0)
        pm.setAttr(jnt + ".translate" + axis, 0)


def pre_bind_matrix_connect(mesh, joint, jointBase):
    """Connect the pre bind matrix of the skin cluseter to the joint parent.
    This create the offset in the  deformation to avoid double transformation

    Args:
        mesh (PyNode): Mesh object with the tweak skin cluster
        joint (PyNode): Tweak joint
        jointBase (PyNode): Tweak joint parent
    """
    # magic of doritos connection
    skinCluster = skin.getSkinCluster(mesh)
    if not skinCluster:
        # apply initial skincluster
        skinCluster = pm.skinCluster(
            joint, mesh, tsb=True, nw=2, n="%s_skinCluster" % mesh.name()
        )
    else:
        try:
            # we try to add the joint to the skin cluster. Will fail if is
            # already in the skin cluster
            pm.skinCluster(skinCluster, e=True, ai=joint, lw=True, wt=0)
        except Exception:
            pm.displayInfo(
                "The Joint: %s  is already in the %s."
                % (joint.name(), skinCluster.name())
            )
            pass
    cn = joint.listConnections(p=True, type="skinCluster")
    for x in cn:
        if x.type() == "matrix":
            if x.name().split(".")[0] == skinCluster.name():
                # We force to avoid errors in case the joint is already
                # connected
                pm.connectAttr(
                    jointBase + ".worldInverseMatrix[0]",
                    skinCluster + ".bindPreMatrix[" + str(x.index()) + "]",
                    f=True,
                )


def createJntTweak(mesh, jntParent, ctlParent):
    """Create a joint tweak

    Args:
        mesh (mesh): The object to deform with the tweak
        jntParent (dagNode): The parent for the new joint
        ctlParent (dagNode): The parent for the control.
    """
    if not isinstance(mesh, list):
        mesh = [mesh]

    name = "_".join(jntParent.name().split("_")[:3])

    # create joints
    jointBase = primitive.addJoint(
        jntParent,
        name + "_tweak_jnt_lvl",
        jntParent.getMatrix(worldSpace=True),
    )
    resetJntLocalSRT(jointBase)
    joint = primitive.addJoint(
        jointBase, name + "_tweak_jnt", jntParent.getMatrix(worldSpace=True)
    )
    resetJntLocalSRT(joint)

    # hiding joint base by changing the draw mode
    # pm.setAttr(jointBase+".drawStyle", 2)

    try:
        defSet = pm.PyNode("rig_deformers_grp")
    except TypeError:
        pm.sets(n="rig_deformers_grp")
        defSet = pm.PyNode("rig_deformers_grp")
    pm.sets(defSet, add=joint)

    controlType = "circle"
    iconBase = icon.create(
        ctlParent,
        name + "_base_tweak_ctl",
        ctlParent.getMatrix(worldSpace=True),
        13,
        controlType,
        w=0.8,
        ro=datatypes.Vector(0, 0, 1.5708),
    )

    attribute.addAttribute(iconBase, "isCtl", "bool", keyable=False)

    o_icon = icon.create(
        iconBase,
        name + "_tweak_ctl",
        ctlParent.getMatrix(worldSpace=True),
        17,
        controlType,
        w=0.5,
        ro=datatypes.Vector(0, 0, 1.5708),
    )

    attribute.addAttribute(o_icon, "isCtl", "bool", keyable=False)

    for t in [".translate", ".scale", ".rotate"]:
        pm.connectAttr(iconBase + t, jointBase + t)
        pm.connectAttr(o_icon + t, joint + t)

    # magic of doritos connection
    for m in mesh:
        pre_bind_matrix_connect(m, joint, jointBase)


def createRivetTweak(
    mesh,
    edgePair,
    name,
    parent=None,
    ctlParent=None,
    jntParent=None,
    color=[0, 0, 0],
    size=0.04,
    defSet=None,
    ctlSet=None,
    side=None,
    gearMulMatrix=True,
    attach_rot=False,
    inputMesh=None,
    ctlShape="sphere",
):
    """Create a tweak joint attached to the mesh using a rivet

    Args:
        mesh (mesh): The object to add the tweak
        edgePair (pair list): The edge pair to create the rivet
        name (str): The name for the tweak
        parent (None or dagNode, optional): The parent for the tweak
        jntParent (None or dagNode, optional): The parent for the joints
        ctlParent (None or dagNode, optional): The parent for the tweak control
        color (list, optional): The color for the control
        size (float, optional): Size of the control
        defSet (None or set, optional): Deformer set to add the joints
        ctlSet (None or set, optional): the set to add the controls
        side (None, str): String to set the side. Valid values are L, R or C.
            If the side is not set or the value is not valid, the side will be
            set automatically based on the world position
        gearMulMatrix (bool, optional): If False will use Maya default multiply
            matrix node

    Returns:
        PyNode: The tweak control
    """
    if not inputMesh:
        blendShape = blendShapes.getBlendShape(mesh)
        if blendShape:
            inputMesh = blendShape.inputTarget.listConnections(
                sh=True, t="shape", d=False
            )[0]
        else:
            morph = blendShapes.getMorph(mesh)
            inputMesh = morph.morphTarget.listConnections(
                sh=True, t="shape", d=False
            )[0]

    oRivet = rivet.rivet()
    base = oRivet.create(inputMesh, edgePair[0], edgePair[1], parent)
    # get side
    if not side or side not in ["L", "R", "C"]:
        if base.getTranslation(space="world")[0] < -0.01:
            side = "R"
        elif base.getTranslation(space="world")[0] > 0.01:
            side = "L"
        else:
            side = "C"

    nameSide = name + "_tweak_" + side
    pm.rename(base, nameSide)

    if not ctlParent:
        ctlParent = base
        ctl_parent_tag = None
    else:
        ctl_parent_tag = ctlParent

    # Joints NPO
    npo = pm.PyNode(
        pm.createNode("transform", n=nameSide + "_npo", p=ctlParent, ss=True)
    )
    if attach_rot:
        # npo.setTranslation(base.getTranslation(space="world"), space="world")
        pm.parentConstraint(base, npo, mo=False)
    else:
        pm.pointConstraint(base, npo, mo=False)

    # create joints
    if not jntParent:
        jntParent = npo
        matrix_cnx = False
    else:
        # need extra connection to ensure is moving with th npo, even is
        # not child of npo
        matrix_cnx = True

    jointBase = primitive.addJoint(jntParent, nameSide + "_jnt_lvl")
    joint = primitive.addJoint(jointBase, nameSide + "_jnt")

    # reset axis and invert behaviour
    for axis in "XYZ":
        pm.setAttr(jointBase + ".jointOrient" + axis, 0)
        pm.setAttr(npo + ".translate" + axis, 0)
        # pm.setAttr(jointBase + ".translate" + axis, 0)

    pp = npo.getParent()
    pm.parent(npo, w=True)
    for axis in "xyz":
        npo.attr("r" + axis).set(0)
    if side == "R":
        npo.attr("ry").set(180)
        npo.attr("sz").set(-1)
    pm.parent(npo, pp)

    dm_node = None

    if matrix_cnx:
        mulmat_node = applyop.gear_mulmatrix_op(
            npo + ".worldMatrix", jointBase + ".parentInverseMatrix"
        )
        dm_node = node.createDecomposeMatrixNode(mulmat_node + ".output")
        m = mulmat_node.attr("output").get()
        pm.connectAttr(dm_node + ".outputTranslate", jointBase + ".t")
        pm.connectAttr(dm_node + ".outputRotate", jointBase + ".r")

        # invert negative scaling in Joints. We only inver Z axis, so is
        # the only axis that we are checking
        if dm_node.attr("outputScaleZ").get() < 0:
            mul_nod_invert = node.createMulNode(
                dm_node.attr("outputScaleZ"), -1
            )
            out_val = mul_nod_invert.attr("outputX")
        else:
            out_val = dm_node.attr("outputScaleZ")

        pm.connectAttr(dm_node.attr("outputScaleX"), jointBase + ".sx")
        pm.connectAttr(dm_node.attr("outputScaleY"), jointBase + ".sy")
        pm.connectAttr(out_val, jointBase + ".sz")
        pm.connectAttr(dm_node + ".outputShear", jointBase + ".shear")

        # Segment scale compensate Off to avoid issues with the global
        # scale
        jointBase.setAttr("segmentScaleCompensate", 0)
        joint.setAttr("segmentScaleCompensate", 0)

        jointBase.setAttr("jointOrient", 0, 0, 0)

        # setting the joint orient compensation in order to have clean
        # rotation channels
        jointBase.attr("jointOrientX").set(jointBase.attr("rx").get())
        jointBase.attr("jointOrientY").set(jointBase.attr("ry").get())
        jointBase.attr("jointOrientZ").set(jointBase.attr("rz").get())

        im = m.inverse()

        if gearMulMatrix:
            mul_nod = applyop.gear_mulmatrix_op(
                mulmat_node.attr("output"), im, jointBase, "r"
            )
            dm_node2 = mul_nod.output.listConnections()[0]
        else:
            mul_nod = node.createMultMatrixNode(
                mulmat_node.attr("matrixSum"), im, jointBase, "r"
            )
            dm_node2 = mul_nod.matrixSum.listConnections()[0]

        if dm_node.attr("outputScaleZ").get() < 0:
            negateTransformConnection(dm_node2.outputRotate, jointBase.rotate)

    else:
        resetJntLocalSRT(jointBase)

    # hidding joint base by changing the draw mode
    pm.setAttr(jointBase + ".drawStyle", 2)
    if not defSet:
        try:
            defSet = pm.PyNode("rig_deformers_grp")
        except TypeError:
            pm.sets(n="rig_deformers_grp", empty=True)
            defSet = pm.PyNode("rig_deformers_grp")
    pm.sets(defSet, add=joint)

    controlType = ctlShape
    o_icon = icon.create(
        npo,
        nameSide + "_ctl",
        datatypes.Matrix(),
        color,
        controlType,
        w=size,
        h=size,
        d=size,
    )

    attribute.addAttribute(o_icon, "isCtl", "bool", keyable=False)

    transform.resetTransform(o_icon)
    if dm_node and dm_node.attr("outputScaleZ").get() < 0:
        pm.connectAttr(o_icon.scale, joint.scale)
        negateTransformConnection(o_icon.rotate, joint.rotate)
        negateTransformConnection(
            o_icon.translate, joint.translate, [1, 1, -1]
        )

    else:
        for t in [".translate", ".scale", ".rotate"]:
            pm.connectAttr(o_icon + t, joint + t)

    # create the attributes to handlde mirror and symetrical pose
    attribute.addAttribute(
        o_icon, "invTx", "bool", 0, keyable=False, niceName="Invert Mirror TX"
    )
    attribute.addAttribute(
        o_icon, "invTy", "bool", 0, keyable=False, niceName="Invert Mirror TY"
    )
    attribute.addAttribute(
        o_icon, "invTz", "bool", 0, keyable=False, niceName="Invert Mirror TZ"
    )
    attribute.addAttribute(
        o_icon, "invRx", "bool", 0, keyable=False, niceName="Invert Mirror RX"
    )
    attribute.addAttribute(
        o_icon, "invRy", "bool", 0, keyable=False, niceName="Invert Mirror RY"
    )
    attribute.addAttribute(
        o_icon, "invRz", "bool", 0, keyable=False, niceName="Invert Mirror RZ"
    )
    attribute.addAttribute(
        o_icon, "invSx", "bool", 0, keyable=False, niceName="Invert Mirror SX"
    )
    attribute.addAttribute(
        o_icon, "invSy", "bool", 0, keyable=False, niceName="Invert Mirror SY"
    )
    attribute.addAttribute(
        o_icon, "invSz", "bool", 0, keyable=False, niceName="Invert Mirror SZ"
    )

    # magic of doritos connection
    pre_bind_matrix_connect(mesh, joint, jointBase)

    # add control tag
    node.add_controller_tag(o_icon, ctl_parent_tag)

    if not ctlSet:
        try:
            ctlSet = pm.PyNode("rig_controllers_grp")
        except TypeError:
            pm.sets(n="rig_controllers_grp", empty=True)
            ctlSet = pm.PyNode("rig_controllers_grp")
    pm.sets(ctlSet, add=o_icon)

    return o_icon


def createMirrorRivetTweak(
    mesh,
    edgePair,
    name,
    parent=None,
    ctlParent=None,
    jntParent=None,
    color=[0, 0, 0],
    size=0.04,
    defSet=None,
    ctlSet=None,
    side=None,
    gearMulMatrix=True,
    attach_rot=False,
    inputMesh=None,
    ctlShape="sphere",
):
    """Create a tweak joint attached to the mesh using a rivet.
    The edge pair will be used to find the mirror position on the mesh

    Args:
        mesh (mesh): The object to add the tweak
        edgePair (pair list): The edge pair to create the rivet
        name (str): The name for the tweak
        parent (None or dagNode, optional): The parent for the tweak
        ctlParent (None or dagNode, optional): The parent for the tweak control
        jntParent (None or dagNode, optional): The parent for the joints
        color (list, optional): The color for the control
        size (float, optional): Size of the control
        defSet (None or set, optional): Deformer set to add the joints
        ctlSet (None or set, optional): the set to add the controls
        side (None, str): String to set the side. Valid values are L, R or C.
            If the side is not set or the value is not valid, the side will be
            set automatically based on the world position
        gearMulMatrix (bool, optional): If False will use Maya default multiply
            matrix node

    Returns:
        PyNode: The tweak control
    """
    if not inputMesh:
        navi_mesh = mesh
    else:
        navi_mesh = inputMesh
    mirror_edge_pair = [
        mesh_navi.find_mirror_edge(navi_mesh, edgePair[1]).index(),
        mesh_navi.find_mirror_edge(navi_mesh, edgePair[0]).index(),
    ]
    return createRivetTweak(
        mesh,
        mirror_edge_pair,
        name,
        parent,
        ctlParent,
        jntParent,
        color,
        size,
        defSet,
        ctlSet,
        side,
        gearMulMatrix,
        attach_rot,
        inputMesh,
        ctlShape,
    )


def createRivetTweakFromList(
    mesh,
    edgePairList,
    name,
    parent=None,
    ctlParent=None,
    jntParent=None,
    color=[0, 0, 0],
    size=0.04,
    defSet=None,
    ctlSet=None,
    side=None,
    mirror=False,
    mParent=None,
    mCtlParent=None,
    mjntParent=None,
    mColor=None,
    gearMulMatrix=True,
    attach_rot=False,
    inputMesh=None,
    ctlShape="sphere",
):
    """Create multiple rivet tweaks from a list of edge pairs

    Args:
        mesh (mesh): The object to add the tweak
        edgePairList (list of list): The edge pair list of list
        name (str): The name for the tweak
        parent (None or dagNode, optional): The parent for the tweak
        ctlParent (None or dagNode, optional): The parent for the tweak control
        jntParent (None or dagNode, optional): The parent for the joints
        color (list, optional): The color for the control
        size (float, optional): Size of the control
        defSet (None or set, optional): Deformer set to add the joints
        ctlSet (None or set, optional): the set to add the controls
        side (None, str): String to set the side. Valid values are L, R or C.
            If the side is not set or the value is not valid, the side will be
            set automatically based on the world position
        mirror (bool, optional): Create the mirror tweak on X axis symmetry
        mParent (None, optional): Mirror tweak parent, if None will use
            parent arg
        mjntParent (None, optional): Mirror  parent joint, if None will use
            jntParent arg
        mCtlParent (None, optional): Mirror ctl parent, if None will use
            ctlParent arg
        mColor (None, optional): Mirror controls color, if None will color arg
        gearMulMatrix (bool, optional): If False will use Maya default multiply
            matrix node

    Returns:
        TYPE: Description
    """
    if not mParent:
        mParent = parent
    if not mCtlParent:
        mCtlParent = ctlParent
    if not mColor:
        mColor = color
    if not mjntParent:
        mjntParent = jntParent

    ctlList = []
    for i, pair in enumerate(edgePairList):
        ctl = createRivetTweak(
            mesh,
            [pair[0], pair[1]],
            name + str(i).zfill(3),
            parent=parent,
            ctlParent=ctlParent,
            jntParent=jntParent,
            color=color,
            size=size,
            defSet=defSet,
            ctlSet=ctlSet,
            side=side,
            gearMulMatrix=gearMulMatrix,
            attach_rot=attach_rot,
            inputMesh=inputMesh,
            ctlShape=ctlShape,
        )
        ctlList.append(ctl)
        if mirror:
            m_ctl = createMirrorRivetTweak(
                mesh,
                [pair[0], pair[1]],
                name + str(i).zfill(3),
                parent=mParent,
                ctlParent=mCtlParent,
                jntParent=mjntParent,
                color=mColor,
                size=size,
                defSet=defSet,
                ctlSet=ctlSet,
                side=side,
                gearMulMatrix=gearMulMatrix,
                attach_rot=attach_rot,
                inputMesh=inputMesh,
                ctlShape=ctlShape,
            )
            ctlList.append(m_ctl)

    return ctlList


def createRivetTweakLayer(
    layerMesh,
    bst,
    edgePairList,
    name,
    parent=None,
    ctlParent=None,
    jntParent=None,
    color=[0, 0, 0],
    size=0.04,
    defSet=None,
    ctlSet=None,
    side=None,
    mirror=False,
    mParent=None,
    mCtlParent=None,
    mjntParent=None,
    mColor=None,
    gearMulMatrix=True,
    static_jnt=None,
    attach_rot=False,
    inputMesh=None,
    ctlShape="sphere",
):
    """Create a rivet tweak layer setup

    Args:
        layerMesh (mesh): The tweak layer mesh
        bst (mesh): The mesh blendshape target
        edgePairList (list of list): The edge pair list of list
        name (str): The name for the tweak
        parent (None or dagNode, optional): The parent for the tweak
        jntParent (None or dagNode, optional): The parent for the joints
        ctlParent (None or dagNode, optional): The parent for the tweak control
        color (list, optional): The color for the control
        size (float, optional): Size of the control
        defSet (None or set, optional): Deformer set to add the joints
        ctlSet (None or set, optional): the set to add the controls
        side (None, str): String to set the side. Valid values are L, R or C.
            If the side is not set or the value is not valid, the side will be
            set automatically based on the world position
        mirror (bool, optional): Create the mirror tweak on X axis symmetry
        mParent (None, optional): Mirror tweak parent, if None will use
            parent arg
        mjntParent (None, optional): Mirror  parent joint, if None will use
            jntParent arg
        mCtlParent (None, optional): Mirror ctl parent, if None will use
            ctlParent arg
        mColor (None, optional): Mirror controls color, if None will color arg
        gearMulMatrix (bool, optional): If False will use Maya default multiply
            matrix node
        static_jnt (dagNode, optional): Static joint for the setup
    """

    # Apply blendshape from blendshapes layer mesh
    blendShapes.connectWithBlendshape(layerMesh, bst)

    # create static joint

    if not static_jnt:
        if pm.objExists("static_jnt") is not True:
            static_jnt = primitive.addJoint(
                parent, "static_jnt", m=datatypes.Matrix(), vis=True
            )
        else:
            static_jnt = pm.PyNode("static_jnt")

    # apply initial skincluster
    pm.skinCluster(
        static_jnt,
        layerMesh,
        tsb=True,
        nw=2,
        n="%s_skinCluster" % layerMesh.name(),
    )

    # create doritos
    if not mParent:
        mParent = parent
    if not mCtlParent:
        mCtlParent = ctlParent
    if not mColor:
        mColor = color
    if not mjntParent:
        mjntParent = jntParent

    createRivetTweakFromList(
        layerMesh,
        edgePairList,
        name,
        parent=parent,
        ctlParent=ctlParent,
        jntParent=jntParent,
        color=color,
        size=size,
        defSet=defSet,
        ctlSet=ctlSet,
        side=side,
        mirror=mirror,
        mParent=mParent,
        mCtlParent=mCtlParent,
        mjntParent=mjntParent,
        mColor=mColor,
        gearMulMatrix=gearMulMatrix,
        attach_rot=attach_rot,
        inputMesh=inputMesh,
        ctlShape=ctlShape,
    )


# Helpers


def edgePairList(log=True):
    """Print and return a list of edge pairs to be use with
    createRivetTweakLayer and createRivetTweakFromList

    Returns:
        list: list of edge pairs
    """
    edge = pm.ls(os=True, fl=True)
    edgePairList = []
    for i in range(0, len(edge), 2):
        a = edge[i].index()
        b = edge[i + 1].index()
        edgePairList.append([a, b])
    if log:
        print(edgePairList)
    return edgePairList


def negateTransformConnection(in_rot, out_rot, neg_axis=[-1, -1, 1]):
    neg_rot_node = pm.createNode("multiplyDivide")
    pm.setAttr(neg_rot_node + ".operation", 1)
    pm.connectAttr(in_rot, neg_rot_node + ".input1", f=True)
    for v, axis in zip(neg_axis, "XYZ"):
        pm.setAttr(neg_rot_node + ".input2" + axis, v)
    pm.connectAttr(neg_rot_node + ".output", out_rot, f=True)


# Proximity Tweak


def create_proximity_tweak(
    mesh,
    edgePair,
    name,
    parent=None,
    ctlParent=None,
    jntParent=None,
    color=[0, 0, 0],
    size=0.04,
    defSet=None,
    ctlSet=None,
    side=None,
    gearMulMatrix=True,
    attach_rot=False,
    inputMesh=None,
    ctlShape="sphere",
    existing_pin=None,
):
    """Create a tweak joint attached to the mesh using a proximity pin

    Args:
        mesh (mesh): The object to add the tweak
        edgePair (pair list): The edge pair to create the proximity pin
        name (str): The name for the tweak
        parent (None or dagNode, optional): The parent for the tweak
        ctlParent (None or dagNode, optional): The parent for the tweak control
        jntParent (None or dagNode, optional): The parent for the joints
        color (list, optional): The color for the control
        size (float, optional): Size of the control
        defSet (None or set, optional): Deformer set to add the joints
        ctlSet (None or set, optional): the set to add the controls
        side (None, str): String to set the side. Valid values are L, R or C.
            If the side is not set or the value is not valid, the side will be
            set automatically based on the world position
        gearMulMatrix (bool, optional): If False will use Maya default multiply
            matrix node
        attach_rot (bool, optional): Description
        inputMesh (None, optional): Description
        ctlShape (str, optional): Description
        existing_pin (None, optional): Description

    Returns:
        list: o_icon and pin node

    """
    if not inputMesh:
        blendShape = blendShapes.getBlendShape(mesh)
        if blendShape:
            inputMesh = blendShape.inputTarget.listConnections(
                sh=True, t="shape", d=False
            )[0]
        else:
            morph = blendShapes.getMorph(mesh)
            inputMesh = morph.morphTarget.listConnections(
                sh=True, t="shape", d=False
            )[0]

    # get edge center
    mesh_dag_path = mesh_navi.get_mesh_dag_path(inputMesh)
    center_position = mesh_navi.get_edge_center(
        mesh_dag_path, [edgePair[0], edgePair[1]]
    )

    # in_trans
    in_trans = pm.spaceLocator(name="inTrans_tempName")[0]
    pm.xform(
        in_trans,
        translation=(center_position.x, center_position.y, center_position.z),
        worldSpace=True,
    )
    pm.parent(in_trans, parent)

    # tweak base
    base, pin = applyop.create_proximity_constraint(
        inputMesh, in_trans, existing_pin=existing_pin
    )
    pm.parent(base, parent)

    # get side
    if not side or side not in ["L", "R", "C"]:
        if base.getTranslation(space="world")[0] < -0.01:
            side = "R"
        elif base.getTranslation(space="world")[0] > 0.01:
            side = "L"
        else:
            side = "C"

    nameSide = name + "_tweak_" + side
    pm.rename(base, nameSide)
    pm.rename(in_trans, name + "_inTrans_" + side)

    if not ctlParent:
        ctlParent = base
        ctl_parent_tag = None
    else:
        ctl_parent_tag = ctlParent

    # Joints NPO
    npo = pm.PyNode(
        pm.createNode("transform", n=nameSide + "_npo", p=ctlParent, ss=True)
    )
    if attach_rot:
        # npo.setTranslation(base.getTranslation(space="world"), space="world")
        pm.parentConstraint(base, npo, mo=False)
    else:
        pm.pointConstraint(base, npo, mo=False)

    # create joints
    if not jntParent:
        jntParent = npo
        matrix_cnx = False
    else:
        # need extra connection to ensure is moving with th npo, even is
        # not child of npo
        matrix_cnx = True

    jointBase = primitive.addJoint(jntParent, nameSide + "_jnt_lvl")
    joint = primitive.addJoint(jointBase, nameSide + "_jnt")

    # reset axis and invert behaviour
    for axis in "XYZ":
        pm.setAttr(jointBase + ".jointOrient" + axis, 0)
        pm.setAttr(npo + ".translate" + axis, 0)

    pp = npo.getParent()
    pm.parent(npo, w=True)
    for axis in "xyz":
        npo.attr("r" + axis).set(0)
    if side == "R":
        npo.attr("ry").set(180)
        npo.attr("sz").set(-1)
    pm.parent(npo, pp)

    dm_node = None

    if matrix_cnx:
        mulmat_node = applyop.gear_mulmatrix_op(
            npo + ".worldMatrix", jointBase + ".parentInverseMatrix"
        )
        dm_node = node.createDecomposeMatrixNode(mulmat_node + ".output")
        m = mulmat_node.attr("output").get()
        pm.connectAttr(dm_node + ".outputTranslate", jointBase + ".t")
        pm.connectAttr(dm_node + ".outputRotate", jointBase + ".r")

        # invert negative scaling in Joints. We only inver Z axis, so is
        # the only axis that we are checking
        if dm_node.attr("outputScaleZ").get() < 0:
            mul_nod_invert = node.createMulNode(
                dm_node.attr("outputScaleZ"), -1
            )
            out_val = mul_nod_invert.attr("outputX")
        else:
            out_val = dm_node.attr("outputScaleZ")

        pm.connectAttr(dm_node.attr("outputScaleX"), jointBase + ".sx")
        pm.connectAttr(dm_node.attr("outputScaleY"), jointBase + ".sy")
        pm.connectAttr(out_val, jointBase + ".sz")
        pm.connectAttr(dm_node + ".outputShear", jointBase + ".shear")

        # Segment scale compensate Off to avoid issues with the global
        # scale
        jointBase.setAttr("segmentScaleCompensate", 0)
        joint.setAttr("segmentScaleCompensate", 0)

        jointBase.setAttr("jointOrient", 0, 0, 0)

        # setting the joint orient compensation in order to have clean
        # rotation channels
        jointBase.attr("jointOrientX").set(jointBase.attr("rx").get())
        jointBase.attr("jointOrientY").set(jointBase.attr("ry").get())
        jointBase.attr("jointOrientZ").set(jointBase.attr("rz").get())

        im = m.inverse()

        if gearMulMatrix:
            mul_nod = applyop.gear_mulmatrix_op(
                mulmat_node.attr("output"), im, jointBase, "r"
            )
            dm_node2 = mul_nod.output.listConnections()[0]
        else:
            mul_nod = node.createMultMatrixNode(
                mulmat_node.attr("matrixSum"), im, jointBase, "r"
            )
            dm_node2 = mul_nod.matrixSum.listConnections()[0]

        if dm_node.attr("outputScaleZ").get() < 0:
            negateTransformConnection(dm_node2.outputRotate, jointBase.rotate)

    else:
        resetJntLocalSRT(jointBase)

    # hidding joint base by changing the draw mode
    pm.setAttr(jointBase + ".drawStyle", 2)
    if not defSet:
        try:
            defSet = pm.PyNode("rig_deformers_grp")
        except TypeError:
            pm.sets(n="rig_deformers_grp", empty=True)
            defSet = pm.PyNode("rig_deformers_grp")
    pm.sets(defSet, add=joint)

    controlType = ctlShape
    o_icon = icon.create(
        npo,
        nameSide + "_ctl",
        datatypes.Matrix(),
        color,
        controlType,
        w=size,
        h=size,
        d=size,
    )

    attribute.addAttribute(o_icon, "isCtl", "bool", keyable=False)

    transform.resetTransform(o_icon)
    if dm_node and dm_node.attr("outputScaleZ").get() < 0:
        pm.connectAttr(o_icon.scale, joint.scale)
        negateTransformConnection(o_icon.rotate, joint.rotate)
        negateTransformConnection(
            o_icon.translate, joint.translate, [1, 1, -1]
        )

    else:
        for t in [".translate", ".scale", ".rotate"]:
            pm.connectAttr(o_icon + t, joint + t)

    # create the attributes to handlde mirror and symetrical pose
    attribute.addAttribute(
        o_icon, "invTx", "bool", 0, keyable=False, niceName="Invert Mirror TX"
    )
    attribute.addAttribute(
        o_icon, "invTy", "bool", 0, keyable=False, niceName="Invert Mirror TY"
    )
    attribute.addAttribute(
        o_icon, "invTz", "bool", 0, keyable=False, niceName="Invert Mirror TZ"
    )
    attribute.addAttribute(
        o_icon, "invRx", "bool", 0, keyable=False, niceName="Invert Mirror RX"
    )
    attribute.addAttribute(
        o_icon, "invRy", "bool", 0, keyable=False, niceName="Invert Mirror RY"
    )
    attribute.addAttribute(
        o_icon, "invRz", "bool", 0, keyable=False, niceName="Invert Mirror RZ"
    )
    attribute.addAttribute(
        o_icon, "invSx", "bool", 0, keyable=False, niceName="Invert Mirror SX"
    )
    attribute.addAttribute(
        o_icon, "invSy", "bool", 0, keyable=False, niceName="Invert Mirror SY"
    )
    attribute.addAttribute(
        o_icon, "invSz", "bool", 0, keyable=False, niceName="Invert Mirror SZ"
    )

    # magic of doritos connection
    pre_bind_matrix_connect(mesh, joint, jointBase)

    # add control tag
    node.add_controller_tag(o_icon, ctl_parent_tag)

    if not ctlSet:
        try:
            ctlSet = pm.PyNode("rig_controllers_grp")
        except TypeError:
            pm.sets(n="rig_controllers_grp", empty=True)
            ctlSet = pm.PyNode("rig_controllers_grp")
    pm.sets(ctlSet, add=o_icon)

    return o_icon, pin


def create_mirror_proximity_tweak(
    mesh,
    edgePair,
    name,
    parent=None,
    ctlParent=None,
    jntParent=None,
    color=[0, 0, 0],
    size=0.04,
    defSet=None,
    ctlSet=None,
    side=None,
    gearMulMatrix=True,
    attach_rot=False,
    inputMesh=None,
    ctlShape="sphere",
    existing_pin=None,
):
    """Create a tweak joint attached to the mesh using a proximity pin.
    The edge pair will be used to find the mirror position on the mesh

    Args:
        mesh (mesh): The object to add the tweak
        edgePair (pair list): The edge pair to create the rivet
        name (str): The name for the tweak
        parent (None or dagNode, optional): The parent for the tweak
        ctlParent (None or dagNode, optional): The parent for the tweak control
        jntParent (None or dagNode, optional): The parent for the joints
        color (list, optional): The color for the control
        size (float, optional): Size of the control
        defSet (None or set, optional): Deformer set to add the joints
        ctlSet (None or set, optional): the set to add the controls
        side (None, str): String to set the side. Valid values are L, R or C.
            If the side is not set or the value is not valid, the side will be
            set automatically based on the world position
        gearMulMatrix (bool, optional): If False will use Maya default multiply
            matrix node
        attach_rot (bool, optional): Description
        inputMesh (None, optional): Description
        ctlShape (str, optional): Description
        existing_pin (None, optional): Description

    Returns:
        PyNode: The tweak control and pin node
    """
    if not inputMesh:
        navi_mesh = mesh
    else:
        navi_mesh = inputMesh
    mirror_edge_pair = [
        mesh_navi.find_mirror_edge(navi_mesh, edgePair[1]).index(),
        mesh_navi.find_mirror_edge(navi_mesh, edgePair[0]).index(),
    ]
    return create_proximity_tweak(
        mesh,
        mirror_edge_pair,
        name,
        parent,
        ctlParent,
        jntParent,
        color,
        size,
        defSet,
        ctlSet,
        side,
        gearMulMatrix,
        attach_rot,
        inputMesh,
        ctlShape,
        existing_pin=existing_pin,
    )
