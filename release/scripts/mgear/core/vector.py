"""Functions to work with vectors"""

import math
import maya.cmds as cmds
import maya.OpenMaya as OpenMaya

from mgear.pymaya import datatypes
from mgear.core import utils


#############################################
# VECTOR OPERATIONS
#############################################
def getDistance(v0, v1):
    """Get the distance between 2 vectors

    Arguments:
        v0 (vector): vector A.
        v1 (vector): vector B.

    Returns:
        float: Distance length.

    """
    v = v1 - v0

    return v.length()


@utils.ensure_pynode
def getDistance2(obj0, obj1):
    """Get the distance between 2 objects.

    Arguments:
        obj0 (dagNode): Object A
        obj1 (dagNode): Object B

    Returns:
        float: Distance length

    """
    v0 = obj0.getTranslation(space="world")
    v1 = obj1.getTranslation(space="world")

    v = v1 - v0

    return v.length()


def get_mvector(obj):
    """Get MVector position of an object in world space.

    Args:
        obj (str): Object name.

    Returns:
        OpenMaya.MVector: Position in world space.
    """
    pos = cmds.xform(obj, q=True, ws=True, t=True)
    return OpenMaya.MVector(pos[0], pos[1], pos[2])


def linearlyInterpolate(v0, v1, blend=.5):
    """Get the vector interpolated between 2 vectors.

    Arguments:
        v0 (vector): vector A.
        v1 (vector): vector B.
        blend (float): Blending value.

    Returns:
        vector: The interpolated vector.

    """
    vector = v1 - v0
    vector *= blend
    vector += v0

    return vector


def getPlaneNormal(v0, v1, v2):
    """Get the normal vector of a plane (Defined by 3 positions).

    Arguments:
        v0 (vector): First position on the plane.
        v1 (vector): Second position on the plane.
        v2 (vector): Third position on the plane.

    Returns:
        vector: The normal.

    """
    vector0 = v1 - v0
    vector1 = v2 - v0
    vector0.normalize()
    vector1.normalize()

    normal = vector1 ^ vector0
    normal.normalize()

    return normal


def getPlaneBiNormal(v0, v1, v2):
    """Get the binormal vector of a plane (Defined by 3 positions).

    Arguments:
        v0 (vector): First position on the plane.
        v1 (vector): Second position on the plane.
        v2 (vector): Third position on the plane.

    Returns:
        vector: The binormal.

    """
    normal = getPlaneNormal(v0, v1, v2)

    vector0 = v1 - v0

    binormal = normal ^ vector0
    binormal.normalize()

    return binormal


def getTransposedVector(v, position0, position1, inverse=False):
    """Get the transposed vector.

    Arguments:
        v (vector): Input Vector.
        position0 (vector): Position A.
        position1 (vector): Position B.
        inverse (bool): Invert the rotation.

    Returns:
        vector: The transposed vector.

    >>> normal = vec.getTransposedVector(self.normal,
                                         [self.guide.apos[0],
                                          self.guide.apos[1]],
                                         [self.guide.apos[-2],
                                          self.guide.apos[-1]])

    """
    v0 = position0[1] - position0[0]
    v0.normalize()

    v1 = position1[1] - position1[0]
    v1.normalize()

    ra = v0.angle(v1)

    if inverse:
        ra = -ra

    axis = v0 ^ v1

    vector = rotateAlongAxis(v, axis, ra)

    # Check if the rotation has been set in the right order
    # ra2 = (math.pi *.5 ) - v1.angle(vector)
    # vector = rotateAlongAxis(v, axis, -ra2)

    return vector


def rotateAlongAxis(v, axis, a):
    """Rotate a vector around a given axis defined by other vector.

    Arguments:
        v (vector): The vector to rotate.
        axis (vector): The axis to rotate around.
        a (float): The rotation angle in radians.

    """
    sa = math.sin(a / 2.0)
    ca = math.cos(a / 2.0)

    q1 = OpenMaya.MQuaternion(v.x, v.y, v.z, 0)
    q2 = OpenMaya.MQuaternion(axis.x * sa, axis.y * sa, axis.z * sa, ca)
    q2n = OpenMaya.MQuaternion(-axis.x * sa, -axis.y * sa, -axis.z * sa, ca)
    q = q2 * q1
    q *= q2n

    out = OpenMaya.MVector(q.x, q.y, q.z)

    return out


def calculatePoleVector(p1, p2, p3, poleDistance=1, time=1):
    """
    This function takes 3  PyNodes as inputs.
    Creates a pole vector position at a "nice" distance away from a triangle
    of positions.
    Normalizes the bone lengths relative to the knee to calculate straight
    ahead without shifting up and down if the bone lengths are different.
    Returns a pymel.core.datatypes.Vector

    Arguments:
        p1 (dagNode): Object A
        p2 (dagNode): Object B
        p3 (dagNode): Object C
        poleDistance (float): distance of the pole vector from the mid point

    Returns:
        vector: The transposed vector.
    """

    vec1 = p1.worldMatrix.get(time=time).translate
    vec2 = p2.worldMatrix.get(time=time).translate
    vec3 = p3.worldMatrix.get(time=time).translate

    # 1. Calculate a "nice distance" based on average of the two bone lengths.
    leg_length = (vec2 - vec1).length()
    knee_length = (vec3 - vec2).length()
    distance = (leg_length + knee_length) * 0.5 * poleDistance

    # 2. Normalize the length of leg and ankle, relative to the knee.
    # This will ensure that the pole vector goes STRAIGHT ahead of the knee
    # Avoids up-down offset if there is a length difference between the two
    # bones.
    vec1norm = ((vec1 - vec2).normal() * distance) + vec2
    vec3norm = ((vec3 - vec2).normal() * distance) + vec2

    # 3. given 3 points, calculate a pole vector position
    mid = vec1norm + (vec2 - vec1norm).projectionOnto(vec3norm - vec1norm)

    # 4. Move the pole vector in front of the knee by the "nice distance".
    mid_pointer = vec2 - mid
    pole_vector = (mid_pointer.normal() * distance) + vec2

    return pole_vector


def subtract_3Dvectors_list(vec_a, vec_b):
    """Subtract two 3D vectors represented as lists.

    Args:
        vec_a (list): First vector [x, y, z].
        vec_b (list): Second vector [x, y, z].

    Returns:
        list: Resulting vector after subtraction.
    """
    if len(vec_a) != 3 or len(vec_b) != 3:
        raise ValueError("Both vectors must have 3 elements.")

    return [a - b for a, b in zip(vec_a, vec_b)]


def add_3Dvectors_list(vec_a, vec_b):
    """Add two 3D vectors represented as lists.

    Args:
        vec_a (list): First vector [x, y, z].
        vec_b (list): Second vector [x, y, z].

    Returns:
        list: Resulting vector after addition.
    """
    if len(vec_a) != 3 or len(vec_b) != 3:
        raise ValueError("Both vectors must have 3 elements.")

    return [a + b for a, b in zip(vec_a, vec_b)]


##########################################################
# CLASS
##########################################################
class Blade(object):
    """The Blade object for shifter guides"""

    def __init__(self, t=datatypes.Matrix()):

        self.transform = t
        mdata = t.get()
        d = [mdata[j][i]
             for j in range(len(mdata))
             for i in range(len(mdata[0]))]

        m = OpenMaya.MMatrix()
        OpenMaya.MScriptUtil.createMatrixFromList(d, m)
        m = OpenMaya.MTransformationMatrix(m)

        x = OpenMaya.MVector(1, 0, 0).rotateBy(m.rotation())
        y = OpenMaya.MVector(0, 1, 0).rotateBy(m.rotation())
        z = OpenMaya.MVector(0, 0, 1).rotateBy(m.rotation())

        self.x = datatypes.Vector(x.x, x.y, x.z)
        self.y = datatypes.Vector(y.x, y.y, y.z)
        self.z = datatypes.Vector(z.x, z.y, z.z)
