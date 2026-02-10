"""Utility functions"""


import os
import sys
import timeit
from functools import wraps
import datetime
import getpass

from maya import cmds
import mgear.pymaya as pm
from maya import mel
import maya.api.OpenMaya as OpenMaya
from .six import string_types, PY2

import mgear


##########################################################
# UTILS
##########################################################


def as_pynode(obj):
    """Check and convert a given string to Pynode

    If the object is not str or unicode or PyNode will raise type error

    Args:
        obj (str, unicode, PyNode): Object to check and/or convert to PyNode

    Returns:
        PyNode: the pynode object
    """
    if isinstance(obj, str) or isinstance(obj, string_types):
        obj = pm.PyNode(obj)

    if not isinstance(obj, (pm.node._Node, pm.node._NodeTypes)):
        raise TypeError(
            "{} is type {} not str, unicode or PyNode".format(
                str(obj), type(obj)
            )
        )

    return obj


def ensure_pynode(func):
    """Decorator to convert string args to PyNodes for Maya dag nodes.

    Args:
        func (callable): Function that accepts Maya node args.

    Returns:
        callable: Wrapped function where string args become PyNodes.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        new_args = []
        for arg in args:
            if isinstance(arg, str):
                new_args.append(pm.PyNode(arg))
            else:
                new_args.append(arg)
        for key, val in kwargs.items():
            if isinstance(val, str):
                kwargs[key] = pm.PyNode(val)
        return func(*new_args, **kwargs)
    return wrapper


def is_odd(num):
    """Check if the number is odd.

    Arguments:
    num (int): the number

    Returns:
        bool: True or False
    """
    return num % 2


def gatherCustomModuleDirectories(
    envvarkey, defaultModulePath, component=False
):
    """returns component directory

    Arguments:
        envvarkey: The environment variable key name, that is searched
        defaultModulePath: The default module path for search in.

    Returns:
        Dict{string: []string}

    """
    results = {}

    # from default path
    if not isinstance(defaultModulePath, list):
        defaultModulePath = [defaultModulePath]
    for dp in defaultModulePath:
        if not os.path.exists(dp):
            message = "= GEAR RIG SYSTEM ====== notify:"
            message += (
                "\n  default module directory is not " "found at {}".format(dp)
            )
            message += "\n\n check your mGear installation"
            message += " or call your system administrator."
            message += "\n"
            mgear.log(message, mgear.sev_error)
            return {}

        results[dp] = sorted(os.listdir(dp))

    # from environment variables
    envvarval = os.environ.get(envvarkey, "")
    for path in envvarval.split(os.pathsep):

        if not path or not os.path.exists(path):
            continue
        if component:
            init_py_path = os.path.join(path, "__init__.py")
            if not os.path.exists(init_py_path):
                message = "= GEAR RIG SYSTEM ====== notify:"
                message += (
                    "\n  __init__.py for custom component not "
                    "found {}".format(init_py_path)
                )
                message += (
                    "\n\n check your module definition file or "
                    "environment variable 'MGEAR_COMPONENTS_PATH'"
                )
                message += " or call your system administrator."
                message += "\n"
                mgear.log(message, mgear.sev_error)
                continue

        modules = sorted(os.listdir(path))
        modules = [x for x in modules if os.path.isdir(os.path.join(path, x))]

        results[path] = modules

    return results


def getModuleBasePath(directories, moduleName):
    """search component path"""

    if PY2:
        dic_items = directories.iteritems
    else:
        dic_items = directories.items
    for basepath, modules in dic_items():
        if moduleName in modules:
            # moduleBasePath = os.path.basename(basepath)
            moduleBasePath = basepath
            break
    else:
        message = (
            "Component '{}' not found in any registered component directory.\n"
            "Please check:\n"
            "  1. The component is installed correctly\n"
            "  2. The MGEAR_COMPONENTS_PATH environment variable includes the component's parent directory\n"
            "  3. The component name is spelled correctly in the guide"
        ).format(moduleName)
        raise ImportError(message)

    return moduleBasePath


def importFromStandardOrCustomDirectories(
    directories, defaultFormatter, customFormatter, moduleName
):
    """Return imported module

    Arguments:
        directories: the directories for search in. this is got by
            gatherCustomModuleDirectories
        defaultFormatter: this represents module structure for default
            module. for example "mgear.core.shifter.component.{}"
        customFormatter:  this represents module structure for custom
            module. for example "{0}.{1}"

    Returns:
        module: imported module

    """
    # Import module and get class
    level = -1 if sys.version_info < (3, 3) else 0
    try:
        module_name = defaultFormatter.format(moduleName)
        module = __import__(module_name, globals(), locals(), ["*"], level)

    except ImportError:
        moduleBasePath = getModuleBasePath(directories, moduleName)
        module_name = customFormatter.format(moduleName)
        if pm.dirmap(cd=moduleBasePath) not in sys.path:
            sys.path.append(pm.dirmap(cd=moduleBasePath))
        module = __import__(module_name, globals(), locals(), ["*"], level)

    return module


# -----------------------------------------------------------------------------
# Decorators
# -----------------------------------------------------------------------------
def viewport_off(func):
    """Decorator - Turn off Maya display while func is running.

    if func will fail, the error will be raised after.

    type: (function) -> function

    """

    @wraps(func)
    def wrap(*args, **kwargs):
        # type: (*str, **str) -> None

        try:
            # Turn $gMainPane Off:
            gMainPane = mel.eval(
                "global string $gMainPane; $temp = $gMainPane;"
            )
            cmds.paneLayout(gMainPane, edit=True, manage=False)

            try:
                return func(*args, **kwargs)

            except Exception as e:
                raise e

            finally:
                cmds.paneLayout(gMainPane, edit=True, manage=True)

        except RuntimeError:
            pm.displayWarning(
                "Turning off viewport has failed."
                " Coninuing with active viewport"
            )
            return func(*args, **kwargs)

    return wrap


def one_undo(func):
    """Decorator - guarantee close chunk.

    type: (function) -> function

    """

    @wraps(func)
    def wrap(*args, **kwargs):
        # type: (*str, **str) -> None

        try:
            cmds.undoInfo(openChunk=True)
            return func(*args, **kwargs)

        except Exception as e:
            raise e

        finally:
            cmds.undoInfo(closeChunk=True)

    return wrap


def undo_off(func):
    """Decorator - Turn off Maya undo while func is running.

    Disables the undo queue before executing the wrapped function and
    re-enables it afterwards. If the function fails, undo is still
    safely restored before the exception is raised.

    type: (function) -> function

    """

    @wraps(func)
    def wrap(*args, **kwargs):
        # type: (*str, **str) -> None

        try:
            cmds.undoInfo(stateWithoutFlush=False)
            pm.displayInfo("Undo off for: {}".format(func.__name__))
            return func(*args, **kwargs)

        except Exception as e:
            raise e

        finally:
            cmds.undoInfo(stateWithoutFlush=True)

    return wrap


def timeFunc(func):
    """Use as a property to time any desired function"""

    @wraps(func)
    def wrap(*args, **kwargs):
        start = timeit.default_timer()
        try:
            return func(*args, **kwargs)

        except Exception as e:
            raise e

        finally:
            end = timeit.default_timer()
            timeConsumed = end - start
            print(
                (
                    "{} time elapsed running {}".format(
                        timeConsumed, func.__name__
                    )
                )
            )

    return wrap


# -----------------------------------------------------------------------------
# selection Decorators
# -----------------------------------------------------------------------------


def _filter_selection(selection, sel_type="nurbsCurve"):
    filtered_sel = []
    for node in selection:
        if node.getShape().type() == sel_type:
            filtered_sel.append(node)
    return filtered_sel


def filter_nurbs_curve_selection(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        args = list(args)
        args[0] = _filter_selection(args[0])
        return func(*args, **kwargs)

    return wrap


def get_frame_rate():
    '''
    Returns the current scene's fps.

    :return: The fps for the current scene's timeline.
    :rtype: int
    '''
    currentUnit = cmds.currentUnit(query=True, time=True)
    if currentUnit == 'film':
        return 24
    if currentUnit == 'show':
        return 48
    if currentUnit == 'pal':
        return 25
    if currentUnit == 'ntsc':
        return 30
    if currentUnit == 'palf':
        return 50
    if currentUnit == 'ntscf':
        return 60
    if 'fps' in currentUnit:
        return int(currentUnit.replace('fps',''))

    return 1 


def set_frame_rate(fps):
    """
    Set Maya Scene's frame rate(fps).

    :param int fps: frames per a second for playback.
    """
    new_fps = ''
    if fps == 24:
        new_fps = 'film'
    elif fps == 48:
        new_fps = 'show'
    elif fps == 25:
        new_fps = 'pal'
    elif fps ==  30:
        new_fps = 'ntsc'
    elif fps ==  50:
        new_fps = 'palf'
    elif fps ==  60:
        new_fps = 'ntscf'
    else:
        new_fps = str(fps)+'fps'
    cmds.currentUnit(time=new_fps)


def get_dag_path(name):
    """
    Gets the dag path for the specified object name.

    :param str name: Name of the object in the Maya Scene.
    
    :return: The dag path to the specified name, else None.
    :rtype: OpenMaya.MDagPath
    """
    selection_list = OpenMaya.MSelectionList()
    try:
        selection_list.add(name)
    except:
        return None

    if selection_list.length() == 0:
        return None
    
    if selection_list.length() > 1:
        raise NameError("Multiple dag paths found from the same name")

    return selection_list.getDagPath(0)


def get_os():
    """
    Gets the OS that Maya is running in.

    :return: Current OS
    :rtype: str
    """
    return cmds.about(os=True)


def get_maya_path():
    """
    Gets the path to the folder where Maya binary lives

    Note: Only works from inside Maya, as Maya adds the path on startup.

    :return: Absolute path to the binary folder that contains maya executable
    :rtype: str
    """
    maya_path = os.environ['MAYA_LOCATION']
    maya_path = os.path.normpath(os.path.join(maya_path,"bin"))
    return maya_path


def get_user_metadata():
    """
    :return: User metadata including username, date, Maya version, and mGear version.
    :rtype: dict[str, str]
    """
    data = {
        "user": getpass.getuser(),
        "date": str(datetime.datetime.now()),
        "maya_version": str(mel.eval("getApplicationVersionAsFloat")),
        "gear_version": mgear.getVersion(),
    }
    return data
