import math
from maya.api import OpenMaya
from . import util


degrees = util.degrees
Space = OpenMaya.MSpace


def _warp_dt(func):
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if isinstance(res, OpenMaya.MVector):
            return Vector(res)
        elif isinstance(res, OpenMaya.MPoint):
            return Point(res)
        elif isinstance(res, OpenMaya.MMatrix):
            return Matrix(res)
        elif isinstance(res, OpenMaya.MTransformationMatrix):
            return TransformationMatrix(res.asMatrix())
        else:
            return res

    return wrapper


class Vector(OpenMaya.MVector):
    WRAP_FUNCS = []
    for fn in dir(OpenMaya.MVector):
        if not fn.startswith("_"):
            f = getattr(OpenMaya.MVector, fn)
            if callable(f):
                WRAP_FUNCS.append(fn)

    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            args = list(args)
            if isinstance(args[0], (list, tuple)) and len(args[0]) == 1:
                l = list(args[0])
                args[0] = l * 3
            elif isinstance(args[0], (int, float)):
                args[0] = [args[0]] * 3

        super(Vector, self).__init__(*args, **kwargs)
        for fn in Vector.WRAP_FUNCS:
            setattr(
                self, fn, _warp_dt(super(Vector, self).__getattribute__(fn))
            )

    def __getitem__(self, item):
        return [self.x, self.y, self.z][item]

    def __add__(self, other):
        """Override addition to return a Vector instead of MVector."""
        return Vector(super(Vector, self).__add__(other))

    def __sub__(self, other):
        """Override subtraction to return a Vector instead of MVector."""
        return Vector(super(Vector, self).__sub__(other))

    def __mul__(self, other):
        """Override multiplication to return a Vector or scalar product."""
        result = super(Vector, self).__mul__(other)
        if isinstance(other, (int, float)):  # Scalar multiplication
            return Vector(result)
        return result  # Dot product returns a scalar

    def __truediv__(self, other):
        """Override division to return a Vector."""
        return Vector(super(Vector, self).__truediv__(other))

    def __neg__(self):
        """Override negation to return a Vector."""
        return Vector(super(Vector, self).__neg__())

    def tolist(self):
        return [self.x, self.y, self.z]

    def get(self):
        return self.tolist()

    def rotateBy(self, *args):
        if args:
            if len(args) == 2 and isinstance(args[0], Vector):
                return Vector(
                    super(Vector, self).rotateBy(
                        Quaternion(float(args[1]), args[0])
                    )
                )
            elif len(args) == 1 and isinstance(args[0], Matrix):
                return Vector(
                    super(Vector, self).rotateBy(
                        TransformationMatrix(args[0]).rotation(True)
                    )
                )
            else:
                return Vector(
                    super(Vector, self).rotateBy(EulerRotation(*args))
                )
        else:
            return self

    def projectionOnto(self, pVector):
        """Project this vector onto anpVector vector.

        Args:
            pVector (Vector): The vector onto which to project this vector.

        Returns:
            Vector: The projected vector.
        """
        pVector = Vector(pVector)  # Ensure input is a Vector
        scale = (self * pVector) / (pVector * pVector)
        return pVector * scale


class Point(OpenMaya.MPoint):
    WRAP_FUNCS = []
    for fn in dir(OpenMaya.MPoint):
        if not fn.startswith("_"):
            f = getattr(OpenMaya.MPoint, fn)
            if callable(f):
                WRAP_FUNCS.append(fn)

    def __init__(self, *args, **kwargs):
        super(Point, self).__init__(*args, **kwargs)
        for fn in Point.WRAP_FUNCS:
            setattr(
                self, fn, _warp_dt(super(Point, self).__getattribute__(fn))
            )

    def tolist(self):
        return [self.x, self.y, self.z]

    def asVector(self):
        return Vector(self.x, self.y, self.z)

    def __getitem__(self, item):
        return [self.x, self.y, self.z, self.w][item]


class Matrix(OpenMaya.MMatrix):
    WRAP_FUNCS = []
    for fn in dir(OpenMaya.MMatrix):
        if not fn.startswith("_"):
            f = getattr(OpenMaya.MMatrix, fn)
            if callable(f):
                WRAP_FUNCS.append(fn)

    def __init__(self, *args, **kwargs):
        if len(args) == 16:
            args = (args,)
        super(Matrix, self).__init__(*args, **kwargs)
        for fn in Matrix.WRAP_FUNCS:
            setattr(
                self, fn, _warp_dt(super(Matrix, self).__getattribute__(fn))
            )

    def get(self):
        gt = super(Matrix, self).__getitem__
        return (
            (gt(0), gt(1), gt(2), gt(3)),
            (gt(4), gt(5), gt(6), gt(7)),
            (gt(8), gt(9), gt(10), gt(11)),
            (gt(12), gt(13), gt(14), gt(15)),
        )

    def __setitem__(self, index, value):
        if index < 0 or index > 3:
            raise Exception("list index out of range")

        if len(value) > 4:
            raise Exception("over 4 values given")

        for i, v in enumerate(value):
            super(Matrix, self).__setitem__(index * 4 + i, v)

    def __getitem__(self, index):
        if index < 0 or index > 3:
            raise Exception("list index out of range")

        gt = super(Matrix, self).__getitem__
        return [
            gt(index * 4),
            gt(index * 4 + 1),
            gt(index * 4 + 2),
            gt(index * 4 + 3),
        ]

    @property
    def translate(self):
        return TransformationMatrix(self).getTranslation(Space.kTransform)


def _trnsfrommatrix_wrp(func, this):
    def wrapper(*args, **kwargs):
        return getattr(OpenMaya.MTransformationMatrix(this), func)(
            *args, **kwargs
        )

    return _warp_dt(wrapper)


class TransformationMatrix(Matrix):
    WRAP_FUNCS = []
    ORG_MEMS = []
    for fn in dir(OpenMaya.MTransformationMatrix):
        if not fn.startswith("_"):
            f = getattr(OpenMaya.MTransformationMatrix, fn)
            if callable(f):
                WRAP_FUNCS.append(fn)

    def __init__(self, *args, **kwargs):
        super(TransformationMatrix, self).__init__(*args, **kwargs)
        for fn in TransformationMatrix.WRAP_FUNCS:
            if not hasattr(self, fn):
                setattr(self, fn, _trnsfrommatrix_wrp(fn, self))
        for m in TransformationMatrix.ORG_MEMS:
            setattr(self, m, getattr(OpenMaya.MTransformationMatrix, m))

    def __repr__(self):
        return (
            super(TransformationMatrix, self)
            .__repr__()
            .replace("MMatrix", "TransformationMatrix")
        )

    def get(self):
        return self.asMatrix().get()

    def __copy(self, other):
        if not isinstance(other, Matrix):
            other = Matrix(other)
        self[0] = other[0]
        self[1] = other[1]
        self[2] = other[2]
        self[3] = other[3]

    def setRotationQuaternion(self, x, y, z, w):
        t = OpenMaya.MTransformationMatrix(self)
        t.setRotation(Quaternion(x, y, z, w))
        self.__copy(t.asMatrix())

    def getRotationQuaternion(self):
        q = self.rotation().asQuaternion()
        return (q.x, q.y, q.z, q.w)

    def getRotation(self):
        return self.rotation()

    def setRotation(self, *args):
        if len(args) == 1 and isinstance(args[0], list):
            args = args[0]
        t = OpenMaya.MTransformationMatrix(self)
        t.setRotation(EulerRotation(*[math.radians(x) for x in args]))
        self.__copy(t.asMatrix())

    def getScale(self, space):
        return self.scale(util.to_mspace(space))

    def setScale(self, scale, space):
        t = OpenMaya.MTransformationMatrix(self)
        t.setScale(scale, util.to_mspace(space))
        self.__copy(t.asMatrix())

    def setShear(self, shear, space):
        t = OpenMaya.MTransformationMatrix(self)
        t.setShear(shear, util.to_mspace(space))
        self.__copy(t.asMatrix())

    def getShear(self, space):
        return self.shear(util.to_mspace(space))

    def setTranslation(self, vector, space):
        t = OpenMaya.MTransformationMatrix(self)
        t.setTranslation(vector, util.to_mspace(space))
        self.__copy(t.asMatrix())

    def getTranslation(self, space):
        return self.translation(util.to_mspace(space))


class BoundingBox(OpenMaya.MBoundingBox):
    WRAP_FUNCS = []
    for fn in dir(OpenMaya.MBoundingBox):
        if not fn.startswith("_"):
            f = getattr(OpenMaya.MBoundingBox, fn)
            if callable(f):
                WRAP_FUNCS.append(fn)

    def __init__(self, *args, **kwargs):
        nargs = []
        for arg in args:
            if isinstance(arg, (list, tuple)):
                arg = Point(arg)
            nargs.append(arg)

        super(BoundingBox, self).__init__(*nargs, **kwargs)
        for fn in BoundingBox.WRAP_FUNCS:
            setattr(
                self,
                fn,
                _warp_dt(super(BoundingBox, self).__getattribute__(fn)),
            )

    def __getitem__(self, index):
        if index == 0:
            return Point(self.min)
        elif index == 1:
            return Point(self.max)
        else:
            raise Exception("Index out of range")


class Quaternion(OpenMaya.MQuaternion):
    WRAP_FUNCS = []
    for fn in dir(OpenMaya.MQuaternion):
        if not fn.startswith("_"):
            f = getattr(OpenMaya.MQuaternion, fn)
            if callable(f):
                WRAP_FUNCS.append(fn)

    def __init__(self, *args, **kwargs):
        super(Quaternion, self).__init__(*args, **kwargs)

        for fn in Quaternion.WRAP_FUNCS:
            setattr(
                self,
                fn,
                _warp_dt(super(Quaternion, self).__getattribute__(fn)),
            )

    def scaleIt(self, scal):
        return Quaternion(
            self.x * scal, self.y * scal, self.z * scal, self.w * scal
        )


class EulerRotation(OpenMaya.MEulerRotation):
    WRAP_FUNCS = []
    for fn in dir(OpenMaya.MEulerRotation):
        if not fn.startswith("_"):
            f = getattr(OpenMaya.MEulerRotation, fn)
            if callable(f):
                WRAP_FUNCS.append(fn)

    def __init__(self, *args, **kwargs):
        super(EulerRotation, self).__init__(*args, **kwargs)

        for fn in EulerRotation.WRAP_FUNCS:
            setattr(
                self,
                fn,
                _warp_dt(super(EulerRotation, self).__getattribute__(fn)),
            )


__all__ = [
    "Vector",
    "EulerRotation",
    "Matrix",
    "TransformationMatrix",
    "Quaternion",
    "degrees",
    "Point",
    "BoundingBox",
    "Space",
]
