from maya import cmds
from maya.api import OpenMaya
from maya import OpenMaya as om
from . import base
import math


def degrees(*args):
    if isinstance(args[0], OpenMaya.MEulerRotation):
        return args[0].__class__(
            math.degrees(args[0].x),
            math.degrees(args[0].y),
            math.degrees(args[0].z),
            args[0].order,
        )

    return math.degrees(*args)


class UndoChunk(object):
    def __init__(self):
        super(UndoChunk, self).__init__()

    def __enter__(self):
        cmds.undoInfo(ock=True)

    def __exit__(self, exc_type, exc_value, traceback):
        cmds.undoInfo(cck=True)


class NameParser(object):
    def __init__(self, name_or_node):
        super(NameParser, self).__init__()
        self.__name_or_node = name_or_node

    def stripNamespace(self):
        n = self.__name_or_node
        if isinstance(n, base.Base):
            n = n.name()

        return "|".join([x.split(":")[-1] for x in n.split("|")])


def to_mspace(space, as_api2=True):
    if isinstance(space, int):
        return space

    if as_api2:
        if space == "transform":
            return OpenMaya.MSpace.kTransform
        elif space == "preTransform":
            return OpenMaya.MSpace.kPreTransform
        elif space == "postTransform":
            return OpenMaya.MSpace.kPostTransform
        elif space == "world":
            return OpenMaya.MSpace.kWorld
        elif space == "object":
            return OpenMaya.MSpace.kObject

        return OpenMaya.MSpace.kInvalid
    else:
        if space == "transform":
            return om.MSpace.kTransform
        elif space == "preTransform":
            return om.MSpace.kPreTransform
        elif space == "postTransform":
            return om.MSpace.kPostTransform
        elif space == "world":
            return om.MSpace.kWorld
        elif space == "object":
            return om.MSpace.kObject

        return om.MSpace.kInvalid


def cross(a, b):
    """
    Computes the cross product of two vectors, supporting both OpenMaya.MVector
    from the API and the original API, while also supporting lists representing
    3D vectors. Non-api OpenMaya.MVector is converted to api.OpenMaya.MVector.

    Args:
        a (MVector or list): The first vector, either an OpenMaya.MVector
                             (api or non-api) or a list of three float values [x, y, z].
        b (MVector or list): The second vector, either an OpenMaya.MVector
                             (api or non-api) or a list of three float values [x, y, z].

    Returns:
        MVector: The cross product of the two vectors in the format of
                 api.OpenMaya.MVector.
    """
    # Convert list to api.OpenMaya.MVector
    if isinstance(a, list):
        a = OpenMaya.MVector(a[0], a[1], a[2])
    elif isinstance(a, om.MVector):  # If it's non-api OpenMaya, convert it
        a = OpenMaya.MVector(a.x, a.y, a.z)
    elif not isinstance(a, OpenMaya.MVector):
        raise TypeError(
            "Argument 'a' must be an MVector or a list of length 3"
        )

    # Same check for b
    if isinstance(b, list):
        b = OpenMaya.MVector(b[0], b[1], b[2])
    elif isinstance(b, om.MVector):  # Convert non-api OpenMaya to api
        b = OpenMaya.MVector(b.x, b.y, b.z)
    elif not isinstance(b, OpenMaya.MVector):
        raise TypeError(
            "Argument 'b' must be an MVector or a list of length 3"
        )

    # Return the cross product in api.OpenMaya.MVector format
    return a ^ b
