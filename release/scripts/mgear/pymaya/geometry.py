import re
from maya.api import OpenMaya
from maya import OpenMaya as om
from maya import cmds
from . import base
from . import datatypes
from . import exception
from . import util


_SELECTION_LIST = OpenMaya.MSelectionList()


class _Geometry(base.Geom):
    @classmethod
    def Match(cls, dagpath, component):
        return False

    @staticmethod
    def __getComponent(nodename):
        _SELECTION_LIST.clear()
        try:
            _SELECTION_LIST.add(nodename)
        except RuntimeError:
            return (None, None)

        dag, comp = _SELECTION_LIST.getComponent(0)
        if comp.isNull():
            return (None, None)

        return (dag, comp)

    def __iter__(self):
        return iter([])

    def __hash__(self):
        return hash(self.name())

    def __init__(self, nodename_or_dagpath, component):
        super(_Geometry, self).__init__()
        if isinstance(nodename_or_dagpath, OpenMaya.MDagPath):
            if not isinstance(
                component, OpenMaya.MObject
            ) or not component.hasFn(OpenMaya.MFn.kComponent):
                raise exception.MayaGeometryError("Invalid component given")
            self.__dagpath = nodename_or_dagpath
            self.__component = component
        else:
            self.__dagpath, self.__component = _Geometry.__getComponent(
                nodename_or_dagpath
            )
            if self.__dagpath is None or self.__component is None:
                raise exception.MayaGeometryError(
                    "No such geometry '{}'".format(nodename_or_dagpath)
                )

    def __str__(self):
        """Return the  name as a string."""
        return self.name()

    def dagPath(self):
        return self.__dagpath

    def component(self):
        return self.__component


class _SingleIndexGeom(_Geometry):
    @classmethod
    def IterClass(cls):
        raise Exception("IterClass is not implemeted yet")

    @classmethod
    def ComponentType(cls):
        raise Exception("ComponentType is not implemeted yet")

    @classmethod
    def AttrName(cls):
        raise Exception("AttrName is not implemeted yet")

    def __init__(self, nodename_or_dagpath, component):
        super(_SingleIndexGeom, self).__init__(nodename_or_dagpath, component)
        self.__indices = None

    def __indices_str(self):
        indices = self.indices()
        latest = None
        grps = []

        for id in sorted(indices):
            if latest is None:
                latest = id
                grps.append([id])
            elif latest + 1 == id:
                grps[-1].append(id)
            else:
                grps.append([id])
            latest = id

        ts = []
        for grp in grps:
            if len(grp) == 1:
                ts.append(str(grp[0]))
            else:
                ts.append("{}:{}".format(grp[0], grp[-1]))

        return ",".join(ts)

    def indices(self):
        if self.__indices is None:
            indices_set = set()
            it = self.IterClass()(self.dagPath(), self.component())
            while not it.isDone():
                indices_set.add(it.index())
                it.next()
            # Cache as list to avoid repeated set-to-list conversions
            self.__indices = list(indices_set)

        return self.__indices

    def toStringList(self):
        names = []
        for i in self.indices():
            names.append(
                self.dagPath().partialPathName()
                + ".{}[{}]".format(self.AttrName(), i)
            )
        return names

    def name(self):
        return self.dagPath().partialPathName() + ".{}[{}]".format(
            self.AttrName(), self.__indices_str()
        )

    def index(self):
        return self.indices()[0]

    def __iter__(self):
        it = self.IterClass()(self.dagPath(), self.component())
        while not it.isDone():
            comp = OpenMaya.MFnSingleIndexedComponent()
            comp_obj = comp.create(self.ComponentType())
            comp.addElement(it.index())
            it.next()
            yield self.__class__(self.dagPath(), comp_obj)

    def __getitem__(self, index):
        self.indices()

        indices = []
        if isinstance(index, (list, tuple)):
            for ind in index:
                if isinstance(ind, slice):
                    indices.extend(range(ind.start, ind.stop + 1))
                else:
                    indices.append(ind)
        elif isinstance(index, slice):
            indices.extend(range(index.start, index.stop + 1))
        else:
            indices = [index]

        comp = OpenMaya.MFnSingleIndexedComponent()
        comp_obj = comp.create(self.ComponentType())
        for id in indices:
            if not id in self.__indices:
                raise Exception("index out of range")

            comp.addElement(id)

        return self.__class__(self.dagPath(), comp_obj)


class MeshVertex(_SingleIndexGeom):
    @classmethod
    def Match(cls, dagpath, component):
        return component.hasFn(OpenMaya.MFn.kMeshVertComponent)

    @classmethod
    def IterClass(cls):
        return OpenMaya.MItMeshVertex

    @classmethod
    def ComponentType(cls):
        return OpenMaya.MFn.kMeshVertComponent

    @classmethod
    def AttrName(cls):
        return "vtx"

    def __init__(self, nodename_or_dagpath, component):
        super(MeshVertex, self).__init__(
            nodename_or_dagpath, component=component
        )

    def getPosition(self, space="preTransform"):
        it = OpenMaya.MItMeshVertex(self.dagPath(), self.component())
        return datatypes.Point(it.position(util.to_mspace(space))).asVector()

    def connectedEdges(self):
        it = OpenMaya.MItMeshVertex(self.dagPath(), self.component())
        comp = OpenMaya.MFnSingleIndexedComponent()
        comp_obj = comp.create(OpenMaya.MFn.kMeshEdgeComponent)
        for ei in it.getConnectedEdges():
            comp.addElement(ei)

        return MeshEdge(self.dagPath(), comp_obj)

    def connectedFaces(self):
        it = OpenMaya.MItMeshVertex(self.dagPath(), self.component())
        comp = OpenMaya.MFnSingleIndexedComponent()
        comp_obj = comp.create(OpenMaya.MFn.kMeshPolygonComponent)
        for ei in it.getConnectedFaces():
            comp.addElement(ei)

        return MeshFace(self.dagPath(), comp_obj)

    def connectedVertices(self):
        """Returns a MeshVertex object containing vertices connected to this vertex.

        Returns:
            MeshVertex: The connected vertices as a MeshVertex object.
        """
        it = OpenMaya.MItMeshVertex(self.dagPath(), self.component())

        connected_verts = it.getConnectedVertices()

        # Create a component to store the connected vertices
        comp = OpenMaya.MFnSingleIndexedComponent()
        comp_obj = comp.create(OpenMaya.MFn.kMeshVertComponent)

        for vi in connected_verts:
            comp.addElement(vi)

        return MeshVertex(self.dagPath(), comp_obj)

    def isOnBoundary(self):
        """Check if the vertex is on the boundary of the mesh.

        Returns:
            bool: True if the vertex is on the boundary, False otherwise.
        """
        it = OpenMaya.MItMeshVertex(self.dagPath(), self.component())
        return it.onBoundary()


class MeshFace(_SingleIndexGeom):
    @classmethod
    def Match(cls, dagpath, component):
        return component.hasFn(OpenMaya.MFn.kMeshPolygonComponent)

    @classmethod
    def IterClass(cls):
        return OpenMaya.MItMeshPolygon

    @classmethod
    def ComponentType(cls):
        return OpenMaya.MFn.kMeshPolygonComponent

    @classmethod
    def AttrName(cls):
        return "f"

    def __init__(self, nodename_or_dagpath, component):
        super(MeshFace, self).__init__(
            nodename_or_dagpath, component=component
        )

    def getVertices(self):
        it = OpenMaya.MItMeshPolygon(self.dagPath(), self.component())
        return list(it.getVertices())

    def getNormal(self, space="preTransform"):
        # getNormal of api2 is returning inaccurate results?
        sel = om.MSelectionList()
        sel.add(self.dagPath().fullPathName())
        dag = om.MDagPath()
        sel.getDagPath(0, dag)
        comp = om.MFnSingleIndexedComponent()
        comp_obj = comp.create(om.MFn.kMeshPolygonComponent)
        for i in self.indices():
            comp.addElement(i)

        it = om.MItMeshPolygon(dag, comp_obj)
        v = om.MVector()
        it.getNormal(v, util.to_mspace(space, as_api2=False))
        return datatypes.Vector(v.x, v.y, v.z)


class NurbsCurveCV(_SingleIndexGeom):
    @classmethod
    def Match(cls, dagpath, component):
        return component.hasFn(OpenMaya.MFn.kCurveCVComponent)

    @classmethod
    def IterClass(cls):
        return OpenMaya.MItCurveCV

    @classmethod
    def ComponentType(cls):
        return OpenMaya.MFn.kCurveCVComponent

    @classmethod
    def AttrName(cls):
        return "cv"

    def __init__(self, nodename_or_dagpath, component=None):
        super(NurbsCurveCV, self).__init__(
            nodename_or_dagpath, component=component
        )

    def getPosition(self, space="preTransform"):
        it = OpenMaya.MItCurveCV(self.dagPath(), self.component())
        return datatypes.Point(it.position(util.to_mspace(space))).asVector()


class MeshEdge(_SingleIndexGeom):
    @classmethod
    def Match(cls, dagPath, component):
        return component.hasFn(OpenMaya.MFn.kMeshEdgeComponent)

    @classmethod
    def IterClass(cls):
        return OpenMaya.MItMeshEdge

    @classmethod
    def ComponentType(cls):
        return OpenMaya.MFn.kMeshEdgeComponent

    @classmethod
    def AttrName(cls):
        return "e"

    def __init__(self, nodename_or_dagpath, component=None):
        super(MeshEdge, self).__init__(
            nodename_or_dagpath, component=component
        )

    def getPoint(self, index, space="preTransform"):
        it = OpenMaya.MItMeshEdge(self.dagPath(), self.component())
        return datatypes.Point(
            it.point(index, util.to_mspace(space))
        ).asVector()

    def connectedVertices(self):
        it = OpenMaya.MItMeshEdge(self.dagPath(), self.component())
        comp1 = OpenMaya.MFnSingleIndexedComponent()
        comp_obj1 = comp1.create(OpenMaya.MFn.kMeshVertComponent)
        comp1.addElement(it.vertexId(0))

        comp2 = OpenMaya.MFnSingleIndexedComponent()
        comp_obj2 = comp2.create(OpenMaya.MFn.kMeshVertComponent)
        comp2.addElement(it.vertexId(1))

        return MeshVertex(self.dagPath(), comp_obj1), MeshVertex(
            self.dagPath(), comp_obj2
        )

    def longName(self):
        try:
            indices = self.indices()
            indices_str = ",".join(map(str, indices))
            return f"{self.dagPath().fullPathName()}.e[{indices_str}]"
        except Exception as e:
            raise AttributeError(f"Failed to generate longName: {e}")

    def connectedEdges(self):
        it = OpenMaya.MItMeshEdge(self.dagPath(), self.component())
        edges = []
        comp = OpenMaya.MFnSingleIndexedComponent()
        comp_obj = comp.create(OpenMaya.MFn.kMeshEdgeComponent)
        for ei in it.getConnectedEdges():
            comp.addElement(ei)

        return MeshEdge(self.dagPath(), comp_obj)

    def __contains__(self, other):
        if isinstance(other, MeshEdge):
            return (
                False if set(other.indices()) - set(self.indices()) else True
            )
        return False


def BindGeometry(name, silent=False):
    if "." not in name:
        return None

    if not re.search("\[[0-9:]+\]$", name):
        name += "[:]"

    _SELECTION_LIST.clear()
    try:
        _SELECTION_LIST.add(name)
    except RuntimeError:
        if not silent:
            raise
        return None

    dg = _SELECTION_LIST.getDependNode(0)
    if not dg.hasFn(OpenMaya.MFn.kGeometric):
        if not silent:
            raise exception.MayaGeometryError("Invalid geometry given")
        return None

    try:
        dag, comp = _SELECTION_LIST.getComponent(0)
    except:
        if not silent:
            raise
        return None

    if comp.isNull():
        if not silent:
            raise exception.MayaGeometryError("Invalid geometry given")
        return None

    for cls in [MeshVertex, MeshFace, NurbsCurveCV, MeshEdge]:
        if cls.Match(dag, comp):
            try:
                return cls(dag, comp)
            except:
                if not silent:
                    raise

    return None
