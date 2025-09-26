"""Predefined nurbsCurve shapes to be use as a rigging control Icons"""

#############################################
# GLOBAL
#############################################
import mgear.pymaya as pm
from maya import cmds
import maya.OpenMaya as om
import mgear.pymaya.util as pmu
from mgear.pymaya import datatypes
from mgear.core import curve, attribute

import math

import mgear

#############################################
# ICON
#############################################


def create(
    parent=None,
    name="icon",
    m=datatypes.Matrix(),
    color=[0, 0, 0],
    icon="cube",
    **kwargs
):
    """Icon master function

    **Create icon master function.**
    This function centralize all the icons creation

    Arguments:
        parent (dagNode): The parent for the new icon
        name (str): Name of the Icon.
        m (matrix): Transformation matrix of the icon
        color (int or list of float): The color in index base or RGB.
        icon (str): Icon type. Options: "cube", "pyramid", "square",
            "flower", "circle", "cylinder", "compas", "diamond",
                    "cubewithpeak", "sphere", "arrow", "crossarrow",
                    "cross", "null"
        kwargs: The keyword arguments can vary depending of the icon type.
                    Please refear to the specific icon method for more info.

    Returns:
        dagNode: The newly created icon.

    """
    if "w" not in kwargs.keys():
        kwargs["w"] = 1
    if "h" not in kwargs.keys():
        kwargs["h"] = 1
    if "d" not in kwargs.keys():
        kwargs["d"] = 1
    if "po" not in kwargs.keys():
        kwargs["po"] = None
    if "ro" not in kwargs.keys():
        kwargs["ro"] = None
    if "degree" not in kwargs.keys():
        kwargs["degree"] = 3

    if icon == "cube":
        ctl = cube(
            parent,
            name,
            kwargs["w"],
            kwargs["h"],
            kwargs["d"],
            color,
            m,
            kwargs["po"],
            kwargs["ro"],
        )
    elif icon == "pyramid":
        ctl = pyramid(
            parent,
            name,
            kwargs["w"],
            kwargs["h"],
            kwargs["d"],
            color,
            m,
            kwargs["po"],
            kwargs["ro"],
        )
    elif icon == "square":
        ctl = square(
            parent,
            name,
            kwargs["w"],
            kwargs["d"],
            color,
            m,
            kwargs["po"],
            kwargs["ro"],
        )
    elif icon == "flower":
        ctl = flower(
            parent,
            name,
            kwargs["w"],
            color,
            m,
            kwargs["po"],
            kwargs["ro"],
            kwargs["degree"],
        )
    elif icon == "circle":
        ctl = circle(
            parent,
            name,
            kwargs["w"],
            color,
            m,
            kwargs["po"],
            kwargs["ro"],
            kwargs["degree"],
        )
    elif icon == "cylinder":
        ctl = cylinder(
            parent,
            name,
            kwargs["w"],
            kwargs["h"],
            color,
            m,
            kwargs["po"],
            kwargs["ro"],
            kwargs["degree"],
        )
    elif icon == "compas":
        ctl = compas(
            parent,
            name,
            kwargs["w"],
            color,
            m,
            kwargs["po"],
            kwargs["ro"],
            kwargs["degree"],
        )
    elif icon == "diamond":
        ctl = diamond(
            parent, name, kwargs["w"], color, m, kwargs["po"], kwargs["ro"]
        )
    elif icon == "cubewithpeak":
        ctl = cubewithpeak(
            parent, name, kwargs["w"], color, m, kwargs["po"], kwargs["ro"]
        )
    elif icon == "sphere":
        ctl = sphere(
            parent,
            name,
            kwargs["w"],
            color,
            m,
            kwargs["po"],
            kwargs["ro"],
            kwargs["degree"],
        )
    elif icon == "arrow":
        ctl = arrow(
            parent, name, kwargs["w"], color, m, kwargs["po"], kwargs["ro"]
        )
    elif icon == "crossarrow":
        ctl = crossarrow(
            parent, name, kwargs["w"], color, m, kwargs["po"], kwargs["ro"]
        )
    elif icon == "cross":
        ctl = cross(
            parent, name, kwargs["w"], color, m, kwargs["po"], kwargs["ro"]
        )
    elif icon == "null":
        ctl = null(
            parent, name, kwargs["w"], color, m, kwargs["po"], kwargs["ro"]
        )

    else:
        mgear.log("invalid type of ico", mgear.sev_error)
        return

    return ctl


def cube(
    parent=None,
    name="cube",
    width=1,
    height=1,
    depth=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a CUBE shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        height (float): Height of the shape.
        depth (float): Depth of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve
            from its center.
        rot_offset (vector): The xyz rotation offset of the curve
            from its center. xyz in radians

    Returns:
        dagNode: The newly created icon.
    """
    lenX = width * 0.5
    lenY = height * 0.5
    lenZ = depth * 0.5

    # p is positive, N is negative
    ppp = datatypes.Vector(lenX, lenY, lenZ)
    ppN = datatypes.Vector(lenX, lenY, lenZ * -1)
    pNp = datatypes.Vector(lenX, lenY * -1, lenZ)
    Npp = datatypes.Vector(lenX * -1, lenY, lenZ)
    pNN = datatypes.Vector(lenX, lenY * -1, lenZ * -1)
    NNp = datatypes.Vector(lenX * -1, lenY * -1, lenZ)
    NpN = datatypes.Vector(lenX * -1, lenY, lenZ * -1)
    NNN = datatypes.Vector(lenX * -1, lenY * -1, lenZ * -1)

    v_array = [
        ppp,
        ppN,
        NpN,
        NNN,
        NNp,
        Npp,
        NpN,
        Npp,
        ppp,
        pNp,
        NNp,
        pNp,
        pNN,
        ppN,
        pNN,
        NNN,
    ]

    points = getPointArrayWithOffset(v_array, pos_offset, rot_offset)

    node = curve.addCurve(parent, name, points, False, 1, m)

    setcolor(node, color)

    return node


def pyramid(
    parent=None,
    name="pyramid",
    width=1,
    height=1,
    depth=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a PYRAMIDE shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        height (float): Height of the shape.
        depth (float): Depth of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve
            from its center.
        rot_offset (vector): The xyz rotation offset of the curve
            from its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    lenX = width * 0.5
    lenY = height
    lenZ = depth * 0.5

    # p is positive, N is negative
    top = datatypes.Vector(0, lenY, 0)
    pp = datatypes.Vector(lenX, 0, lenZ)
    pN = datatypes.Vector(lenX, 0, lenZ * -1)
    Np = datatypes.Vector(lenX * -1, 0, lenZ)
    NN = datatypes.Vector(lenX * -1, 0, lenZ * -1)

    v_array = [pp, top, pN, pp, Np, top, NN, Np, NN, pN]

    points = getPointArrayWithOffset(v_array, pos_offset, rot_offset)

    node = curve.addCurve(parent, name, points, False, 1, m)

    setcolor(node, color)

    return node


def square(
    parent=None,
    name="square",
    width=1,
    depth=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a SQUARE shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        depth (float): Depth of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    lenX = width * 0.5
    lenZ = depth * 0.5

    v0 = datatypes.Vector(lenX, 0, lenZ)
    v1 = datatypes.Vector(lenX, 0, lenZ * -1)
    v2 = datatypes.Vector(lenX * -1, 0, lenZ * -1)
    v3 = datatypes.Vector(lenX * -1, 0, lenZ)

    points = getPointArrayWithOffset([v0, v1, v2, v3], pos_offset, rot_offset)

    node = curve.addCurve(parent, name, points, True, 1, m)

    setcolor(node, color)

    return node


def flower(
    parent=None,
    name="flower",
    width=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
    degree=3,
):
    """Create a curve with a FLOWER shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    dlen = width

    v0 = datatypes.Vector(0, -dlen, 0)
    v1 = datatypes.Vector(-dlen * 0.4, dlen * 0.4, 0)
    v2 = datatypes.Vector(dlen, 0, 0)
    v3 = datatypes.Vector(-dlen * 0.4, -dlen * 0.4, 0)
    v4 = datatypes.Vector(0, dlen, 0)
    v5 = datatypes.Vector(dlen * 0.4, -dlen * 0.4, 0)
    v6 = datatypes.Vector(-dlen, 0, 0)
    v7 = datatypes.Vector(dlen * 0.4, dlen * 0.4, 0)

    points = getPointArrayWithOffset(
        [v0, v1, v2, v3, v4, v5, v6, v7], pos_offset, rot_offset
    )

    node = curve.addCurve(parent, name, points, True, degree, m)

    setcolor(node, color)

    return node


def circle(
    parent=None,
    name="circle",
    width=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
    degree=3,
):
    """Create a curve with a CIRCLE shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    dlen = width * 0.5

    v0 = datatypes.Vector(0, 0, -dlen * 1.108)
    v1 = datatypes.Vector(dlen * 0.78, 0, -dlen * 0.78)
    v2 = datatypes.Vector(dlen * 1.108, 0, 0)
    v3 = datatypes.Vector(dlen * 0.78, 0, dlen * 0.78)
    v4 = datatypes.Vector(0, 0, dlen * 1.108)
    v5 = datatypes.Vector(-dlen * 0.78, 0, dlen * 0.78)
    v6 = datatypes.Vector(-dlen * 1.108, 0, 0)
    v7 = datatypes.Vector(-dlen * 0.78, 0, -dlen * 0.78)

    points = getPointArrayWithOffset(
        [v0, v1, v2, v3, v4, v5, v6, v7], pos_offset, rot_offset
    )

    node = curve.addCurve(parent, name, points, True, degree, m)

    setcolor(node, color)

    return node


def cylinder(
    parent=None,
    name="cylinder",
    width=1,
    heigth=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
    degree=3,
):
    """Create a curve with a CYLINDER shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        height (float): Height of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    dlen = width * 0.5
    dhei = heigth * 0.5

    if degree == 3:
        offsetMult = 1
    else:
        offsetMult = 1.108

    # upper circle
    v0 = datatypes.Vector(0, dhei, -dlen * 1.108)
    v1 = datatypes.Vector(dlen * 0.78, dhei, -dlen * 0.78)
    v2 = datatypes.Vector(dlen * 1.108, dhei, 0)
    v3 = datatypes.Vector(dlen * 0.78, dhei, dlen * 0.78)
    v4 = datatypes.Vector(0, dhei, dlen * 1.108)
    v5 = datatypes.Vector(-dlen * 0.78, dhei, dlen * 0.78)
    v6 = datatypes.Vector(-dlen * 1.108, dhei, 0)
    v7 = datatypes.Vector(-dlen * 0.78, dhei, -dlen * 0.78)

    # lower circle
    v8 = datatypes.Vector(0, -dhei, -dlen * 1.108)
    v9 = datatypes.Vector(dlen * 0.78, -dhei, -dlen * 0.78)
    v10 = datatypes.Vector(dlen * 1.108, -dhei, 0)
    v11 = datatypes.Vector(dlen * 0.78, -dhei, dlen * 0.78)
    v12 = datatypes.Vector(0, -dhei, dlen * 1.108)
    v13 = datatypes.Vector(-dlen * 0.78, -dhei, dlen * 0.78)
    v14 = datatypes.Vector(-dlen * 1.108, -dhei, 0)
    v15 = datatypes.Vector(-dlen * 0.78, -dhei, -dlen * 0.78)

    # curves
    v16 = datatypes.Vector(0, dhei, -dlen * offsetMult)
    v17 = datatypes.Vector(0, -dhei, -dlen * offsetMult)
    v18 = datatypes.Vector(0, -dhei, dlen * offsetMult)
    v19 = datatypes.Vector(0, dhei, dlen * offsetMult)

    v20 = datatypes.Vector(dlen * offsetMult, dhei, 0)
    v21 = datatypes.Vector(dlen * offsetMult, -dhei, 0)
    v22 = datatypes.Vector(-dlen * offsetMult, -dhei, 0)
    v23 = datatypes.Vector(-dlen * offsetMult, dhei, 0)

    points = getPointArrayWithOffset(
        [v0, v1, v2, v3, v4, v5, v6, v7], pos_offset, rot_offset
    )
    node = curve.addCurve(parent, name, points, True, degree, m)

    points = getPointArrayWithOffset(
        [v8, v9, v10, v11, v12, v13, v14, v15], pos_offset, rot_offset
    )
    crv_0 = curve.addCurve(parent, node + "_0crv", points, True, degree, m)

    points = getPointArrayWithOffset([v16, v17], pos_offset, rot_offset)
    crv_1 = curve.addCurve(parent, node + "_1crv", points, True, 1, m)

    points = getPointArrayWithOffset([v18, v19], pos_offset, rot_offset)
    crv_2 = curve.addCurve(parent, node + "_2crv", points, True, 1, m)

    points = getPointArrayWithOffset([v20, v21], pos_offset, rot_offset)
    crv_3 = curve.addCurve(parent, node + "_3crv", points, True, 1, m)

    points = getPointArrayWithOffset([v22, v23], pos_offset, rot_offset)
    crv_4 = curve.addCurve(parent, node + "_4crv", points, True, 1, m)

    for crv in [crv_0, crv_1, crv_2, crv_3, crv_4]:
        for shp in crv.listRelatives(shapes=True):
            node.addChild(shp, add=True, shape=True)
        pm.delete(crv)

    setcolor(node, color)

    return node


def compas(
    parent=None,
    name="compas",
    width=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
    degree=3,
):
    """Create a curve with a COMPAS shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    dlen = width * 0.5

    division = 24

    point_pos = []
    v = datatypes.Vector(0, 0, dlen)

    for i in range(division):
        if i == division / 2:
            w = datatypes.Vector(v.x, v.y, v.z - dlen * 0.4)
        else:
            w = datatypes.Vector(v.x, v.y, v.z)
        point_pos.append(w)
        v = v.rotateBy((0, (2 * pmu.math.pi) / (division + 0.0), 0))

    points = getPointArrayWithOffset(point_pos, pos_offset, rot_offset)
    node = curve.addCurve(parent, name, points, True, degree, m)

    setcolor(node, color)

    return node


def diamond(
    parent=None,
    name="diamond",
    width=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a DIAMOND shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        height (float): Height of the shape.
        depth (float): Depth of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    dlen = width * 0.5

    top = datatypes.Vector(0, dlen, 0)
    pp = datatypes.Vector(dlen, 0, dlen)
    pN = datatypes.Vector(dlen, 0, dlen * -1)
    Np = datatypes.Vector(dlen * -1, 0, dlen)
    NN = datatypes.Vector(dlen * -1, 0, dlen * -1)
    bottom = datatypes.Vector(0, -dlen, 0)

    v_array = [
        pp,
        top,
        pN,
        pp,
        Np,
        top,
        NN,
        Np,
        NN,
        pN,
        bottom,
        NN,
        bottom,
        Np,
        bottom,
        pp,
    ]

    points = getPointArrayWithOffset(v_array, pos_offset, rot_offset)

    node = curve.addCurve(parent, name, points, False, 1, m)

    setcolor(node, color)

    return node


def cubewithpeak(
    parent=None,
    name="cubewithpeak",
    width=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a CUBE WITH PEAK shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    dlen = width * 0.5

    peak = datatypes.Vector(0, width, 0)
    ppp = datatypes.Vector(dlen, dlen, dlen)
    ppN = datatypes.Vector(dlen, dlen, dlen * -1)
    pNp = datatypes.Vector(dlen, 0, dlen)
    Npp = datatypes.Vector(dlen * -1, dlen, dlen)
    pNN = datatypes.Vector(dlen, 0, dlen * -1)
    NNp = datatypes.Vector(dlen * -1, 0, dlen)
    NpN = datatypes.Vector(dlen * -1, dlen, dlen * -1)
    NNN = datatypes.Vector(dlen * -1, 0, dlen * -1)

    v_array = [
        peak,
        ppp,
        ppN,
        peak,
        NpN,
        ppN,
        NpN,
        peak,
        Npp,
        NpN,
        NNN,
        NNp,
        Npp,
        NpN,
        Npp,
        ppp,
        pNp,
        NNp,
        pNp,
        pNN,
        ppN,
        pNN,
        NNN,
    ]

    points = getPointArrayWithOffset(v_array, pos_offset, rot_offset)

    node = curve.addCurve(parent, name, points, False, 1, m)

    setcolor(node, color)

    return node


def sphere(
    parent=None,
    name="sphere",
    width=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
    degree=3,
):
    """Create a curve with a SPHERE shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    dlen = width * 0.5

    v0 = datatypes.Vector(0, 0, -dlen * 1.108)
    v1 = datatypes.Vector(dlen * 0.78, 0, -dlen * 0.78)
    v2 = datatypes.Vector(dlen * 1.108, 0, 0)
    v3 = datatypes.Vector(dlen * 0.78, 0, dlen * 0.78)
    v4 = datatypes.Vector(0, 0, dlen * 1.108)
    v5 = datatypes.Vector(-dlen * 0.78, 0, dlen * 0.78)
    v6 = datatypes.Vector(-dlen * 1.108, 0, 0)
    v7 = datatypes.Vector(-dlen * 0.78, 0, -dlen * 0.78)

    ro = datatypes.Vector([1.5708, 0, 0])

    points = getPointArrayWithOffset(
        [v0, v1, v2, v3, v4, v5, v6, v7], pos_offset, rot_offset
    )
    node = curve.addCurve(parent, name, points, True, degree, m)

    if rot_offset:
        rot_offset += ro
    else:
        rot_offset = ro
    points = getPointArrayWithOffset(
        [v0, v1, v2, v3, v4, v5, v6, v7], pos_offset, rot_offset
    )
    crv_0 = curve.addCurve(parent, node + "_0crv", points, True, degree, m)

    ro = datatypes.Vector([1.5708, 0, 1.5708])
    if rot_offset:
        rot_offset += ro
    else:
        rot_offset = ro
    points = getPointArrayWithOffset(
        [v0, v1, v2, v3, v4, v5, v6, v7], pos_offset, rot_offset + ro + ro
    )

    crv_1 = curve.addCurve(parent, node + "_1crv", points, True, degree, m)

    for crv in [crv_0, crv_1]:
        for shp in crv.listRelatives(shapes=True):
            node.addChild(shp, add=True, shape=True)
        pm.delete(crv)

    setcolor(node, color)

    return node


def arrow(
    parent=None,
    name="arrow",
    width=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a ARROW shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    dlen = width * 0.5

    v0 = datatypes.Vector(0, 0.3 * dlen, -dlen)
    v1 = datatypes.Vector(0, 0.3 * dlen, 0.3 * dlen)
    v2 = datatypes.Vector(0, 0.6 * dlen, 0.3 * dlen)
    v3 = datatypes.Vector(0, 0, dlen)
    v4 = datatypes.Vector(0, -0.6 * dlen, 0.3 * dlen)
    v5 = datatypes.Vector(0, -0.3 * dlen, 0.3 * dlen)
    v6 = datatypes.Vector(0, -0.3 * dlen, -dlen)

    points = getPointArrayWithOffset(
        [v0, v1, v2, v3, v4, v5, v6], pos_offset, rot_offset
    )

    node = curve.addCurve(parent, name, points, True, 1, m)

    setcolor(node, color)

    return node


def crossarrow(
    parent=None,
    name="crossArrow",
    width=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a CROSS ARROW shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    dlen = width * 0.5

    v0 = datatypes.Vector(0.2 * dlen, 0, 0.2 * dlen)
    v1 = datatypes.Vector(0.2 * dlen, 0, 0.6 * dlen)
    v2 = datatypes.Vector(0.4 * dlen, 0, 0.6 * dlen)
    v3 = datatypes.Vector(0, 0, dlen)
    v4 = datatypes.Vector(-0.4 * dlen, 0, 0.6 * dlen)
    v5 = datatypes.Vector(-0.2 * dlen, 0, 0.6 * dlen)
    v6 = datatypes.Vector(-0.2 * dlen, 0, 0.2 * dlen)
    v7 = datatypes.Vector(-0.6 * dlen, 0, 0.2 * dlen)
    v8 = datatypes.Vector(-0.6 * dlen, 0, 0.4 * dlen)
    v9 = datatypes.Vector(-dlen, 0, 0)
    v10 = datatypes.Vector(-0.6 * dlen, 0, -0.4 * dlen)
    v11 = datatypes.Vector(-0.6 * dlen, 0, -0.2 * dlen)
    v12 = datatypes.Vector(-0.2 * dlen, 0, -0.2 * dlen)
    v13 = datatypes.Vector(-0.2 * dlen, 0, -0.6 * dlen)
    v14 = datatypes.Vector(-0.4 * dlen, 0, -0.6 * dlen)
    v15 = datatypes.Vector(0, 0, -dlen)
    v16 = datatypes.Vector(0.4 * dlen, 0, -0.6 * dlen)
    v17 = datatypes.Vector(0.2 * dlen, 0, -0.6 * dlen)
    v18 = datatypes.Vector(0.2 * dlen, 0, -0.2 * dlen)
    v19 = datatypes.Vector(0.6 * dlen, 0, -0.2 * dlen)
    v20 = datatypes.Vector(0.6 * dlen, 0, -0.4 * dlen)
    v21 = datatypes.Vector(dlen, 0, 0)
    v22 = datatypes.Vector(0.6 * dlen, 0, 0.4 * dlen)
    v23 = datatypes.Vector(0.6 * dlen, 0, 0.2 * dlen)

    v_array = [
        v0,
        v1,
        v2,
        v3,
        v4,
        v5,
        v6,
        v7,
        v8,
        v9,
        v10,
        v11,
        v12,
        v13,
        v14,
        v15,
        v16,
        v17,
        v18,
        v19,
        v20,
        v21,
        v22,
        v23,
    ]
    points = getPointArrayWithOffset(v_array, pos_offset, rot_offset)

    node = curve.addCurve(parent, name, points, True, 1, m)

    setcolor(node, color)

    return node


def cross(
    parent=None,
    name="cross",
    width=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a CROSS shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    width = width * 0.35
    offset1 = width * 0.5
    offset2 = width * 1.5

    v0 = datatypes.Vector(width, offset2, 0)
    v1 = datatypes.Vector(offset2, width, 0)
    v2 = datatypes.Vector(offset1, 0, 0)

    v3 = datatypes.Vector(offset2, -width, 0)
    v4 = datatypes.Vector(width, -offset2, 0)
    v5 = datatypes.Vector(0, -offset1, 0)

    v6 = datatypes.Vector(-width, -offset2, 0)
    v7 = datatypes.Vector(-offset2, -width, 0)
    v8 = datatypes.Vector(-offset1, 0, 0)

    v9 = datatypes.Vector(-offset2, width, 0)
    v10 = datatypes.Vector(-width, offset2, 0)
    v11 = datatypes.Vector(0, offset1, 0)

    points = getPointArrayWithOffset(
        [v0, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11],
        pos_offset,
        rot_offset,
    )

    node = curve.addCurve(parent, name, points, True, 1, m)

    setcolor(node, color)

    return node


def null(
    parent=None,
    name="null",
    width=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a NULL shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    dlen = width * 0.5

    v0 = datatypes.Vector(dlen, 0, 0)
    v1 = datatypes.Vector(-dlen, 0, 0)
    v2 = datatypes.Vector(0, dlen, 0)
    v3 = datatypes.Vector(0, -dlen, 0)
    v4 = datatypes.Vector(0, 0, dlen)
    v5 = datatypes.Vector(0, 0, -dlen)

    points = getPointArrayWithOffset([v0, v1], pos_offset, rot_offset)
    node = curve.addCurve(parent, name, points, False, 1, m)

    points = getPointArrayWithOffset([v2, v3], pos_offset, rot_offset)
    crv_0 = curve.addCurve(parent, name, points, False, 1, m)

    points = getPointArrayWithOffset([v4, v5], pos_offset, rot_offset)
    crv_1 = curve.addCurve(parent, name, points, False, 1, m)

    for crv in [crv_0, crv_1]:
        for shp in crv.listRelatives(shapes=True):
            node.addChild(shp, add=True, shape=True)
        pm.delete(crv)

    setcolor(node, color)

    return node


def axis(
    parent=None,
    name="axis",
    width=1,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a AXIS shape.

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    dlen = width * 0.5

    v0 = datatypes.Vector(0, 0, 0)
    v1 = datatypes.Vector(dlen, 0, 0)
    v2 = datatypes.Vector(0, dlen, 0)
    v3 = datatypes.Vector(0, 0, dlen)

    points = getPointArrayWithOffset([v0, v1], pos_offset, rot_offset)
    node = curve.addCurve(parent, name, points, False, 1, m)
    setcolor(node, 4)

    points = getPointArrayWithOffset([v0, v2], pos_offset, rot_offset)
    crv_0 = curve.addCurve(parent, name, points, False, 1, m)
    setcolor(crv_0, 14)

    points = getPointArrayWithOffset([v0, v3], pos_offset, rot_offset)
    crv_1 = curve.addCurve(parent, name, points, False, 1, m)
    setcolor(crv_1, 6)

    for crv in [crv_0, crv_1]:
        for shp in crv.listRelatives(shapes=True):
            node.addChild(shp, add=True, shape=True)
        pm.delete(crv)

    return node


##########################################################
# Display helper Icons
##########################################################
def connection_display_curve(name, centers=[], degree=1):
    """Visual reference curves connectiong points.

    Display curve object is a simple curve to show the connection between
    different guide element..

    Args:
        name (str): Local name of the element.
        centers (list of dagNode):  List of object to define the curve.
        degree (int): Curve degree. Default 1 = lineal.

    Returns:
        dagNode: The newly creted curve.

    """
    crv = curve.addCnsCurve(centers[0], name, centers, degree)
    crv.attr("overrideEnabled").set(1)
    crv.attr("overrideDisplayType").set(1)

    return crv


def direction_arrow(
    axis="z", length=1, name="direction_arrow", parent_name=None
):
    """
    Creates a curve shaped like an arrow, aligned with a specified axis and length.

    Args:
        parent_name (str): The name of the parent object. The arrow is created
            relative to its local axis.
        axis (str): The axis for the arrow direction ('x', 'y', 'z', '-x', '-y', '-z').
        length (float): The length of the arrow.

    Returns:
        str: The name of the created arrow curve.
    """
    # Validate axis input
    valid_axes = ["x", "y", "z", "-x", "-y", "-z"]
    if axis not in valid_axes:
        raise ValueError(
            "Invalid axis '{}'. Must be one of: {}".format(axis, valid_axes)
        )

    # Define arrow points in local space
    size_ratio = 0.9
    tip = [0, 0, length]
    base1 = [-0.1 * length, 0, size_ratio * length]
    base2 = [0.1 * length, 0, size_ratio * length]
    base3 = [-0.05 * length, 0, size_ratio * length]
    base4 = [0.05 * length, 0, size_ratio * length]
    shaft_start = [0, 0, 0]
    shaft_end = [0, 0, size_ratio * length]

    # Assemble the arrow shape
    points = [
        shaft_start,
        shaft_end,
        base4,
        base2,
        tip,
        base1,
        base3,
        shaft_end,
    ]

    # Transform points to match the axis
    for i in range(len(points)):
        if axis == "x":
            points[i] = [points[i][2], points[i][1], points[i][0]]
        elif axis == "-x":
            points[i] = [-points[i][2], points[i][1], points[i][0]]
        elif axis == "y":
            points[i] = [points[i][0], points[i][2], points[i][1]]
        elif axis == "-y":
            points[i] = [points[i][0], -points[i][2], points[i][1]]
        elif axis == "-z":
            points[i] = [points[i][0], points[i][1], -points[i][2]]

    # Create the curve
    arrow_curve = cmds.curve(p=points, d=1, n=name)

    if parent_name:
        cmds.parent(arrow_curve, parent_name)

    return pm.PyNode(arrow_curve)


##########################################################
# Guide Icons
##########################################################


def guideRootIcon(
    parent=None,
    name="root",
    width=0.5,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a ROOT GUIDE shape.

    Note:
        This icon is specially design for **Shifter** root guides

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    rootIco = null(parent, name, width, color, m, pos_offset, rot_offset)
    cubeWidth = width / 2.0
    cubeIco = cube(
        parent,
        name,
        cubeWidth,
        cubeWidth,
        cubeWidth,
        color,
        m,
        pos_offset,
        rot_offset,
    )

    for shp in cubeIco.listRelatives(shapes=True):
        rootIco.addChild(shp, add=True, shape=True)
    pm.delete(cubeIco)

    attribute.setNotKeyableAttributes(rootIco)
    rootIco.addAttr("isGearGuide", at="bool", dv=True)
    # Set the control shapes isHistoricallyInteresting
    for oShape in rootIco.getShapes():
        oShape.isHistoricallyInteresting.set(False)

    return rootIco


def guideRootIcon2D(
    parent=None,
    name="root",
    width=0.5,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a 2D ROOT GUIDE shape.

    Note:
        This icon is specially design for **Shifter** root guides

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    rootIco = null(parent, name, width, color, m, pos_offset, rot_offset)
    pm.delete(rootIco.getShapes()[-1])  # Remove the z axis

    rot_offset_orig = datatypes.Vector(math.radians(90), 0, 0)
    if rot_offset:
        rot_offset_orig.rotateBy(rot_offset)

    squareWidth = width / 2.0
    squareIco = square(
        parent,
        name,
        squareWidth,
        squareWidth,
        color,
        m,
        pos_offset,
        rot_offset_orig,
    )

    for shp in squareIco.listRelatives(shapes=True):
        rootIco.addChild(shp, add=True, shape=True)
    pm.delete(squareIco)

    attribute.setNotKeyableAttributes(rootIco)
    rootIco.addAttr("isGearGuide", at="bool", dv=True)
    # Set the control shapes isHistoricallyInteresting
    for oShape in rootIco.getShapes():
        oShape.isHistoricallyInteresting.set(False)

    return rootIco


def guideLocatorIcon(
    parent=None,
    name="locator",
    width=0.5,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a LOCATOR GUIDE shape.

    Note:
        This icon is specially design for **Shifter** locator guides

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        width (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.
    """
    rootIco = null(parent, name, width, color, m, pos_offset, rot_offset)
    spheWidth = width / 2.0

    sphereIco = sphere(
        parent, name, spheWidth, color, m, pos_offset, rot_offset, degree=3
    )

    for shp in sphereIco.listRelatives(shapes=True):
        rootIco.addChild(shp, add=True, shape=True)
    pm.delete(sphereIco)

    attribute.setNotKeyableAttributes(rootIco)
    rootIco.addAttr("isGearGuide", at="bool", dv=True)
    # Set the control shapes isHistoricallyInteresting
    for oShape in rootIco.getShapes():
        oShape.isHistoricallyInteresting.set(False)

    return rootIco


def guideBladeIcon(
    parent=None,
    name="blade",
    lenX=1.0,
    color=[0, 0, 0],
    m=datatypes.Matrix(),
    pos_offset=None,
    rot_offset=None,
):
    """Create a curve with a BLADE GUIDE shape.

    Note:
        This icon is specially design for **Shifter** blade guides

    Arguments:
        parent (dagNode): The parent object of the newly created curve.
        name (str): Name of the curve.
        lenX (float): Width of the shape.
        color (int or list of float): The color in index base or RGB.
        m (matrix): The global transformation of the curve.
        pos_offset (vector): The xyz position offset of the curve from
            its center.
        rot_offset (vector): The xyz rotation offset of the curve from
            its center. xyz in radians

    Returns:
        dagNode: The newly created icon.

    """
    v0 = datatypes.Vector(0, 0, 0)
    v1 = datatypes.Vector(lenX / 2, 0, 0)
    v2 = datatypes.Vector(lenX, lenX / 4, 0)
    v3 = datatypes.Vector(lenX / 2, lenX / 2, 0)
    v4 = datatypes.Vector(0, lenX / 2, 0)

    points = getPointArrayWithOffset(
        [v0, v1, v2, v3, v4], pos_offset, rot_offset
    )

    bladeIco = curve.addCurve(parent, name, points, True, 1, m)

    setcolor(bladeIco, color)

    attribute.setNotKeyableAttributes(bladeIco)
    attribute.unlockAttribute(
        bladeIco,
        attributes=[
            "tx",
            "ty",
            "tz",
            "rx",
            "ry",
            "rz",
            "sx",
            "sy",
            "sz",
            "v",
            "ro",
        ],
    )
    # bladeIco.scale.set(1, 1, 1)
    # Set the control shapes isHistoricallyInteresting
    for oShape in bladeIco.getShapes():
        oShape.isHistoricallyInteresting.set(False)

    return bladeIco


##########################################################
# MISC
##########################################################
# ========================================================


def getPointArrayWithOffset(point_pos, pos_offset=None, rot_offset=None):
    """Get Point array with offset

    Convert a list of vector to a List of float and add the position and
    rotation offset.

    Arguments:
        point_pos (list of vector): Point positions.
        pos_offset (vector):  The position offset of the curve from its
            center.
        rot_offset (vector): The rotation offset of the curve from its
            center. In radians.

    Returns:
        list of vector: the new point positions

    """
    points = []
    for v in point_pos:
        if rot_offset:
            mv = om.MVector(v.x, v.y, v.z)
            mv = mv.rotateBy(
                om.MEulerRotation(
                    rot_offset.x,
                    rot_offset.y,
                    rot_offset.z,
                    om.MEulerRotation.kXYZ,
                )
            )
            v = datatypes.Vector(mv.x, mv.y, mv.z)
        if pos_offset:
            v = v + pos_offset

        points.append(v)

    return points


def setcolor(node, color):
    """Set the color in the Icons.

    Arguments:
        node(dagNode): The object
        color (int or list of float): The color in index base or RGB.


    """
    # TODO: configure this funcion to work with RGB or Index color base
    # on Maya version.
    # version = mgear.core.getMayaver()

    curve.set_color(node, color)
