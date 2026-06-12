
# imports
from __future__ import absolute_import
import os
import re
import json
from contextlib import contextmanager
from maya import cmds, mel, OpenMayaUI
from maya.app.renderSetup.model import renderSetup, renderLayer, typeIDs
from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCompat
from mgear.animbits.cache_manager.query import (
    _MANAGER_PREFERENCE_PATH,
    get_preference_file,
    get_cache_destination_path,
    get_time_stamp)

try:
    long
except NameError:
    # Python 3 compatibility
    long = int

def __create_preference_file():
    """ Creates the json file to store preferences for the cache manager

    The preference file is created inside the preference folder. It's placement
    is defined by the MAYA_APP_DIR environment variable and it's name by the
    _MANAGER_PREFERENCE_FILE constant

    Returns:
        str: Path to the preference file
    """

    try:
        # creates file
        pref_file = open(get_preference_file(), "w")

        # creates the data structure
        data = {}
        data["cache_manager_cache_path"] = ""
        data["cache_manager_model_group"] = ""
        data["cache_manager_unload_rigs"] = 1
        json.dump(data, pref_file, indent=4)
        pref_file.close()
        return pref_file.name
    except Exception as e:
        message = "Contact mGear's developers reporting this issue to get help"
        print("{} - {} / {}".format(type(e).__name__, e,
                                    message))


def __create_preference_folder():
    """ Creates the preference folder for the cache manager

    The preference folder gets created wherever the MAYA_APP_DIR environment
    variables points at.
    """

    try:
        os.makedirs(_MANAGER_PREFERENCE_PATH)
    except Exception as e:
        message = "Contact mGear's developers reporting this issue to get help"
        print("{} - {} / {}".format(type(e).__name__, e,
                                    message))


def __is_maya_batch():
    """ Returns if the current session is a Maya batch session or not

    Returns:
        bool: if Maya is on batch mode or not
    """

    return cmds.about(batch=True)


def __set_reference_edits(ref_edit_default, value):
    """ Sets the reference edits lock/unlock preference value to the given value

    We only act on the preference if needed. If user already allows reference
    lock/unlock edits then we don't change it's preferences

    Args:
        ref_edit_default (bool): the original state of the preferences
        value (bool): whether or not lock/unlock edits are allowed
    """

    # we allow references edits
    if not ref_edit_default:
        cmds.optionVar(iv=("refLockEditable", value))


def check_gpu_plugin():
    """ Check for the gpuCache plugin load
    """

    if not cmds.pluginInfo('gpuCache', query=True, loaded=True):
        cmds.loadPlugin('gpuCache')


def create_cache_manager_preference_file():
    """ Creates the Animbits cache manager preference file

    Returns:
        str or None: Path to the preference file if existing or created one.
                     None if failed
    """

    pref_file = get_preference_file()

    if not os.path.exists(pref_file):
        __create_preference_folder()
        pref_file = __create_preference_file()

    return pref_file


def delete_cache_file(file_path):
    """ Deletes the given file

    Args:
        file_patj (str): path and name to the file
    """

    try:
        os.remove(file_path)
    except Exception as e:
        message = "Contact mGear's developers reporting this issue to get help"
        print("{} - {} / {}".format(type(e).__name__, e,
                                    message))


def generate_gpu_cache(geo_node, cache_name, start, end, rig_node, lock=False):
    """ Generates a GPU representation for shapes found under the geo_node

    Args:
        geo_node (str): geometry group transform node containing the shapes to
                        cache
        cache_name (str): file name to use for the gpu cache file
        start (float): start frame to use
        end (float): end frame to use
        rig_node (str): Rig root node containing the geo_node
        lock (bool): Whether or not the gpu cache node should be locked
    """

    # checks for plugin load
    check_gpu_plugin()

    # gets cache destination path
    cache_destination = get_cache_destination_path()

    try:
        file_name = re.sub('[^\w_.)( -]', '_', cache_name)
        file_name += "_{}".format(get_time_stamp())
        # Runs the GPU cache generation
        gpu_file = cmds.gpuCache("{}".format(geo_node),
                                 startTime=start,
                                 endTime=end,
                                 optimize=True,
                                 optimizationThreshold=4000,
                                 writeMaterials=True,
                                 directory=cache_destination,
                                 fileName=file_name,
                                 showStats=True,
                                 useBaseTessellation=False,
                                 saveMultipleFiles=True)

        # loads gpu cache
        return load_gpu_cache(cache_name, gpu_file[0], rig_node, lock)

    except Exception as e:
        raise e


def install_script_job(function):
    """ Adds a script job for file read and scene opened
    """

    kill_script_job(function.__name__)
    cmds.scriptJob(event=["NewSceneOpened", function])
    cmds.scriptJob(conditionTrue=["readingFile", function])


def kill_script_job(name):
    """ Finds the given script job name and deletes it

    Args:
        name (str): the name for the script job to kill
    """

    for job in cmds.scriptJob(lj=True):
        if name in job:
            _id = int(job.split(":")[0])
            cmds.scriptJob(k=_id)


def kill_ui(name):
    """ Deletes an already created widget

    Args:
        name (str): the widget object name
    """

    # finds workspace control if dockable widget
    if cmds.workspaceControl(name, exists=True):
        cmds.workspaceControl(name, edit=True, clp=False)
        cmds.deleteUI(name)

    # finds the widget
    widget = OpenMayaUI.MQtUtil.findWindow(name)

    if not widget:
        return

    # wraps the widget into a qt object
    qt_object = QtCompat.wrapInstance(long(widget), QtWidgets.QDialog)

    # sets the widget parent to none
    qt_object.setParent(None)

    # deletes the widget
    qt_object.deleteLater()
    del(qt_object)


def load_gpu_cache(node_name, gpu_file, rig_node, lock):
    """ Generic method to load gpu cache files into a Maya scene

    Args:
        node_name (str): gpu cache node name to be use
        gpu_file (str): file name to use for the gpu cache file
        rig_node (str): Rig root node containing the geo_node
        lock (bool): Whether or not the gpu cache node should be locked

    Returns:
        str: the gpu cache node created
    """

    # checks for plugin load
    check_gpu_plugin()

    # loads gpu cache
    gpu_node = cmds.createNode("gpuCache", name="{}_cacheShape"
                               .format(node_name))
    cmds.setAttr("{}.cacheFileName".format(gpu_node),
                 "{}".format(gpu_file), type="string")

    # adds link attribute to rig
    cmds.addAttr(gpu_node, longName="rig_link", dataType="string")
    cmds.setAttr("{}.rig_link".format(gpu_node), "{}".format(rig_node),
                 type="string", lock=True)

    # adds link to reference node
    cmds.addAttr(gpu_node, longName="rig_reference_node", dataType="string")
    ref_node = cmds.referenceQuery(rig_node, referenceNode=True)
    cmds.setAttr("{}.rig_reference_node".format(gpu_node),
                 "{}".format(ref_node), type="string", lock=True)

    # adds state of the visibility attribute on the rig_node to use later
    cmds.addAttr(gpu_node, longName="visibility_is_locked",
                 attributeType="bool", dv=False)
    cmds.setAttr("{}.visibility_is_locked".format(gpu_node),
                 cmds.getAttr("{}.visibility".format(rig_node), lock=True),
                 lock=True)

    cmds.lockNode(gpu_node, lock=lock)
    cmds.lockNode("{}_cache".format(node_name), lock=lock)

    return gpu_node


def mute_and_hide_node(node):
    """ Mutes the visibility attribute on the given node and hides it

    Args:
        node (str): node to mute and hide
    """

    # we query connections and hide from the mute node
    if cmds.listConnections("{}.visibility".format(node)):
        _mute = cmds.mute("{}.visibility".format(node))
        # we deferre hiding with the mute node due to Maya bullshit
        cmds.evalDeferred("cmds.setAttr('{}.hold', False)".format(_mute[0]))

    # we simply hide
    else:
        cmds.setAttr("{}.visibility".format(node), False)


def unmute_and_show_node(node):
    """ Un-mutes the visibility attribute on the given node and show it

    Args:
        node (str): node to unmute and show
    """

    # we query connections and hide from the mute node
    if cmds.listConnections("{}.visibility".format(node)):
        cmds.mute("{}.visibility".format(node), disable=True, force=True)

    # we simply hide
    else:
        cmds.setAttr("{}.visibility".format(node), 1)


@contextmanager
def set_gpu_color_override(model_group, color):
    """ Creates a Maya render layer to override GPU caches display color
    """

    try:
        cmds.undoInfo(openChunk=True)

        # creates a new instance of the render setup and force clear
        render_setup = renderSetup.instance()
        render_setup.clearAll()

        # force deleting unused shading nodes
        mel.eval('MLdeleteUnused;')

        # creates render layer
        color_layer = render_setup.createRenderLayer("cache_manager_rl")

        # creates collection
        collection = color_layer.createCollection("cache_manager_override")

        # adds model group into the collection of the render layer
        collection.getSelector().setPattern(model_group)

        # creates shader
        mat = cmds.shadingNode("phong", asShader=True,
                               name="cache_manager_display_phong")
        cmds.setAttr("{}.color".format(mat), color[0], color[1], color[2])
        cmds.setAttr("{}.specularColor".format(mat), 0.1, 0.1, 0.1)

        # create override and sets shader
        override = collection.createOverride('shading_override',
                                             typeIDs.shaderOverride)
        override.setShader(mat)

        render_setup.switchToLayer(color_layer)
        yield

    finally:
        # switch back to default render layer
        render_setup.switchToLayer(render_setup.getDefaultRenderLayer())

        # deletes cache manager render layer
        render_setup.detachRenderLayer(color_layer)
        renderLayer.delete(color_layer)

        # force deleting unused shading nodes
        mel.eval('MLdeleteUnused;')
        cmds.undoInfo(closeChunk=True)


def set_preference_file_cache_destination(cache_path):
    """ Sets the Cache Manager cache destination path into the preference file

    Args:
        cache_path (str): The folder path for the cache files
    """

    set_preference_file_setting("cache_manager_cache_path", cache_path)


def set_preference_file_model_group(model_group):
    """ Sets the Cache Manager model group name into the preference file

    Args:
        model_group (str): The model group name
    """

    set_preference_file_setting("cache_manager_model_group", model_group)


def set_preference_file_unload_method(value):
    """ Sets the Cache Manager unload method into the preference file

    Args:
        value (bool): whether or not the rig is unloaded or hidden
    """

    set_preference_file_setting("cache_manager_unload_rigs", value)


def set_preference_file_setting(setting, value):
    """ Generic method to save data into the preference file

    Args:
        setting (str): name of the setting to store
        value (str / bool): value for the setting
    """

    # preference file
    pref_file = get_preference_file()

    try:
        # reads file
        pref_file = open(get_preference_file(), "r")

        # edits path
        data = json.load(pref_file)
        data[setting] = value
        pref_file.close()

        # writes file
        pref_file = open(get_preference_file(), "w")
        json.dump(data, pref_file, indent=4)
        pref_file.close()

    except Exception as e:
        message = "Contact mGear's developers reporting this issue to get help"
        print("{} - {} / {}".format(type(e).__name__, e,
                                    message))
        return None


def load_rig(rig_node):
    """ Brings back the rig

    Args:
        rig_node (str): The rig root node name
    """

    # this is a simple check if the cache actually exists to operate on it
    if not cmds.objExists("{}_cacheShape.cacheFileName".format(rig_node)):
        return

    # gets file path
    file_path = cmds.getAttr("{}_cacheShape.cacheFileName".format(rig_node))

    # gets visibility state recorder
    visibility = cmds.getAttr("{}_cacheShape.visibility_is_locked"
                              .format(rig_node))

    # deletes cache file
    delete_cache_file(file_path)

    # reloads rig
    if cmds.objExists(rig_node):

        # we query reference edits settings
        ref_edits = cmds.optionVar(query="refLockEditable")

        # allow reference edits
        __set_reference_edits(ref_edits, True)

        # show node
        unmute_and_show_node(rig_node)

        # we unlock the attribute
        cmds.setAttr("{}.visibility".format(rig_node), lock=visibility)

        # disable reference edits
        __set_reference_edits(ref_edits, False)

    else:
        ref_node = cmds.getAttr("{}_cacheShape.rig_reference_node"
                                .format(rig_node))
        cmds.file(lr=ref_node)

    # delete gpu node
    cmds.lockNode("{}_cache".format(rig_node), lock=False)
    cmds.lockNode("{}_cacheShape".format(rig_node), lock=False)
    cmds.delete("{}_cache".format(rig_node))


def unload_rig(rig_node, method):
    """ Hides or unloads the given rig

    Hiding method is using the visibility attribute. We would like to
    transport it to the lodVisibility attribute but using this one does not
    trigger correctly the visibility evaluator causing slow-downs due to rig
    still been computed even if hidden.

    Args:
        rig_node (str): The rig root node name
        method (int): 0=hide, 1=unload
    """

    # unload method when we unload reference file
    if method and cmds.referenceQuery(rig_node, rfn=True):
        cmds.file(fr=cmds.referenceQuery(rig_node, rfn=True))
        return

    # check for the hide method
    elif cmds.getAttr("{}.visibility".format(rig_node), lock=True):

        # we query reference edits settings
        ref_edits = cmds.optionVar(query="refLockEditable")

        # allow reference edits
        __set_reference_edits(ref_edits, True)

        # we unlock the attribute
        cmds.setAttr("{}.visibility".format(rig_node), lock=False)

        # hides node
        mute_and_hide_node(rig_node)

        # disable reference edits
        __set_reference_edits(ref_edits, False)

        return

    # hide method when we just hide the rig node
    mute_and_hide_node(rig_node)
