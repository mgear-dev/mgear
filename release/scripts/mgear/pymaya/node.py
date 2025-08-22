import re
from maya.api import OpenMaya
from maya.api import OpenMayaAnim
from maya import cmds
from . import cmd
from . import attr
from . import base
from . import datatypes
from . import exception
from . import geometry
from . import util
from functools import partial
import math


RE_ATTR_INDEX = re.compile("\[([0-9]+)\]")


def _getPivots(node, **kwargs):
    kwargs.pop("pivots", kwargs.pop("piv", None))
    kwargs["pivots"] = True
    kwargs["q"] = True
    res = cmd.xform(node, **kwargs)
    return (datatypes.Vector(res[:3]), datatypes.Vector(res[3:]))


def _setTransformation(node, matrix):
    """Sets the transformation of the node using the provided matrix.

    Args:
        node: The node whose transformation will be set.
        matrix: Can be either an OpenMaya.MMatrix, OpenMaya.MTransformationMatrix,
                or a list of lists representing a 4x4 transformation matrix.
    """

    # If the matrix is a list of lists, convert it to OpenMaya.MMatrix
    if isinstance(matrix, (list, tuple)):
        # Ensure it's a 4x4 matrix (list of 4 lists, each with 4 elements)
        if len(matrix) == 4 and all(len(row) == 4 for row in matrix):
            flat_matrix = [elem for row in matrix for elem in row]
            m_matrix = OpenMaya.MMatrix(flat_matrix)
            matrix = m_matrix
        else:
            raise ValueError("Matrix must be a 4x4 list of lists.")

    # If the matrix is MMatrix, convert it to MTransformationMatrix
    if isinstance(matrix, OpenMaya.MMatrix):
        matrix = OpenMaya.MTransformationMatrix(matrix)

    # Apply the transformation to the node
    OpenMaya.MFnTransform(node.dagPath()).setTransformation(matrix)


def _getTransformation(node):
    return datatypes.TransformationMatrix(
        OpenMaya.MFnTransform(node.dagPath()).transformationMatrix()
    )


def _getShape(node, **kwargs):
    shapes = node.getShapes(**kwargs)
    if shapes:
        return shapes[0]

    return None


def _getShapes(node, **kwargs):
    kwargs.pop("shapes", kwargs.pop("s", None))
    kwargs["shapes"] = True
    return cmd.listRelatives(node, fullPath=True, **kwargs)


def _getParent(node, generations=1):
    if generations == 1:
        res = cmd.listRelatives(node, fullPath=True, p=True, c=False)
        if res:
            return res[0]

        return None
    else:
        splt = [x for x in node.dagPath().fullPathName().split("|") if x]
        spltlen = len(splt)
        if generations >= 0:
            if generations >= spltlen:
                return None

            return BindNode("|" + "|".join(splt[: spltlen - generations]))
        else:
            if abs(generations) > spltlen:
                return None

            return BindNode("|" + "|".join(splt[:-generations]))


def _getChildren(node, **kwargs):
    kwargs["c"] = True
    if "fullPath" not in kwargs:
        kwargs["fullPath"] = True
    return cmd.listRelatives(node, **kwargs)


def _addChild(node, child, **kwargs):
    return cmd.parent(child, node, **kwargs)


def _setMatrix(node, val, **kwargs):
    kwargs.pop("m", kwargs.pop("matrix", None))
    kwargs["m"] = cmd._dt_to_value(val)
    cmd.xform(node, **kwargs)


def _getMatrix(node, **kwargs):
    kwargs.pop("m", kwargs.pop("matrix", None))
    kwargs.pop("q", kwargs.pop("query", None))
    kwargs.update({"q": True, "m": True})

    return datatypes.Matrix(cmd.xform(node, **kwargs))


def _getTranslation(node, space="object"):
    space = util.to_mspace(space)
    return datatypes.Vector(
        OpenMaya.MFnTransform(node.dagPath()).translation(space)
    )


def _setTranslation(node, value, space="object", **kwargs):
    if kwargs.pop("worldSpace", kwargs.pop("ws", False)):
        space = "world"
    elif kwargs.pop("objectSpace", kwargs.pop("os", False)):
        space = "object"

    space = util.to_mspace(space)
    OpenMaya.MFnTransform(node.dagPath()).setTranslation(value, space)


def _getRotation(node, space="object", quaternion=False, **kwargs):
    space = util.to_mspace(space)
    res = OpenMaya.MFnTransform(node.dagPath()).rotation(
        space=space, asQuaternion=True
    )

    if quaternion:
        return datatypes.Quaternion(res)
    else:
        return datatypes.EulerRotation(res.asEulerRotation())


def _setRotation(node, rotation, space="object"):
    if isinstance(rotation, list):
        if len(rotation) == 3:
            rotation = datatypes.EulerRotation(
                *[math.radians(x) for x in rotation]
            )
        elif len(rotation) == 4:
            rotation = datatypes.Quaternion(*rotation)

    if isinstance(rotation, OpenMaya.MEulerRotation):
        rotation = rotation.asQuaternion()

    space = util.to_mspace(space)
    OpenMaya.MFnTransform(node.dagPath()).setRotation(rotation, space)


def _setScale(node, scale):
    OpenMaya.MFnTransform(node.dagPath()).setScale(scale)


def _getScale(node):
    return OpenMaya.MFnTransform(node.dagPath()).scale()


def _getBoundingBox(node, invisible=False, space="object"):
    opts = {"query": True}
    if invisible:
        opts["boundingBoxInvisible"] = True
    else:
        opts["boundingBox"] = True

    if space == "object":
        opts["objectSpace"] = True
    elif space == "world":
        opts["worldSpace"] = True
    else:
        raise Exception("unknown space '{}'".format(space))

    res = cmd.xform(node, **opts)

    return datatypes.BoundingBox(res[:3], res[3:])


class _Node(base.Node):
    __selection_list = OpenMaya.MSelectionList()

    @staticmethod
    def __getObjectFromName(nodename):
        _Node.__selection_list.clear()
        try:
            _Node.__selection_list.add(nodename)
        except RuntimeError as e:
            return None

        return _Node.__selection_list.getDependNode(0)

    def __hash__(self):
        return hash(self.name())

    def __init__(self, nodename_or_mobject):
        super(_Node, self).__init__()
        self.__attrs = {}
        self.__api_mfn = None

        if isinstance(nodename_or_mobject, OpenMaya.MObject):
            self.__obj = nodename_or_mobject
        else:
            self.__obj = _Node.__getObjectFromName(nodename_or_mobject)
            if self.__obj is None:
                raise exception.MayaNodeError(
                    "No such node '{}'".format(nodename_or_mobject)
                )

        if not self.__obj.hasFn(OpenMaya.MFn.kDependencyNode):
            raise exception.MayaNodeError(
                "Not a dependency node '{}'".format(nodename_or_mobject)
            )

        self.__fn_dg = OpenMaya.MFnDependencyNode(self.__obj)
        self.__api_mfn = self.__fn_dg
        self.__is_transform = False

        if self.__obj.hasFn(OpenMaya.MFn.kDagNode):
            dagpath = OpenMaya.MDagPath.getAPathTo(self.__obj)
            self.__dagpath = dagpath
            self.__fn_dag = OpenMaya.MFnDagNode(dagpath)
            self.getParent = partial(_getParent, self)
            self.getChildren = partial(_getChildren, self)
            self.addChild = partial(_addChild, self)
            if self.__obj.hasFn(OpenMaya.MFn.kTransform):
                self.__is_transform = True
                self.getBoundingBox = partial(_getBoundingBox, self)
                self.getPivots = partial(_getPivots, self)
                self.setTransformation = partial(_setTransformation, self)
                self.getTransformation = partial(_getTransformation, self)
                self.getShape = partial(_getShape, self)
                self.getShapes = partial(_getShapes, self)
                self.setMatrix = partial(_setMatrix, self)
                self.getMatrix = partial(_getMatrix, self)
                self.getTranslation = partial(_getTranslation, self)
                self.setTranslation = partial(_setTranslation, self)
                self.setRotation = partial(_setRotation, self)
                self.getRotation = partial(_getRotation, self)
                self.getScale = partial(_getScale, self)
                self.setScale = partial(_setScale, self)

            self.__api_mfn = self.__fn_dag
        else:
            self.__dagpath = None
            self.__fn_dag = None

    def __getattribute__(self, name):
        try:
            return super(_Node, self).__getattribute__(name)
        except AttributeError:
            nfnc = super(_Node, self).__getattribute__("name")
            if cmds.ls("{}.{}".format(nfnc(), name)):
                return super(_Node, self).__getattribute__("attr")(name)
            elif cmds.ls("{}.{}[:]".format(nfnc(), name)):
                return geometry.BindGeometry("{}.{}[:]".format(nfnc(), name))
            elif self.__is_transform:
                sp = self.getShape()
                if sp:
                    sym = getattr(sp, name, None)
                    if sym:
                        return sym

            raise

    def __eq__(self, other):
        if isinstance(other, str):
            other = _Node(other)
        return self.__obj == other.__obj

    def __ne__(self, other):
        if isinstance(other, str):
            other = _Node(other)
        return self.__obj != other.__obj

    def __str__(self):
        """Return the long name of the node as a string."""
        return self.longName()

    def __repr__(self):
        """Return a string representation of the object."""
        return "<_Node '{}'>".format(self.longName())

    def __unicode__(self):
        """Return the long name of the node as a unicode string (for Python 2)."""
        return self.longName()

    def object(self):
        return self.__obj

    def dgFn(self):
        return self.__fn_dg

    def dagFn(self):
        return self.__fn_dag

    def dagPath(self):
        return self.__dagpath

    def isDag(self):
        return self.__fn_dag is not None

    def __apimfn__(self):
        return self.__api_mfn

    def name(self, long=False):
        fdag = super(_Node, self).__getattribute__("_Node__fn_dag")
        if fdag is not None:
            return fdag.partialPathName() if not long else fdag.fullPathName()
        fdg = super(_Node, self).__getattribute__("_Node__fn_dg")
        return fdg.name()

    def nodeName(self):
        return self.name()

    def getName(self):
        return self.name()

    def longName(self):
        fdag = super(_Node, self).__getattribute__("_Node__fn_dag")
        if fdag is not None:
            return fdag.fullPathName()
        fdg = super(_Node, self).__getattribute__("_Node__fn_dg")
        return fdg.name()

    def shortName(self):
        """Return the short name of the node."""
        fdag = super(_Node, self).__getattribute__("_Node__fn_dag")
        if fdag is not None:
            return fdag.partialPathName().split("|")[-1]
        fdg = super(_Node, self).__getattribute__("_Node__fn_dg")
        return fdg.name().split("|")[-1]

    # def namespace(self, **kwargs):
    #     n = self.name()
    #     if ":" not in n:
    #         return ""
    #     return ":".join(n.split("|")[-1].split(":")[:-1]) + ":"

    def stripNamespace(self):
        return "|".join([x.split(":")[-1] for x in self.name().split("|")])

    def child(self, index=0):
        """Retrieve a specific child node by index.

        Args:
            index (int): The index of the child to retrieve. Defaults to 0.

        Returns:
            _Node: The child node at the specified index.

        Raises:
            IndexError: If the index is out of range.
        """
        children = self.listRelatives(c=True, fullPath=True)
        if not children or index < 0 or index >= len(children):
            raise IndexError(f"Child index {index} is out of range.")
        return children[index]

    def attr(self, name, checkShape=True):
        """
        Retrieve an attribute from the node.

        This method attempts to resolve an attribute by its name, including support
        for compound attributes (e.g., "translate.translateX") and array attributes
        (e.g., "someArray[0]"). It also handles alias attributes and can fall back
        to checking the shape node if the attribute is not found on the main node.

        Args:
            name (str): The name of the attribute to retrieve. This can include
                        compound or array syntax.
            checkShape (bool, optional): Whether to check the shape node for the
                                        attribute if it is not found on the main
                                        node. Defaults to True.

        Returns:
            Attribute: An `Attribute` wrapper object representing the resolved
                    attribute.

        Raises:
            exception.MayaAttributeError: If the attribute does not exist or cannot
                                        be resolved.

        Behavior:
            - Checks if the attribute exists in the cache.
            - Resolves compound attributes by splitting the name.
            - Handles array attributes by extracting the index.
            - Attempts to find the attribute plug using the OpenMaya API.
            - Resolves alias attributes if applicable.
            - Falls back to checking the shape node if `checkShape` is True.
            - Uses `cmds.objExists` as a final fallback to confirm the attribute's
            existence.

        Example:
            >>> node = _Node("pSphere1")
            >>> translate_x = node.attr("translateX")
            >>> print(translate_x)
        """
        # Check if the attribute is already cached
        attr_cache = super(_Node, self).__getattribute__("_Node__attrs")
        if name in attr_cache:
            return attr_cache[name]

        # Split the attribute name to handle compound attributes
        parts = name.split(".")
        attrname = parts[0]
        sub_attr = parts[1] if len(parts) > 1 else None
        idx = None

        # Handle array attributes by extracting the index
        idre = RE_ATTR_INDEX.search(attrname)
        if idre:
            attrname = attrname[: idre.start()]
            idx = int(idre.group(1))

        # Attempt to find the attribute plug using the OpenMaya API
        fn_dg = super(_Node, self).__getattribute__("_Node__fn_dg")
        p = None

        try:
            p = fn_dg.findPlug(attrname, False)
        except Exception:
            if checkShape:
                try:
                    # Check the shape node if the attribute is not found
                    get_shape = super(_Node, self).__getattribute__("getShape")
                    shape = get_shape()
                    p = shape.dgFn().findPlug(attrname, False)
                except Exception:
                    pass

        # If the plug is still not resolved, confirm existence with cmds
        if p is None or p.isNull:
            full_attr_name = f"{self.name()}.{name}"
            if cmds.objExists(full_attr_name):
                return attr.Attribute(full_attr_name)
            raise exception.MayaAttributeError(f"No '{name}' attr found")

        # Handle indexed attributes (arrays)
        if idx is not None:
            if p.isArray:
                try:
                    p = p.elementByLogicalIndex(idx)
                except RuntimeError:
                    raise exception.MayaAttributeError(
                        f"Index {idx} not found in attribute '{attrname}'"
                    )
            else:
                raise exception.MayaAttributeError(
                    f"'{attrname}' is not an array attribute"
                )

        # If no sub-attribute, return the resolved plug
        if not sub_attr:
            attr_cache[name] = attr.Attribute(p)
            return attr_cache[name]

        # Ensure the attribute is a compound attribute
        attr_obj = p.attribute()
        if not attr_obj.hasFn(OpenMaya.MFn.kCompoundAttribute):
            raise exception.MayaAttributeError(
                f"'{attrname}' is not a compound attribute"
            )

        # Resolve the sub-attribute within the compound attribute
        fn_attr = OpenMaya.MFnCompoundAttribute(attr_obj)
        found_child_plug = None
        for i in range(fn_attr.numChildren()):
            child_obj = fn_attr.child(i)
            child_fn_attr = OpenMaya.MFnAttribute(child_obj)

            if child_fn_attr.name == sub_attr:
                found_child_plug = p.child(i)
                break

        if found_child_plug is None or found_child_plug.isNull:
            raise exception.MayaAttributeError(
                f"No '{sub_attr}' attr found under '{attrname}'"
            )

        # Cache and return the resolved attribute
        attr_cache[name] = attr.Attribute(found_child_plug)
        return attr_cache[name]

    def addAttr(self, name, **kwargs):
        kwargs.pop("ln", None)
        kwargs.pop("longName", None)
        kwargs["longName"] = name
        return cmd.addAttr(self.name(), **kwargs)

    def getAttr(self, name, **kwargs):
        return cmd.getAttr("{}.{}".format(self.name(), name), **kwargs)

    def setAttr(self, name, *args, **kwargs):
        return cmd.setAttr("{}.{}".format(self.name(), name), *args, **kwargs)

    def hasAttr(self, name, checkShape=True):
        return cmds.objExists("{}.{}".format(self.name(), name))

    def listAttr(self, **kwargs):
        return cmd.listAttr(**kwargs)

    def disconnectAttr(self, attr_name):
        # Construct the full attribute name
        full_attr = "{}.{}".format(self.name(), attr_name)

        # Check if the attribute exists
        if not cmds.objExists(full_attr):
            raise RuntimeError(
                "Attribute '{}' does not exist.".format(full_attr)
            )

        # Get the input connection for the attribute
        input_connection = cmds.listConnections(
            full_attr, source=True, destination=False, plugs=True
        )

        if not input_connection:
            cmd.displayWarning(
                "Attribute '{}' does not have an input connection.".format(
                    full_attr
                )
            )
            return

        # Disconnect the source and destination attributes
        source_attr = input_connection[0]
        cmds.disconnectAttr(source_attr, full_attr)
        # cmd.displayInfo(
        #     "Disconnected '{}' from '{}'.".format(source_attr, full_attr)
        # )

    # NOTE: encapsulation is neded to avoid lossing the types. Previosly it
    # will incorrelty convert the items to a list of strings.
    def __listConnections(self, **kwargs):
        """Encapsulates the cmd.listConnections call."""
        return cmd.listConnections(self, **kwargs)

    def listConnections(self, **kwargs):
        connections = self.__listConnections(**kwargs)

        if kwargs.get("c", False) and isinstance(connections, list):
            return list(zip(connections[::2], connections[1::2]))

        return connections

    def listRelatives(self, **kwargs):
        # ensure we use fullpath to avoid name clashing with maya.cmds
        # this will ensure that return as object and not str if name clashing
        if "fullPath" not in kwargs:
            kwargs["fullPath"] = True
        return cmd.listRelatives(self.name(), **kwargs)

    def type(self):
        return self.__fn_dg.typeName

    # same????
    def nodeType(self):
        return self.__fn_dg.typeName

    def namespace(self):
        nss = self.name().split("|")[-1].split(":")[:-1]
        if not nss:
            return ""

        return ":".join(nss) + ":"

    def node(self):
        return self

    def rename(self, name):
        return BindNode(cmds.rename(self.name(), name))

    def startswith(self, word):
        return self.name().startswith(word)

    def endswith(self, word):
        return self.name().endswith(word)

    def replace(self, old, new):
        return self.name().replace(old, new)

    def split(self, word):
        return self.name().split(word)

    def listHistory(self, **kwargs):
        """Lists the history nodes of the current node, supports all kwargs f
        rom cmds.listHistory.

        Args:
            **kwargs: Keyword arguments to be passed to cmds.listHistory().

        Returns:
            list: A list of instances representing the history nodes.
        """
        # Get the history nodes using cmds.listHistory() with the provided
        # kwargs
        history = cmds.listHistory(self.name(), **kwargs)
        if not history:
            return []

        # Convert the nodes to their registered classes
        node_types = (
            _NodeTypes()
        )  # Access the singleton instance of _NodeTypes
        history_instances = []
        for hist_node in history:
            node_type = cmds.nodeType(hist_node)
            node_class = node_types.getTypeClass(node_type)
            if node_class:
                history_instances.append(node_class(hist_node))
            else:
                history_instances.append(_Node(hist_node))  # Default class

        return history_instances


class _NodeTypes(object):
    __Instance = None

    def __new__(self):
        if _NodeTypes.__Instance is None:
            _NodeTypes.__Instance = super(_NodeTypes, self).__new__(self)
            _NodeTypes.__Instance.__types = {}

        return _NodeTypes.__Instance

    def registerClass(self, typename, cls=None):
        if cls is not None:
            self.__types[typename] = cls
        else:
            clsname = "{}{}".format(typename[0].upper(), typename[1:])

            class _New(_Node):
                def __repr__(self):
                    return "{}('{}')".format(clsname, self.name())

            _New.__name__ = clsname
            self.__types[typename] = _New

    def getTypeClass(self, typename):
        self_types = super(_NodeTypes, self).__getattribute__(
            "_NodeTypes__types"
        )
        if typename in self_types:
            return self_types[typename]

        if typename in cmds.allNodeTypes():
            self.registerClass(typename, cls=None)
            return self_types[typename]

        return None

    def getAllRegisteredTypes(self):
        """Retrieve all registered node types."""
        return self.__types.copy()

    def __getattribute__(self, name):
        try:
            return super(_NodeTypes, self).__getattribute__(name)
        except AttributeError:
            tcls = super(_NodeTypes, self).__getattribute__("getTypeClass")(
                "{}{}".format(name[0].lower(), name[1:])
            )
            if tcls:
                return tcls

            raise

    # def __getattribute__(self, name):
    #     """Override __getattribute__ to fetch registered types safely."""
    #     # Avoid recursion by bypassing custom lookup for special attributes
    #     if name in ("__dict__", "_NodeTypes__types", "getTypeClass"):
    #         return super(_NodeTypes, self).__getattribute__(name)

    #     try:
    #         return super(_NodeTypes, self).__getattribute__(name)
    #     except AttributeError:
    #         # Prevent infinite recursion
    #         if name.startswith("_"):
    #             raise

    #         try:
    #             typename = "{}{}".format(name[0].lower(), name[1:])
    #             tcls = super(_NodeTypes, self).__getattribute__(
    #                 "getTypeClass"
    #             )(typename)
    #             if tcls:
    #                 return tcls
    #         except RecursionError:
    #             raise RuntimeError(
    #                 "Recursion detected while retrieving attribute: {}".format(
    #                     name
    #                 )
    #             )

    #         raise

    def __init__(self):
        super(_NodeTypes, self).__init__()


nt = _NodeTypes()


class SoftMod(_Node):
    def __init__(self, nodename_or_mobject):
        super(SoftMod, self).__init__(nodename_or_mobject)

    def getGeometry(self):
        # pymel returns str list
        return cmds.softMod(self.name(), g=True, q=True)


nt.registerClass("softMod", cls=SoftMod)


class ObjectSet(_Node):
    def __init__(self, nodename_or_mobject):
        super(ObjectSet, self).__init__(nodename_or_mobject)

    def members(self):
        """
        Return the members of the set.

        Returns:
            list: A list of members in the set, or an empty list if no members exist.
        """
        return cmds.sets(self, q=True) or []

    def union(self, *other_sets):
        """
        Perform a union of this set with other sets and return a new ObjectSet.

        Args:
            other_sets (ObjectSet): One or more ObjectSet instances to union with.

        Returns:
            ObjectSet: A new ObjectSet containing the union of the members.
        """

        # Loop through all other sets and gather their members
        other_members = None
        for other_set in other_sets:
            if isinstance(other_set, ObjectSet):
                # Get the members of the other set
                other_members = other_set.members()
            elif isinstance(other_set, list):
                other_members = other_set
                # Add members to the current set
            else:
                raise TypeError(
                    "Expected list or ObjectSet , got {}".format(
                        type(other_set)
                    )
                )
            if other_members:
                cmds.sets(other_members, addElement=self.name())

    def remove(self, *items):
        objects_to_remove = []

        # Loop through the provided items
        for item in items:
            if isinstance(item, list):
                # If it's a list, extend the objects to remove
                objects_to_remove.extend(item)
            else:
                # Otherwise, append the single object
                objects_to_remove.append(item)

        if objects_to_remove:
            # Add objects to the set using cmds.sets
            cmds.sets(objects_to_remove, remove=self.name())

    def add(self, *items):
        """
        Add one or more objects to the set.

        Args:
            *items: Objects to add to the set. Can be a mix of single objects
                    and lists of objects.

        Returns:
            None
        """
        objects_to_add = []

        # Loop through the provided items
        for item in items:
            if isinstance(item, list):
                # If it's a list, extend the objects to add
                objects_to_add.extend(item)
            else:
                # Otherwise, append the single object
                objects_to_add.append(item)

        if objects_to_add:
            # Add objects to the set using cmds.sets
            cmds.sets(objects_to_add, addElement=self.name())


nt.registerClass("objectSet", cls=ObjectSet)


class NurbsCurve(_Node):
    def __init__(self, nodename_or_mobject):
        super(NurbsCurve, self).__init__(nodename_or_mobject)
        self.__fn_curve = OpenMaya.MFnNurbsCurve(self.dagPath())

    def length(self):
        return self.__fn_curve.length()

    def findParamFromLength(self, l):
        return self.__fn_curve.findParamFromLength(l)

    def getPointAtParam(self, p, space="local"):
        mspace = (
            OpenMaya.MSpace.kObject
            if space == "local"
            else OpenMaya.MSpace.kWorld
        )
        return self.__fn_curve.getPointAtParam(p, mspace)

    def form(self):
        frm = self.__fn_curve.form
        if frm == OpenMaya.MFnNurbsCurve.kInvalid:
            return attr.EnumValue(0, "invalid")
        elif frm == OpenMaya.MFnNurbsCurve.kOpen:
            return attr.EnumValue(1, "open")
        elif frm == OpenMaya.MFnNurbsCurve.kClosed:
            return attr.EnumValue(2, "closed")
        elif frm == OpenMaya.MFnNurbsCurve.kPeriodic:
            return attr.EnumValue(3, "periodic")
        else:
            return attr.EnumValue(4, "last")

    def degree(self):
        return self.__fn_curve.degree

    def numSpans(self):
        """Calculate and return the number of spans in the NURBS curve."""
        num_knots = self.__fn_curve.numKnots
        degree = self.__fn_curve.degree
        num_spans = num_knots - degree - 1

        # Adjust for periodic curves
        if self.__fn_curve.form == OpenMaya.MFnNurbsCurve.kPeriodic:
            num_spans -= 1

        return num_spans

    def getKnots(self):
        return [x for x in self.__fn_curve.knots()]

    def getCVs(self, space="preTransform"):
        return [
            datatypes.Point(x).asVector()
            for x in self.__fn_curve.cvPositions(util.to_mspace(space))
        ]

    def setCV(self, index, position, space="world"):
        """Set the position of a single CV.

        Args:
            index (int): The CV index to modify.
            position (datatypes.Point): The new position of the CV.
            space (str): The transformation space (default is "world").

        Raises:
            IndexError: If the CV index is out of range.
        """
        num_cvs = self.__fn_curve.numCVs
        if index < 0 or index >= num_cvs:
            raise IndexError(
                "CV index out of range. Expected 0-{}, got {}.".format(
                    num_cvs - 1, index
                )
            )

        # Ensure position is a datatypes.Point
        if isinstance(position, (list, tuple)):
            if len(position) != 3:
                raise TypeError("Position must be a list/tuple of 3 floats.")
            position = datatypes.Point(*position)
        elif not isinstance(position, datatypes.Point):
            raise TypeError(
                "Position must be a datatypes.Point or [x, y, z] list."
            )

        mspace = util.to_mspace(space)
        self.__fn_curve.setCVPosition(index, position, mspace)
        self.__fn_curve.updateCurve()

    def setCVs(self, cvs, space="preTransform"):
        """Set the positions of all CVs in the curve.

        Args:
            cvs (list): A list of `datatypes.Point` objects representing
                new CV positions.
            space (str): The transformation space (default is "preTransform").

        Raises:
            ValueError: If the number of provided CVs does not match
                the curve's CV count.
        """
        num_cvs = self.__fn_curve.numCVs
        if len(cvs) != num_cvs:
            raise ValueError(
                "Incorrect number of CVs. Expected {}, got {}.".format(
                    num_cvs, len(cvs)
                )
            )

        for i, cv in enumerate(cvs):
            self.setCV(i, cv, space)


nt.registerClass("nurbsCurve", cls=NurbsCurve)


class SkinCluster(_Node):
    def __init__(self, nodename_or_mobject):
        super(SkinCluster, self).__init__(nodename_or_mobject)
        self.__skn = OpenMayaAnim.MFnSkinCluster(self.object())

    def getGeometry(self, **kwargs):
        kwargs["geometry"] = True
        kwargs["query"] = True
        return cmd.skinCluster(self, **kwargs)

    def addInfluence(self, joint, weight=0):
        cmds.skinCluster(self.name(), e=True, ai=joint, lw=True, wt=weight)
        return True

    def __apimfn__(self):
        return self.__skn


nt.registerClass("skinCluster", cls=SkinCluster)


class Mesh(_Node):
    def __init__(self, nodename_or_mobject):
        super(Mesh, self).__init__(nodename_or_mobject)
        self.__fm = OpenMaya.MFnMesh(self.object())

    @property
    def faces(self):
        return geometry.BindGeometry("{}.f[:]".format(self.name()))

    def numFaces(self):
        return self.__fm.numPolygons


nt.registerClass("mesh", cls=Mesh)


class Joint(_Node):
    def __init__(self, nodename_or_mobject):
        super(Joint, self).__init__(nodename_or_mobject)

    def getRadius(self):
        return cmd.joint(self, q=True, radius=True)[0]


nt.registerClass("joint", cls=Joint)


def BindNode(name):
    if not cmds.objExists(name):
        raise exception.MayaNodeError("No such node '{}'".format(name))

    return nt.getTypeClass(cmds.nodeType(name))(name)
