from . import base
from . import exception
from . import datatypes
from maya import cmds
from maya import mel as _mel
from maya.api import OpenMaya
import functools
import inspect
import pprint
from . import bind
from .geometry import MeshEdge, MeshVertex, MeshFace, BindGeometry


__all__ = []
__DO_NOT_CAST_FUNCS = set()
__SCOPE_ATTR_FUNCS = {"listAttr"}


SCOPE_ATTR = 0
SCOPE_NODE = 1
Callback = functools.partial
displayError = OpenMaya.MGlobal.displayError
displayInfo = OpenMaya.MGlobal.displayInfo
displayWarning = OpenMaya.MGlobal.displayWarning
# TODO : None to list


# maybe we need same class of cmds
class _Mel(object):
    __Instance = None

    def __new__(self):
        if _Mel.__Instance is None:
            _Mel.__Instance = super(_Mel, self).__new__(self)
            _Mel.__Instance.__cmds = {}
            _Mel.__Instance.eval = _mel.eval

        return _Mel.__Instance

    def __init__(self):
        super(_Mel, self).__init__()

    def __wrap_mel(self, melcmd, *args):
        argstr = ", ".join([x.__repr__() for x in args])
        return super(_Mel, self).__getattribute__("eval")(
            "{}({})".format(melcmd, argstr)
        )

    def __getattribute__(self, name):
        try:
            return super(_Mel, self).__getattribute__(name)
        except AttributeError:
            cache = super(_Mel, self).__getattribute__("_Mel__cmds")
            if name in cache:
                return cache[name]

            if name == "eval":
                return super(_Mel, self).__getattribute__("eval")

            incmd = getattr(cmds, name, None)
            if incmd is not None:
                cache[name] = _pymaya_cmd_wrap(incmd, wrap_object=False)
                return cache[name]

            res = super(_Mel, self).__getattribute__("eval")(
                "whatIs {}".format(name)
            )
            if res.endswith(".mel"):
                cache[name] = functools.partial(
                    super(_Mel, self).__getattribute__("_Mel__wrap_mel"), name
                )
                return cache[name]

            raise


mel = _Mel()


def exportSelected(*args, **kwargs):
    cmds.file(*args, es=True, **kwargs)


def hasAttr(obj, attr, checkShape=True):
    obj = _obj_to_name(obj)

    has = cmds.attributeQuery(attr, n=obj, ex=True)
    if not has and checkShape:
        shapes = cmds.listRelatives(obj, s=True) or []
        for s in shapes:
            has = cmds.attributeQuery(attr, n=s, ex=True)
            if has:
                break

    return has


def selected(**kwargs):
    return _name_to_obj(cmds.ls(sl=True, **kwargs))


class versions:
    def current():
        return cmds.about(api=True)


def importFile(filepath, **kwargs):
    return _name_to_obj(cmds.file(filepath, i=True, **kwargs))


def sceneName():
    return cmds.file(q=True, sn=True)


class MayaGUIs(object):
    def GraphEditor(self):
        cmds.GraphEditor()


runtime = MayaGUIs()


def confirmBox(title, message, yes="Yes", no="No", *moreButtons, **kwargs):
    ret = cmds.confirmDialog(
        t=title,
        m=message,
        b=[yes, no] + list(moreButtons),
        db=yes,
        ma="center",
        cb=no,
        ds=no,
    )
    if moreButtons:
        return ret
    else:
        return ret == yes


__all__.append("Callback")
__all__.append("displayError")
__all__.append("displayInfo")
__all__.append("displayWarning")
__all__.append("exportSelected")
__all__.append("mel")
__all__.append("hasAttr")
__all__.append("selected")
__all__.append("versions")
__all__.append("importFile")
__all__.append("sceneName")
__all__.append("runtime")
__all__.append("confirmBox")


def _obj_to_name(arg):
    """Convert a Maya object to its name representation.

    Recursively converts items in collections. For objects of type base.Geom,
    it returns the result of `toStringList()`. For objects of type base.Base,
    it returns the result of `name()`.

    Args:
        arg (any): The object to convert.

    Returns:
        any: The converted name, or a collection of converted names.
    """
    if isinstance(arg, (list, set, tuple)):
        return arg.__class__([_obj_to_name(x) for x in arg])
    elif isinstance(arg, dict):
        return {k: _obj_to_name(v) for k, v in arg.items()}
    elif isinstance(arg, base.Geom):
        return arg.toStringList()
    elif isinstance(arg, base.Base):
        return arg.name()
    return arg


def _dt_to_value(arg):
    if isinstance(arg, (list, set, tuple)):
        return arg.__class__([_dt_to_value(x) for x in arg])
    elif isinstance(arg, datatypes.Vector):
        return [arg[0], arg[1], arg[2]]
    elif isinstance(arg, datatypes.Point):
        return [arg[0], arg[1], arg[2], arg[3]]
    elif isinstance(arg, datatypes.Matrix):
        return [
            arg[0][0],
            arg[0][1],
            arg[0][2],
            arg[0][3],
            arg[1][0],
            arg[1][1],
            arg[1][2],
            arg[1][3],
            arg[2][0],
            arg[2][1],
            arg[2][2],
            arg[2][3],
            arg[3][0],
            arg[3][1],
            arg[3][2],
            arg[3][3],
        ]
    else:
        return arg


def _name_to_obj(arg, scope=SCOPE_NODE, known_node=None):
    """Convert a node name or collection of names to PyNode objects.

    If the input is a collection (list, set, or tuple), the function applies
    the conversion recursively. For a string input, it attempts to convert the
    string to a PyNode. If the conversion fails, it returns the original string.

    Args:
        arg (any): The value to convert.
        scope (int, optional): The scope identifier (SCOPE_NODE or SCOPE_ATTR).
            Defaults to SCOPE_NODE.
        known_node (str, optional): Known node name used in attribute scope.
            Defaults to None.

    Returns:
        any: A PyNode object, a collection of PyNode objects, or the original value.
    """
    if arg is None:
        return None

    if isinstance(arg, (list, set, tuple)):
        return arg.__class__(
            [_name_to_obj(x, scope=scope, known_node=known_node) for x in arg]
        )

    if isinstance(arg, str):
        node_name = (
            "{}.{}".format(known_node, arg)
            if scope == SCOPE_ATTR and known_node
            else arg
        )
        try:
            return bind.PyNode(node_name)
        except Exception:
            return arg

    return arg


def _pymaya_cmd_wrap(func, wrap_object=True, scope=SCOPE_NODE):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        args = _obj_to_name(args)
        kwargs = _obj_to_name(kwargs)

        try:
            res = func(*args, **kwargs)
        except Exception as e:
            # Format the command for copy-paste debugging
            args_repr = ", ".join(repr(arg) for arg in args)
            kwargs_repr = ", ".join(
                f"{key}={repr(value)}" for key, value in kwargs.items()
            )
            command_repr = (
                f"{func.__module__}.{func.__name__}({args_repr}, {kwargs_repr})"
            )

            # Raise an error with detailed debugging information
            raise RuntimeError(
                f"Error occurred while calling wrapped function '{func.__module__}.{func.__name__}': {str(e)}\n"
                f"Arguments: {args}\n"
                f"Keyword Arguments: {kwargs}\n"
                f"Command for debugging: {command_repr}"
            ) from e
        # filter if the function should not return as list
        # Constraints
        if (
            func.__name__.endswith("Constraint")
            and "query" not in kwargs.keys()
        ):
            res = res[0] if res else None

        # Convert None to empty list for list commands
        # NOTE : is it correct?
        if func.__name__.startswith("list") and res is None:
            res = []

        # # NOTE: we can't use a general unwrapping since the return should be
        # # a list depending of the command, for example pm.deformer
        # # New general unwrapping of single-element lists
        # elif (
        #     not func.__name__.startswith("list")
        #     and isinstance(res, list)
        #     and len(res) == 1
        # ):
        #     # Unwrap the single-item list into just the object

        #     print(
        #         f" {func.__name__}: unwrap single item list: {str(res)}, to {str(res[0])}"
        #     )
        #     res = res[0]

        if wrap_object:
            known_node = None
            if scope == SCOPE_ATTR:
                candi = None

                if args:
                    known_node = args[0]
                else:
                    sel = cmds.ls(sl=True)
                    if sel:
                        known_node = sel[0]

                if known_node is not None:
                    if not isinstance(_name_to_obj(known_node), base.Base):
                        known_node = None

            return _name_to_obj(res, scope=scope, known_node=known_node)
        else:
            return res

    return wrapper


def getAttr(*args, **kwargs):
    args = _obj_to_name(args)
    kwargs = _obj_to_name(kwargs)

    try:
        res = cmds.getAttr(*args, **kwargs)
    except Exception as e:
        raise exception.MayaAttributeError(*e.args)

    if isinstance(res, list) and len(res) > 0:
        at = cmds.getAttr(args[0], type=True)
        if isinstance(res[0], tuple):
            if at == "pointArray":
                return [datatypes.Vector(x) for x in res]
            elif at == "vectorArray":
                return [datatypes.Point(x) for x in res]

            if at.endswith("3"):
                return datatypes.Vector(res[0])

            return res[0]
        else:
            if at == "vectorArray":
                return [
                    datatypes.Vector(res[i], res[i + 1], res[i + 2])
                    for i in range(0, len(res), 3)
                ]
            elif at == "matrix":
                return datatypes.Matrix(res)

            return res

    return res


def setAttr(*args, **kwargs):
    args = _dt_to_value(_obj_to_name(args))
    kwargs = _obj_to_name(kwargs)

    try:
        fargs = []
        for arg in args:
            if isinstance(arg, (list, set, tuple)):
                fargs.extend(arg)
            else:
                fargs.append(arg)

        if (
            len(fargs) == 2
            and isinstance(fargs[1], str)
            and "typ" not in kwargs
            and "type" not in kwargs
        ):
            kwargs["type"] = "string"

        cmds.setAttr(*fargs, **kwargs)
    except Exception as e:
        raise exception.MayaAttributeError(*e.args)


def currentTime(*args, **kwargs):
    if not args and not kwargs:
        kwargs["query"] = True

    return cmds.currentTime(*args, **kwargs)


def listHistory(*args, type=None, exactType=None, **kwargs):
    args = _obj_to_name(args)
    kwargs = _obj_to_name(kwargs)

    res = cmds.listHistory(*args, **kwargs) or []

    if exactType:
        return _name_to_obj([x for x in res if cmds.nodeType(x) == exactType])
    elif type:
        return _name_to_obj(
            [x for x in res if type in cmds.nodeType(x, inherited=True)]
        )
    else:
        return _name_to_obj(res)


def listConnections(*args, sourceFirst=False, **kwargs):
    args = _obj_to_name(args)
    kwargs = _obj_to_name(kwargs)

    if sourceFirst:
        # first  list the source connections
        if "source" not in kwargs or not kwargs["source"]:
            kwargs["source"] = True
        if "destination" not in kwargs or kwargs["destination"]:
            kwargs["destination"] = False

        connections = cmds.listConnections(*args, **kwargs) or []
        res_source = [
            (connections[i + 1], connections[i])
            for i in range(0, len(connections), 2)
        ]

        # add the connections from the destination side
        kwargs["source"] = False
        kwargs["destination"] = True

        connections = cmds.listConnections(*args, **kwargs) or []
        res_destination = [
            (connections[i], connections[i + 1])
            for i in range(0, len(connections), 2)
        ]

        res = res_destination + res_source

    else:
        res = cmds.listConnections(*args, **kwargs) or []
    return _name_to_obj(res)


def _listRelatives(
    dag_path,
    allDescendents=False,
    children=False,
    parent=False,
    fullPath=True,
    path=False,
    shapes=False,
    noIntermediate=False,
    type=None,
):
    """Internal implementation of listRelatives using maya.api.OpenMaya.

    This function implements the logic similar to cmds.listRelatives.

    Args:
        dag_path (str): Name of the DAG node.
        allDescendents (bool): If True, recursively lists all descendants.
        children (bool): If True, lists only immediate children.
        parent (bool): If True, returns the parent of the node.
        fullPath (bool): If True, returns full DAG paths.
        path (bool): Alias for fullPath.
        shapes (bool): If True, filters for shape nodes.
        noIntermediate (bool): If True, excludes intermediate objects.
        type (str): Filter nodes by this type (e.g., "mesh", "nurbsCurve").

    Returns:
        list: List of node names matching the criteria.
    """
    # If "path" flag is True, treat it as fullPath.
    if path:
        fullPath = True

    # Default behavior is children if no traversal flag is set.
    if not (parent or allDescendents or children):
        children = True

    sel_list = OpenMaya.MSelectionList()

    if not isinstance(dag_path, str):
        # dag_path_type = __builtins__["type"](dag_path)
        # print("dag_path_type: {}".format(dag_path_type))
        dag_path = dag_path.longName()
    try:
        sel_list.add(dag_path)
    except RuntimeError:
        OpenMaya.MGlobal.displayWarning(
            "Node '{}' does not exist.".format(dag_path)
        )
        return []

    try:
        dag_path_obj = sel_list.getDagPath(0)
    except Exception:
        OpenMaya.MGlobal.displayWarning(
            "Unable to get DAG path for '{}'.".format(dag_path)
        )
        return []

    # Verify the node is a DAG node.
    dag_node = dag_path_obj.node()
    if not dag_node.hasFn(OpenMaya.MFn.kDagNode):
        OpenMaya.MGlobal.displayWarning(
            "'{}' is not a DAG node.".format(dag_path)
        )
        return []

    dag_fn = OpenMaya.MFnDagNode(dag_path_obj)
    result_nodes = []

    # If parent flag is set, return parent (if any) and exit.
    if parent:
        # Check if the node is a MeshEdge, MeshVertex, or MeshFace.
        bound_geometry = BindGeometry(dag_path, silent=True)
        if isinstance(bound_geometry, (MeshEdge, MeshVertex, MeshFace)):
            return _name_to_obj([bound_geometry.dagPath().fullPathName()])

        if dag_fn.parentCount() > 0:
            parent_obj = dag_fn.parent(0)
            if not parent_obj.isNull():
                parent_fn = OpenMaya.MFnDagNode(parent_obj)
                node_name = (
                    parent_fn.fullPathName() if fullPath else parent_fn.name()
                )
                if node_name:
                    result_nodes.append(node_name)
        return _name_to_obj(result_nodes)

    def process_node(node_obj):
        """Process a node and return its name if it passes filters.

        Args:
            node_obj (MObject): Maya node object.

        Returns:
            str or None: Node name if node passes filters, else None.
        """
        try:
            node_fn = OpenMaya.MFnDagNode(node_obj)
        except Exception:
            return None

        if shapes:
            if not node_fn.object().hasFn(OpenMaya.MFn.kShape):
                return None

        if type is not None:
            if node_fn.typeName != type:
                return None

        if noIntermediate and node_fn.isIntermediateObject:
            return None

        return node_fn.fullPathName() if fullPath else node_fn.name()

    def traverse(node_fn):
        """Recursively traverse children of a node.

        Args:
            node_fn (MFnDagNode): Function set for a DAG node.
        """
        for i in range(node_fn.childCount()):
            child_obj = node_fn.child(i)
            if not child_obj.isNull():
                node_name = process_node(child_obj)
                if node_name is not None:
                    result_nodes.append(node_name)
                traverse(OpenMaya.MFnDagNode(child_obj))

    if allDescendents:
        traverse(dag_fn)
    else:
        # Only immediate children.
        for i in range(dag_fn.childCount()):
            child_obj = dag_fn.child(i)
            if not child_obj.isNull():
                node_name = process_node(child_obj)
                if node_name is not None:
                    result_nodes.append(node_name)

    return _name_to_obj(result_nodes)


def listRelatives(*args, **kwargs):
    """Wrapper for _listRelatives that accepts short and long argument names.

    This function converts short keyword arguments to their corresponding long
    names and then calls the internal _listRelatives implementation.

    Args:
        *args: Positional arguments. The first positional argument must be the
            DAG node name.
        **kwargs: Keyword arguments that may include short or long names.

    Returns:
        list: List of node names matching the criteria.
    """
    # Mapping from short argument names to long names.
    short_to_long = {
        "ad": "allDescendents",
        "c": "children",
        "p": "parent",
        "fp": "fullPath",
        "s": "shapes",
        "ni": "noIntermediate",
        "t": "type",
        "typ": "type",
    }
    # Convert short names in kwargs to long names.
    for key in list(kwargs):
        if key in short_to_long:
            long_key = short_to_long[key]
            if long_key not in kwargs:
                kwargs[long_key] = kwargs.pop(key)
            else:
                kwargs.pop(key)

    # Extract dag_path from positional args or kwargs.
    if args:
        dag_path = args[0]
        new_args = (dag_path,)
    else:
        dag_path = kwargs.pop("dag_path", None)
        new_args = (dag_path,)
    if dag_path is None:
        raise ValueError(
            "dag_path must be provided as a positional or keyword argument."
        )

    # Set default values if not provided.
    defaults = {
        "allDescendents": False,
        "children": False,
        "parent": False,
        "fullPath": True,
        "path": False,
        "shapes": False,
        "noIntermediate": False,
        "type": None,
    }
    for key, value in defaults.items():
        if key not in kwargs:
            kwargs[key] = value

    return _listRelatives(dag_path, **kwargs)


def keyframe(*args, **kwargs):
    args = _obj_to_name(args)
    kwargs = _obj_to_name(kwargs)

    t = kwargs.pop("time", kwargs.pop("k", None))
    if t is not None:
        if isinstance(t, (int, float)):
            kwargs["time"] = (t,)
        else:
            kwargs["time"] = t

    return cmds.keyframe(*args, **kwargs)


def cutKey(*args, **kwargs):
    nargs = _obj_to_name(args)
    nkwargs = {}
    for k, v in kwargs.items():
        nkwargs[k] = _obj_to_name(v)

    t = nkwargs.pop("time", nkwargs.pop("k", None))
    if t is not None:
        if isinstance(t, (int, float)):
            nkwargs["time"] = (t,)
        else:
            nkwargs["time"] = t

    return cmds.cutKey(*nargs, **nkwargs)


def bakeResults(*args, **kwargs):
    args = _obj_to_name(args)
    kwargs = _obj_to_name(kwargs)

    t = kwargs.pop("t", kwargs.pop("time", None))
    if t is not None:
        if isinstance(t, str) and ":" in t:
            t = tuple([float(x) for x in t.split(":")])
        kwargs["time"] = t

    return cmds.bakeResults(*args, **kwargs)


def sets(*args, **kwargs):
    # from pymel general sets
    _set_set_flags = {
        "subtract",
        "sub",
        "union",
        "un",
        "intersection",
        "int",
        "isIntersecting",
        "ii",
        "isMember",
        "im",
        "split",
        "sp",
        "addElement",
        "add",
        "include",
        "in",
        "remove",
        "rm",
        "forceElement",
        "fe",
    }
    _set_flags = {"copy", "cp", "clear", "cl", "flatten", "fl"}

    args = _obj_to_name(args)
    kwargs = _obj_to_name(kwargs)

    for flag, value in kwargs.items():
        if flag in _set_set_flags:
            kwargs[flag] = args[0]

            if isinstance(value, (tuple, list, set)):
                args = tuple(value)
            elif isinstance(value, str):
                args = (value,)
            else:
                args = ()
            break
        elif flag in _set_flags:
            kwargs[flag] = args[0]
            args = ()
            break

    return _name_to_obj(cmds.sets(*args, **kwargs))


def disconnectAttr(*args, **kwargs):
    args = _obj_to_name(args)
    kwargs = _obj_to_name(kwargs)

    if len(args) == 1:
        cons = (
            cmds.listConnections(args[0], s=True, d=False, p=True, c=True)
            or []
        )
        for i in range(0, len(cons), 2):
            cmds.disconnectAttr(cons[i + 1], cons[i], **kwargs)
        cons = (
            cmds.listConnections(args[0], s=False, d=True, p=True, c=True)
            or []
        )
        for i in range(0, len(cons), 2):
            cmds.disconnectAttr(cons[i], cons[i + 1], **kwargs)
    else:
        cmds.disconnectAttr(*args, **kwargs)


def curve(*args, **kwargs):
    """
    Creates a NURBS curve

    """
    curve_obj = cmds.curve(*args, **kwargs)

    # Get the actual transform name (handles Maya's auto-renaming)
    transform_name = cmds.ls(curve_obj, long=False)[0]
    # Find the shapes of the curve
    shapes = (
        cmds.listRelatives(transform_name, shapes=True, fullPath=True) or []
    )

    # Rename shapes based on the transform name
    if len(shapes) == 1:
        # Single shape: rename without index
        cmds.rename(
            shapes[0], "{}Shape".format(transform_name.replace("|", ""))
        )
    else:
        # Multiple shapes: rename with index
        for i, shape in enumerate(shapes, start=1):
            shape_name = "{}Shape{}".format(transform_name, i)
            cmds.rename(shape, shape_name.replace("|", ""))
    the_return = _name_to_obj(transform_name)
    return the_return


def _flatten_list(nested_list):
    """Recursively flattens a nested list structure into a single list."""
    flat_list = []
    for item in nested_list:
        if isinstance(item, (list, tuple)):
            flat_list.extend(_flatten_list(item))
        else:
            flat_list.append(item)
    return flat_list


def select(*args, **kwargs):
    """Wrapper for cmds.select() that supports nested lists."""
    args = _flatten_list(args)
    return _name_to_obj(cmds.select(*args, **kwargs))


# set Locals dict

local_dict = locals()

for n, func in inspect.getmembers(cmds, callable):
    if n not in local_dict:
        local_dict[n] = _pymaya_cmd_wrap(
            func,
            wrap_object=(n not in __DO_NOT_CAST_FUNCS),
            scope=SCOPE_ATTR if n in __SCOPE_ATTR_FUNCS else SCOPE_NODE,
        )
    __all__.append(n)
