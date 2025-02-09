"""

**Apply operator module**

Operators are any node that connected to other nodes creates a rig behaviour::

    I.E: IK solvers and  constraints are operators

"""


#############################################
# GLOBAL
#############################################
import pymel.core as pm
from pymel.core import datatypes

import maya.api.OpenMaya as om
from .six import string_types

from mgear.core import attribute
from mgear.core import surface

#############################################
# BUILT IN NODES
#############################################


def parentCns(driver, driven, maintain_offset=True, **kwargs):
    """
    Apply a parent constraint from driver to driven, skipping locked attributes,
    and allowing additional keyword arguments for the parentConstraint command.

    Args:
        driver (pm.nt.Transform): The driver object to apply the constraint.
        driven (pm.nt.Transform): The driven object to be constrained.
        maintain_offset (bool): Whether to maintain the current offset.

    Returns:
        pm.nodetypes.ParentConstraint: The created parent constraint node.

    Raises:
        ValueError: If all translate and rotate attributes on the driven are locked.
    """
    # Determine which translate and rotate attributes are locked
    skip_translate = [
        axis for axis in "xyz" if driven.attr("t" + axis).isLocked()
    ]
    skip_rotate = [
        axis for axis in "xyz" if driven.attr("r" + axis).isLocked()
    ]

    # Check if all attributes are locked, raise an exception if so
    if len(skip_translate) == 3 and len(skip_rotate) == 3:
        raise ValueError(
            "All translate and rotate attributes on the driven are locked."
        )

    # Apply constraint, skipping the locked attributes
    constraint = pm.parentConstraint(
        driver,
        driven,
        mo=maintain_offset,
        skipTranslate=skip_translate,
        skipRotate=skip_rotate,
        **kwargs  # Pass any additional keyword arguments
    )

    return constraint


def curvecns_op(crv, inputs=[]):
    for i, item in enumerate(inputs):
        node = pm.createNode("decomposeMatrix")
        pm.connectAttr(item + ".worldMatrix[0]", node + ".inputMatrix")
        pm.connectAttr(
            node + ".outputTranslate", crv + ".controlPoints[%s]" % i
        )

    return node


def splineIK(name, chn, parent=None, cParent=None, curve=None):
    """Apply a splineIK solver to a chain.

    Arguments:
        name (str): Name of the operator node.
        chn (list of joints): List of joints. At less 2 joints should be in
            the list.
        parent (dagNode): Parent for the ikHandle.
        cParent (dagNode): Parent for the curve.
        curve (dagNode): Specifies the curve to be used by the ikSplineHandle.
            This param is optional.

    Returns:
        list: ikHandle node and splinecrv in a list

    Example:
        >>> aop.splineIK(self.getName("rollRef"),
                         self.rollRef,
                         parent=self.root,
                         cParent=self.bone0 )

    """
    data = {}
    data["n"] = name
    data["solver"] = "ikSplineSolver"
    data["ccv"] = True
    data["startJoint"] = chn[0]
    data["endEffector"] = chn[-1]
    if curve is not None:
        data["curve"] = curve

    node, effector, splineCrv = pm.ikHandle(**data)
    # converting to pyNode
    node = pm.PyNode("|" + node)
    effector = pm.PyNode(effector)
    splineCrv = pm.PyNode(splineCrv)

    node.setAttr("visibility", False)
    splineCrv.setAttr("visibility", False)
    pm.rename(splineCrv, name + "_crv")
    pm.rename(effector, name + "_eff")
    if parent is not None:
        parent.addChild(node)
    if cParent is not None:
        cParent.addChild(splineCrv)

    return node, splineCrv


def oriCns(driver, driven, maintainOffset=False):
    """Apply orientation constraint

    Apply orientation constraint changing XYZ  default connexions by
    rotate compound connexions

    Note:
        We have found an evaluation difference in the values if the connexion
        is compound or by axis

    Arguments:
        driver (dagNode or dagNode list): Driver object.
        driven (dagNode): Driven object.
        maintainOffset (bool): Keep the offset.

    Returns:
        pyNode: Orientation constraintn node.

    Example:
        .. code-block:: python

            import mgear.core.applyop as aop
            import pymel.core as pm
            sphere = pm.polySphere(n='sphereDriver')
            cube = pm.polyCube(n='cubeDriven')
            ori_cns = aop.oriCns(sphere[0], cube[0], True)

    """
    oriCns = pm.orientConstraint(driver, driven, maintainOffset=maintainOffset)
    for axis in "XYZ":
        pm.disconnectAttr(
            oriCns + ".constraintRotate" + axis, driven + ".rotate" + axis
        )
    pm.connectAttr(oriCns + ".constraintRotate", driven + ".rotate", f=True)

    return oriCns


def pathCns(obj, curve, cnsType=False, u=0, tangent=False):
    """
    Apply a path constraint or curve constraint.

    Arguments:
        obj (dagNode): Constrained object.
        curve (Nurbscurve): Constraining Curve.
        cnsType (int): 0 for Path Constraint, 1 for Curve
            Constraint (Parametric).
        u (float): Position of the object on the curve (from 0 to 100 for path
            constraint, from 0 to 1 for Curve cns).
        tangent (bool): Keep tangent orientation option.

    Returns:
        pyNode: The newly created constraint.
    """
    node = pm.PyNode(pm.createNode("motionPath"))
    node.setAttr("uValue", u)
    node.setAttr("fractionMode", not cnsType)
    node.setAttr("follow", tangent)

    pm.connectAttr(curve.attr("worldSpace"), node.attr("geometryPath"))
    pm.connectAttr(node.attr("allCoordinates"), obj.attr("translate"))
    pm.connectAttr(node.attr("rotate"), obj.attr("rotate"))
    pm.connectAttr(node.attr("rotateOrder"), obj.attr("rotateOrder"))
    pm.connectAttr(node.attr("message"), obj.attr("specifiedManipLocation"))

    return node


# TODO: review function to make wupObject optional


def aimCns(
    obj,
    master,
    axis="xy",
    wupType="objectrotation",
    wupVector=[0, 1, 0],
    wupObject=None,
    maintainOffset=False,
):
    """Apply a direction constraint

    Arguments:
        obj (dagNode): Constrained object.
        master (dagNode): Constraining Object.
        axis (str): Define pointing axis and upvector
            axis (combination of xyz and -x-y-z).
        wupType (str): scene, object, objectrotation, vector, or none.
        wupVector (list of 3 float): world up vector. Exp: [0.0,1.0,0.0].
        wupObject (pyNode): world up object.
        maintainOffset (bool): Maintain offset.

    Returns:
        pyNode: Newly created constraint.

    """
    node = pm.aimConstraint(
        master,
        obj,
        worldUpType=wupType,
        worldUpVector=wupVector,
        worldUpObject=wupObject,
        maintainOffset=maintainOffset,
    )

    if axis == "xy":
        a = [1, 0, 0, 0, 1, 0]
    elif axis == "xz":
        a = [1, 0, 0, 0, 0, 1]
    elif axis == "yx":
        a = [0, 1, 0, 1, 0, 0]
    elif axis == "yz":
        a = [0, 1, 0, 0, 0, 1]
    elif axis == "zx":
        a = [0, 0, 1, 1, 0, 0]
    elif axis == "zy":
        a = [0, 0, 1, 0, 1, 0]

    elif axis == "-xy":
        a = [-1, 0, 0, 0, 1, 0]
    elif axis == "-xz":
        a = [-1, 0, 0, 0, 0, 1]
    elif axis == "-yx":
        a = [0, -1, 0, 1, 0, 0]
    elif axis == "-yz":
        a = [0, -1, 0, 0, 0, 1]
    elif axis == "-zx":
        a = [0, 0, -1, 1, 0, 0]
    elif axis == "-zy":
        a = [0, 0, -1, 0, 1, 0]

    elif axis == "x-y":
        a = [1, 0, 0, 0, -1, 0]
    elif axis == "x-z":
        a = [1, 0, 0, 0, 0, -1]
    elif axis == "y-x":
        a = [0, 1, 0, -1, 0, 0]
    elif axis == "y-z":
        a = [0, 1, 0, 0, 0, -1]
    elif axis == "z-x":
        a = [0, 0, 1, -1, 0, 0]
    elif axis == "z-y":
        a = [0, 0, 1, 0, -1, 0]

    elif axis == "-x-y":
        a = [-1, 0, 0, 0, -1, 0]
    elif axis == "-x-z":
        a = [-1, 0, 0, 0, 0, -1]
    elif axis == "-y-x":
        a = [0, -1, 0, -1, 0, 0]
    elif axis == "-y-z":
        a = [0, -1, 0, 0, 0, -1]
    elif axis == "-z-x":
        a = [0, 0, -1, -1, 0, 0]
    elif axis == "-z-y":
        a = [0, 0, -1, 0, -1, 0]

    for i, name in enumerate(
        [
            "aimVectorX",
            "aimVectorY",
            "aimVectorZ",
            "upVectorX",
            "upVectorY",
            "upVectorZ",
        ]
    ):
        pm.setAttr(node + "." + name, a[i])

    return node


#############################################
# CUSTOM NODES
#############################################


def gear_raycast(
    in_mesh, ray_source, ray_direction, out_obj=None, connect_srt="t"
):
    """Create and connect mraycast  node

    Args:
        in_mesh (shape): Mesh shape
        ray_source (transform): ray source
        ray_direction (transform): ray direction
        out_obj (transform, optional): Object to apply the raycast contact
        connect_srt (str, optional): scale rotation traanslation flag

    Returns:
        PyNode: The raycast node
    """
    node = pm.createNode("mgear_rayCastPosition")
    pm.connectAttr(
        ray_source + ".worldMatrix[0]", node + ".raySource", force=True
    )
    pm.connectAttr(
        ray_direction + ".worldMatrix[0]", node + ".rayDirection", force=True
    )
    pm.connectAttr(in_mesh + ".outMesh", node + ".meshInput", force=True)

    if out_obj:
        gear_matrix_cns(node.output, out_obj=out_obj, connect_srt=connect_srt)

    return node


def gear_matrix_cns(
    in_obj,
    out_obj=None,
    connect_srt="srt",
    rot_off=[0, 0, 0],
    rot_mult=[1, 1, 1],
    scl_mult=[1, 1, 1],
    maintainRotOffset=True,
):
    """Create and connect matrix constraint node

    Args:
        in_obj (transform): the driver object or matrix
        out_obj (transform, optional): the driven object
        connect_srt (str, optional): scale rotation traanslation flag
        rot_off (list, optional): rotation offset for XYZ
        rot_mult (list, optional): rotation multiplier for XYZ
        scl_mult (list, optional): scale multiplier for XYZ

    Returns:
        PyNode: The matrix constraint node
    """
    node = pm.createNode("mgear_matrixConstraint")
    if isinstance(in_obj, pm.PyNode) and in_obj.type() == "matrix":
        pm.connectAttr(in_obj, node + ".driverMatrix", force=True)
    else:
        pm.connectAttr(
            in_obj + ".worldMatrix[0]", node + ".driverMatrix", force=True
        )

    # setting rot and scl config
    node.driverRotationOffsetX.set(rot_off[0])
    node.driverRotationOffsetY.set(rot_off[1])
    node.driverRotationOffsetZ.set(rot_off[2])

    node.rotationMultX.set(rot_mult[0])
    node.rotationMultY.set(rot_mult[1])
    node.rotationMultZ.set(rot_mult[2])

    node.scaleMultX.set(scl_mult[0])
    node.scaleMultY.set(scl_mult[1])
    node.scaleMultZ.set(scl_mult[2])

    if out_obj:
        pm.connectAttr(
            out_obj + ".parentInverseMatrix[0]",
            node + ".drivenParentInverseMatrix",
            force=True,
        )

        if maintainRotOffset:
            # calculate rotation rest pose
            # we use the  outputDriverOffsetMatrix to have in account the offset
            # rotation when the rest pose is calculated
            driver_m = om.MMatrix(
                pm.getAttr(node + ".outputDriverOffsetMatrix")
            )
            driven_m = om.MMatrix(
                pm.getAttr(out_obj + ".parentInverseMatrix[0]")
            )
            mult = driver_m * driven_m
            pm.setAttr(node + ".drivenRestMatrix", mult, type="matrix")

        # connect srt (scale, rotation, translation)
        if "t" in connect_srt:
            pm.connectAttr(node.translate, out_obj.attr("translate"), f=True)
        if "r" in connect_srt:
            pm.connectAttr(node.rotate, out_obj.attr("rotate"), f=True)
        if "s" in connect_srt:
            pm.connectAttr(node.scale, out_obj.attr("scale"), f=True)
            pm.connectAttr(node.shear, out_obj.attr("shear"), f=True)

    return node


def gear_spring_op(in_obj, goal=False, solver="mgear_springNode"):
    """Apply mGear spring node.

    Arguments:
        in_obj (dagNode): Constrained object.
        goal (dagNode): By default is False.
        solver (str, optional): Spring solver

    Returns:
        pyNode: Newly created node
    """
    if not goal:
        goal = in_obj

    node = pm.createNode(solver)

    pm.connectAttr("time1.outTime", node + ".time")
    dm_node = pm.createNode("decomposeMatrix")
    pm.connectAttr(goal + ".parentMatrix", dm_node + ".inputMatrix")
    pm.connectAttr(dm_node + ".outputTranslate", node + ".goal")

    cm_node = pm.createNode("composeMatrix")
    pm.connectAttr(node + ".output", cm_node + ".inputTranslate")

    mm_node = pm.createNode("mgear_mulMatrix")

    pm.connectAttr(cm_node + ".outputMatrix", mm_node + ".matrixA")
    pm.connectAttr(in_obj + ".parentInverseMatrix", mm_node + ".matrixB")

    dm_node2 = pm.createNode("decomposeMatrix")
    pm.connectAttr(mm_node + ".output", dm_node2 + ".inputMatrix")
    pm.connectAttr(dm_node2 + ".outputTranslate", in_obj + ".translate")

    pm.setAttr(node + ".stiffness", 0.5)
    pm.setAttr(node + ".damping", 0.5)

    return node


def gear_spring_gravity_op(in_obj, goal=False):
    """Apply mGear spring Gravity  node.

    Arguments:
        in_obj (dagNode): Constrained object.
        goal (dagNode): By default is False.

    Returns:
        pyNode: Newly created node
    """

    return gear_spring_op(in_obj, goal=goal, solver="mgear_springGravityNode")


def gear_mulmatrix_op(mA, mB, target=False, transform="srt"):
    """Create mGear multiply Matrix node.

    Note:
        This node have same functionality as the default Maya matrix
        multiplication.

    Arguments:
        mA (matrix): input matrix A.
        mB (matrix): input matrix B.
        target (dagNode): object target to apply the transformation
        transform (str): if target is True. out transform  to SRT valid
            value s r t

    Returns:
        pyNode: Newly created mGear_multMatrix node

    """
    node = pm.createNode("mgear_mulMatrix")
    for m, mi in zip([mA, mB], ["matrixA", "matrixB"]):
        if isinstance(m, datatypes.Matrix):
            pm.setAttr(node.attr(mi), m)
        else:
            pm.connectAttr(m, node.attr(mi))
    if target:
        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(node + ".output", dm_node + ".inputMatrix")
        if "t" in transform:
            pm.connectAttr(
                dm_node + ".outputTranslate", target.attr("translate"), f=True
            )
        if "r" in transform:
            pm.connectAttr(
                dm_node + ".outputRotate", target.attr("rotate"), f=True
            )
        if "s" in transform:
            pm.connectAttr(
                dm_node + ".outputScale", target.attr("scale"), f=True
            )

    return node


def gear_intmatrix_op(mA, mB, blend=0):
    """
    create mGear interpolate Matrix node.

    Arguments:
        mA (matrix): Input matrix A.
        mB (matrix): Input matrix A.
        blend (float or connection): Blending value.

    Returns:
        pyNode: Newly created mGear_intMatrix node
    """
    node = pm.createNode("mgear_intMatrix")

    pm.connectAttr(mA, node + ".matrixA")
    pm.connectAttr(mB, node + ".matrixB")

    if isinstance(blend, string_types) or isinstance(blend, pm.Attribute):
        pm.connectAttr(blend, node + ".blend")
    else:
        pm.setAttr(node + ".blend", blend)

    return node


def gear_curvecns_op(crv, inputs=[]):
    """
    create mGear curvecns node.

    Arguments:
        crv (nurbsCurve): Nurbs curve.
        inputs (List of dagNodes): Input object to drive the curve. Should be
            same number as crv points.
            Also the order should be the same as the points

    Returns:
        pyNode: The curvecns node.
    """
    pm.select(crv)
    node = pm.deformer(type="mgear_curveCns")[0]

    for i, item in enumerate(inputs):
        pm.connectAttr(item + ".worldMatrix", node + ".inputs[%s]" % i)

    return node


def gear_curveslide2_op(
    outcrv, incrv, position=0, maxstretch=1, maxsquash=1, softness=0
):
    """Apply a sn_curveslide2_op operator

    Arguments:
        outcrv (NurbsCurve): Out Curve.
        incrv (NurbsCurve):  In Curve.
        position (float): Default position value (from 0 to 1).
        maxstretch (float): Default maxstretch value (from 1 to infinite).
        maxsquash (float): Default maxsquash value (from 0 to 1).
        softness (float): Default softness value (from 0 to 1).

    Returns:
        pyNode: The newly created operator.
    """
    pm.select(outcrv)
    node = pm.deformer(type="mgear_slideCurve2")[0]

    pm.connectAttr(incrv + ".local", node + ".master_crv")
    pm.connectAttr(incrv + ".worldMatrix", node + ".master_mat")

    pm.setAttr(node + ".master_length", pm.arclen(incrv))
    pm.setAttr(node + ".slave_length", pm.arclen(incrv))
    pm.setAttr(node + ".position", 0)
    pm.setAttr(node + ".maxstretch", 1)
    pm.setAttr(node + ".maxsquash", 1)
    pm.setAttr(node + ".softness", 0)

    return node


def gear_spinePointAtOp(cns, startobj, endobj, blend=0.5, axis="-Z"):
    """
    Apply a SpinePointAt operator

    Arguments:
        cns (Constraint): The constraint to apply the operator on (must be a
            curve, path or direction constraint).
        startobj (dagNode): Start Reference.
        endobj (dagNode): End Reference.
        blend (float): Blend influence value from 0 to 1.
        axis (string): Axis direction.

    Returns:
        pyNode: The newly created operator.
    """
    node = pm.createNode("mgear_spinePointAt")

    # Inputs
    pm.setAttr(node + ".blend", blend)
    pm.setAttr(node + ".axe", ["X", "Y", "Z", "-X", "-Y", "-Z"].index(axis))

    pm.connectAttr(startobj + ".rotate", node + ".rotA")
    pm.connectAttr(endobj + ".rotate", node + ".rotB")

    # Outputs
    pm.setAttr(cns + ".worldUpType", 3)

    pm.connectAttr(node + ".pointAt", cns + ".worldUpVector")

    return node


def gear_spinePointAtOpWM(cns, startobj, endobj, blend=0.5, axis="-Z"):
    """
    Apply a SpinePointAt operator using world matrix

    Arguments:
        cns Constraint: The constraint to apply the operator on (must be a
            curve, path or direction constraint).
        startobj (dagNode): Start Reference.
        endobj (dagNode): End Reference.
        blend (float): Blend influence value from 0 to 1.
        axis (str): Axis direction.

    Returns:
        pyNode: The newly created operator.
    """
    node = pm.createNode("mgear_spinePointAt")

    # Inputs
    pm.setAttr(node + ".blend", blend)
    pm.setAttr(node + ".axe", ["X", "Y", "Z", "-X", "-Y", "-Z"].index(axis))

    dem_node1 = pm.createNode("decomposeMatrix")
    dem_node2 = pm.createNode("decomposeMatrix")
    pm.connectAttr(startobj + ".worldMatrix", dem_node1 + ".inputMatrix")
    pm.connectAttr(endobj + ".worldMatrix", dem_node2 + ".inputMatrix")

    pm.connectAttr(dem_node1 + ".outputRotate", node + ".rotA")
    pm.connectAttr(dem_node2 + ".outputRotate", node + ".rotB")

    # Outputs
    pm.setAttr(cns + ".worldUpType", 3)

    pm.connectAttr(node + ".pointAt", cns + ".worldUpVector")

    return node


def gear_ikfk2bone_op(
    out=[],
    root=None,
    eff=None,
    upv=None,
    fk0=None,
    fk1=None,
    fk2=None,
    lengthA=5,
    lengthB=3,
    negate=False,
    blend=0,
):
    """Apply a sn_ikfk2bone_op operator

    Arguments:
        out (list of dagNodes): The constrained outputs order must be respected
            (BoneA, BoneB,  Center, CenterN, Eff), set it to None if you don't
            want one of the output.
        root (dagNode): Object that will act as the root of the chain.
        eff (dagNode): Object that will act as the eff controler of the chain.
        upv (dagNode): Object that will act as the up vector of the chain.
        fk0 (dagNode): Object that will act as the first fk controler of the
            chain.
        fk1 (dagNode): Object that will act as the second fk controler of the
            chain.
        fk2 (dagNode): Object that will act as the fk effector controler of the
            chain.
        lengthA (float): Length of first bone.
        lengthB (float): Length of second bone.
        negate (bool):  Use with negative Scale.
        blend (float): Default blend value (0 for full ik, 1 for full fk).

    Returns:
        pyNode: The newly created operator.

    """
    node = pm.createNode("mgear_ikfk2Bone")

    # Inputs
    pm.setAttr(node + ".lengthA", lengthA)
    pm.setAttr(node + ".lengthB", lengthB)
    pm.setAttr(node + ".negate", negate)
    pm.setAttr(node + ".blend", blend)

    pm.connectAttr(root + ".worldMatrix", node + ".root")
    pm.connectAttr(eff + ".worldMatrix", node + ".ikref")
    pm.connectAttr(upv + ".worldMatrix", node + ".upv")
    pm.connectAttr(fk0 + ".worldMatrix", node + ".fk0")
    pm.connectAttr(fk1 + ".worldMatrix", node + ".fk1")
    pm.connectAttr(fk2 + ".worldMatrix", node + ".fk2")

    # Outputs
    if out[0] is not None:
        pm.connectAttr(out[0] + ".parentMatrix", node + ".inAparent")

        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(node + ".outA", dm_node + ".inputMatrix")
        pm.connectAttr(dm_node + ".outputTranslate", out[0] + ".translate")
        pm.connectAttr(dm_node + ".outputRotate", out[0] + ".rotate")
        pm.connectAttr(dm_node + ".outputScale", out[0] + ".scale")

    if out[1] is not None:
        pm.connectAttr(out[1] + ".parentMatrix", node + ".inBparent")

        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(node + ".outB", dm_node + ".inputMatrix")
        pm.connectAttr(dm_node + ".outputTranslate", out[1] + ".translate")
        pm.connectAttr(dm_node + ".outputRotate", out[1] + ".rotate")
        pm.connectAttr(dm_node + ".outputScale", out[1] + ".scale")

    if out[2] is not None:
        pm.connectAttr(out[2] + ".parentMatrix", node + ".inCenterparent")

        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(node + ".outCenter", dm_node + ".inputMatrix")
        pm.connectAttr(dm_node + ".outputTranslate", out[2] + ".translate")
        pm.connectAttr(dm_node + ".outputRotate", out[2] + ".rotate")
        # connectAttr(dm_node+".outputScale", out[2]+".scale") # the scaling
        # is not working with FK blended to 1.
        # The output is from the solver I need to review the c++ solver

    if out[3] is not None:
        pm.connectAttr(out[3] + ".parentMatrix", node + ".inEffparent")

        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(node + ".outEff", dm_node + ".inputMatrix")
        pm.connectAttr(dm_node + ".outputTranslate", out[3] + ".translate")
        pm.connectAttr(dm_node + ".outputRotate", out[3] + ".rotate")
        pm.connectAttr(dm_node + ".outputScale", out[3] + ".scale")

    return node


def gear_rollsplinekine_op(out, controlers=[], u=0.5, subdiv=10):
    """Apply a sn_rollsplinekine_op operator

    Arguments:
        out (dagNode): onstrained Object.
        controlers (list of dagNodes): Objects that will act as controler of
            the bezier curve. Objects must have a parent that will be used as
            an input for the operator.
        u (float): Position of the object on the bezier curve (from 0 to 1).
        subdiv (int): spline subdivision precision.

    Returns:
        pyNode: The newly created operator.
    """
    node = pm.createNode("mgear_rollSplineKine")

    # Inputs
    pm.setAttr(node + ".u", u)
    pm.setAttr(node + ".subdiv", subdiv)

    dm_node = pm.createNode("decomposeMatrix")

    pm.connectAttr(node + ".output", dm_node + ".inputMatrix")
    pm.connectAttr(dm_node + ".outputTranslate", out + ".translate")
    pm.connectAttr(dm_node + ".outputRotate", out + ".rotate")
    # connectAttr(dm_node+".outputScale", out+".scale")

    pm.connectAttr(out + ".parentMatrix", node + ".outputParent")

    for i, obj in enumerate(controlers):
        pm.connectAttr(obj + ".parentMatrix", node + ".ctlParent[%s]" % i)

        pm.connectAttr(obj + ".worldMatrix", node + ".inputs[%s]" % i)
        pm.connectAttr(obj + ".rx", node + ".inputsRoll[%s]" % i)

    return node


def gear_squashstretch2_op(
    out, sclref=None, length=5, axis="x", scaleComp=None
):
    """Apply a sn_squashstretch2_op operator

    Arguments:
        out (dagNode): Constrained object.
        sclref (dagNode): Global scaling reference object.
        length (float): Rest Length of the S&S.
        axis (str): 'x' for scale all except x axis...
        scaleComp (list of float): extra scale compensation to avoid double
            scale in some situations.

    Returns:
        pyNode: The newly created operator.
    """
    node = pm.createNode("mgear_squashStretch2")

    pm.setAttr(node + ".global_scaleX", 1)
    pm.setAttr(node + ".global_scaleY", 1)
    pm.setAttr(node + ".global_scaleZ", 1)
    pm.setAttr(node + ".driver_ctr", length)
    pm.setAttr(node + ".driver_max", length * 2)
    pm.setAttr(node + ".driver_min", length / 2)
    pm.setAttr(node + ".axis", "xyz".index(axis))

    # we use a mult div node to force the evaluation in a composed attribute in
    # osx
    # Also helper connection for scale compensation (scaleComp)
    mult_node = pm.createNode("multiplyDivide")
    pm.connectAttr(node + ".output", mult_node + ".input1")
    for axis in "XYZ":
        pm.connectAttr(mult_node + ".output%s" % axis, out + ".scale%s" % axis)
    if scaleComp:
        pm.connectAttr(scaleComp, mult_node + ".input2")

    if sclref is not None:
        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(sclref + ".worldMatrix", dm_node + ".inputMatrix")
        pm.connectAttr(dm_node + ".outputScale", node + ".global_scale")

    return node


def gear_inverseRotorder_op(out_obj, in_obj):
    """
    Apply a sn_inverseRotorder_op operator

    Arguments:
        out_obj (dagNode): Output object.
        in_obj (dagNode): Input object.

    Returns:
        pyNode: The newly created operator.
    """
    node = pm.createNode("mgear_inverseRotOrder")

    pm.connectAttr(in_obj + ".ro", node + ".ro")
    pm.connectAttr(node + ".output", out_obj + ".ro")

    return node


def create_proximity_constraint(
    shape,
    in_trans,
    existing_pin=None,
    mtx_connect=True,
    out_trans=None,
    **kwargs
):
    """Create a proximity constraint between a shape and a transform.

    Args:
        shape (PyNode or str): Driver shape
        in_trans (PyNode or str): in transform
        existing_pin (PyNode, optional): Existing proximityPin node to connect to. Defaults to None.

    Returns:
        Tuple[PyNode, PyNode]: out_trans, pin
    """

    # Convert shape to PyNode if necessary
    if isinstance(shape, str):
        shape = pm.PyNode(shape)
    if isinstance(in_trans, str):
        in_trans = pm.PyNode(in_trans)

    # Try to get the original shape node
    shape_orig_connections = shape.inMesh.listConnections(d=True)
    if not shape_orig_connections:
        # If there's no original shape node, create one
        dup = pm.duplicate(shape, n="{}OrigTrans".format(shape), rc=True)[0]
        shape_orig = pm.listRelatives(dup, s=True)[0]
        shape_orig.rename("{}Orig".format(shape))
        pm.parent(shape_orig, shape, shape=True, add=True)
        pm.delete(dup)
        shape_orig.intermediateObject.set(1)
        shape_orig.worldMesh[0] >> shape.inMesh
    else:
        shape_orig = shape_orig_connections[0]
        # in some situation we get the transform instead of the shape.
        # In that case we try to get the shape
        try:
            shape_orig = shape_orig.getShape()
        except AttributeError:
            pass
        if not isinstance(shape_orig, pm.nt.Mesh):
            shape_orig = shape_orig.originalGeometry[0].listConnections(
                d=True, sh=True
            )[0]

    if existing_pin:
        pin = existing_pin
        idx = attribute.find_next_available_index(pin, "inputMatrix")
    else:
        # Create a new proximity pin node
        pin = pm.createNode("proximityPin", n="{}_proximityPin".format(shape))
        idx = 0

        # Set the input connections for the proximity pin
        shape.worldMesh[0] >> pin.deformedGeometry
        shape_orig.outMesh >> pin.originalGeometry

    # Connect in_trans to the found or default idx
    if mtx_connect:
        in_trans.matrix >> pin.inputMatrix[idx]
    else:
        pin.inputMatrix[idx].set(in_trans.matrix.get())

    if not out_trans:
        # Create the output transform
        out_trans = pm.createNode(
            "transform", n="{}_pinTrans{}".format(shape, idx)
        )

    # Set the input connections for the output transform
    pin.outputMatrix[idx] >> out_trans.offsetParentMatrix

    return out_trans, pin


def create_proximity_constraints(shape, in_trans_list):
    """Create a proximity constraint between a shape and a list of transforms.

    Args:
        shape (PyNode or str): Driver shape
        in_trans_list (List[PyNode] or List[str]): List of in transforms

    Returns:
        List[PyNode]: List of output transforms
    """
    # Convert shape to PyNode if necessary
    if isinstance(shape, str):
        shape = pm.PyNode(shape)

    # Convert each in_trans in the list to PyNode if necessary
    in_trans_list = [
        pm.PyNode(in_trans) if isinstance(in_trans, str) else in_trans
        for in_trans in in_trans_list
    ]

    # Try to get the original shape node
    shape_orig_connections = shape.inMesh.listConnections(d=True)
    if not shape_orig_connections:
        # If there's no original shape node, create one
        dup = pm.duplicate(shape, n="{}OrigTrans".format(shape), rc=True)[0]
        shape_orig = pm.listRelatives(dup, s=True)[0]
        shape_orig.rename("{}Orig".format(shape))
        dup.visibility.set(0)
        shape_orig.intermediateObject.set(1)
        shape_orig.worldMesh[0] >> shape.inMesh
    else:
        shape_orig = shape_orig_connections[0]
        if not isinstance(shape_orig, pm.nt.Mesh):
            shape_orig = shape_orig.originalGeometry[0].listConnections(
                d=True, sh=True
            )[0]

    # Create the proximity pin node
    pin = pm.createNode("proximityPin", n="{}_proximityPin".format(shape))

    # Set the input connections for the proximity pin
    shape.worldMesh[0] >> pin.deformedGeometry
    shape_orig.outMesh >> pin.originalGeometry

    # Create output transforms for each in_trans in the list
    out_trans_list = []
    for idx, in_trans in enumerate(in_trans_list):
        in_trans.matrix >> pin.inputMatrix[idx]

        # Create the output transform for this in_trans
        out_trans = pm.createNode(
            "transform", n="{}_pinTrans{}".format(shape, idx)
        )
        pin.outputMatrix[idx] >> out_trans.offsetParentMatrix
        out_trans_list.append(out_trans)

    return out_trans_list


def create_uv_pin_constraint(
    shape, in_trans, existing_pin=None, out_trans=None, **kwargs
):
    """Create a UV pin constraint between a shape and a transform.

    Args:
        shape (PyNode or str): Driver shape
        in_trans (PyNode or str): in transform
        existing_pin (PyNode, optional): Existing uvPin node to connect to. Defaults to None.
        mtx_connect (bool, optional): Whether to connect the input matrix. Defaults to True.
        out_trans (PyNode, optional): Existing out transform node to connect to. Defaults to None.

    Returns:
        Tuple[PyNode, PyNode]: out_trans, pin
    """
    # Convert shape to PyNode if necessary
    if isinstance(shape, str):
        shape = pm.PyNode(shape)
    if isinstance(in_trans, str):
        in_trans = pm.PyNode(in_trans)
    # Try to get the original shape node
    shape_orig_connections = shape.worldSpace.listConnections(d=True)
    if not shape_orig_connections:
        # If there's no original shape node, create one
        dup = pm.duplicate(shape, n="{}OrigTrans".format(shape), rc=True)[0]
        shape_orig = pm.listRelatives(dup, s=True)[0]
        shape_orig.rename("{}Orig".format(shape))
        pm.parent(shape_orig, shape, shape=True, add=True)
        pm.delete(dup)
        shape_orig.intermediateObject.set(1)
    else:
        shape_orig = shape_orig_connections[0]
        # In some situations we get the transform instead of the shape.
        # In that case we try to get the shape
        try:
            shape_orig = shape_orig.getShape()
        except AttributeError:
            pass
        if not isinstance(shape_orig, pm.nt.NurbsSurface):
            shape_orig = shape_orig.originalGeometry.listConnections(
                d=True, sh=True
            )[0]

    if existing_pin:
        pin = existing_pin
        idx = attribute.find_next_available_index(pin, "outputMatrix")
    else:
        # Create a new UV pin node
        pin = pm.createNode("uvPin", n="{}_uvPin".format(shape))
        idx = 0

        # Set the input connections for the UV pin
        shape.worldSpace[0] >> pin.deformedGeometry
        shape_orig.worldSpace[0] >> pin.originalGeometry

    # Set UV coordinates to the closest point
    position = in_trans.getTranslation(space="world")
    closest_uv = surface.get_closest_uv_coord(shape.name(), position)
    pin.coordinate[idx].coordinateU.set(closest_uv[0])
    pin.coordinate[idx].coordinateV.set(closest_uv[1])

    if not out_trans:
        # Create the output transform
        out_trans = pm.createNode(
            "transform", n="{}_pinTrans{}".format(shape, idx)
        )
    # Set the input connections for the output transform
    pin.outputMatrix[idx] >> out_trans.offsetParentMatrix

    return out_trans, pin
