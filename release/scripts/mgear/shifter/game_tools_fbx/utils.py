import os
import sys
import ctypes
import ctypes.wintypes
import traceback
import subprocess
import tempfile

import mgear.pymaya as pm
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

from mgear.vendor.Qt import QtWidgets, QtCore

from mgear.core import (
    pyFBX as pfbx,
    pyqt,
    string,
    utils as coreUtils,
    animLayers,
)
# from mgear.shifter.game_tools_fbx import sdk_utils

NO_EXPORT_TAG = "no_export"
WORLD_CONTROL_NAME = "world_ctl"

FRAMES_PER_SECOND = {
    "24 FPS": ("film", 24),
    "30 FPS": ("ntsc", 30),
    "60 FPS": ("ntscf", 60),
    "120 FPS": ("120fps", 120),
}
AS_FRAMES = dict(FRAMES_PER_SECOND.values())
TRANSFORM_ATTRIBUTES = [
    "tx",
    "ty",
    "tz",
    "rx",
    "ry",
    "rz",
    "sx",
    "sy",
    "sz",
    "visibility",
]


class SelectorDialog(QtWidgets.QDialog):
    def __init__(
        self, items=[], title="Selector Dialog", parent=pyqt.maya_main_window()
    ):
        super(SelectorDialog, self).__init__(parent)
        self.title = title
        self.items = items
        self.item = None

        self.setWindowTitle(self.title)
        self.setWindowFlags(
            self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
        )

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.list_wgt = QtWidgets.QListWidget()
        for item in self.items:
            self.list_wgt.addItem(item.name())

        self.ok_btn = QtWidgets.QPushButton("OK")

    def create_layout(self):
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)
        main_layout.addWidget(self.list_wgt)
        main_layout.addStretch()
        main_layout.addLayout(button_layout)

    def create_connections(self):
        self.list_wgt.itemClicked.connect(self.get_item)
        self.list_wgt.itemDoubleClicked.connect(self.accept)

        self.ok_btn.clicked.connect(self.accept)

    def get_item(self, item):
        self.item = item.text()


def export_animation_clip(config_data, clip_data):
    """
    Exports a singular animation clip.

    config_data: The configuration for the scene/session
    clip_data: Information about the clip to be exported.

    :return: return the path of the newly exported fbx.
    :rtype: str
    """
    # Clip Data
    start_frame = clip_data.get(
        "start_frame", cmds.playbackOptions(query=True, minTime=True)
    )
    end_frame = clip_data.get(
        "end_frame", cmds.playbackOptions(query=True, maxTime=True)
    )
    title = clip_data.get("title", "")
    frame_rate = clip_data.get("geo_root", coreUtils.get_frame_rate())
    anim_layer = clip_data.get("anim_layer", "")

    # Config Data
    root_joint = config_data.get("joint_root", "")
    file_path = config_data.get("file_path", "")
    file_name = config_data.get("file_name", "")
    preset_path = config_data.get("preset_path", None)
    up_axis = config_data.get(
        "up_axis", cmds.optionVar(query="upAxisDirection")
    )
    file_type = config_data.get("file_type", "binary").lower()
    fbx_version = config_data.get("fbx_version", None)

    # Validate timeline range
    if start_frame > end_frame:
        msg = "Start frame {} must be lower than the end frame {}"
        cmds.error(msg.format(start_frame, end_frame))
        return False

    # Validate file path
    if not file_path or not file_name:
        msg = "No valid file path or file name given for the FBX to export!"
        cmds.warning(msg)
        return False

    if title:
        file_name = "{}_{}".format(file_name, title)
    if not file_name.endswith(".fbx"):
        file_name = "{}.fbx".format(file_name)
    path = string.normalize_path(os.path.join(file_path, file_name))
    print("\t>>> Export Path: {}".format(path))

    auto_key_state = cmds.autoKeyframe(query=True, state=True)
    cycle_check = cmds.cycleCheck(query=True, evaluation=True)
    scene_modified = cmds.file(query=True, modified=True)
    current_frame_range = cmds.currentUnit(query=True, time=True)
    current_frame = cmds.currentTime(query=True)
    original_start_frame = cmds.playbackOptions(query=True, minTime=True)
    original_end_frame = cmds.playbackOptions(query=True, maxTime=True)
    temp_mesh = None
    temp_skin_cluster = None
    original_anim_layer_weights = animLayers.get_layer_weights()

    try:
        # default mute status to on
        animlayer_mute = True

        # set anim layer to enable
        if animLayers.animation_layer_exists(anim_layer):
            animLayers.set_layer_weight(anim_layer, toggle_other_off=True)
            
            # Store anim layer mute status
            animlayer_mute = cmds.animLayer(anim_layer, query=True, mute=True)
            cmds.animLayer(anim_layer, edit=True, mute=False)

        # disable viewport
        mel.eval("paneLayout -e -manage false $gMainPane")

        pfbx.FBXResetExport()

        # set configuration
        fbx_version_str = None
        if preset_path is not None:
            # load FBX export preset file
            pfbx.FBXLoadExportPresetFile(f=preset_path)
        if up_axis is not None:
            pfbx.FBXExportUpAxis(up_axis.lower())
        if fbx_version is not None:
            fbx_version_str = "{}00".format(
                fbx_version.split("/")[0].replace(" ", "")
            )
            pfbx.FBXExportFileVersion(v=fbx_version_str)
        if file_type == "ascii":
            pfbx.FBXExportInAscii(v=True)

        # # create temporal triangle to skin
        # temp_mesh = cmds.polyCreateFacet(point=[(-0, 0, 0), (0, 0, 0), (0, 0, 0)], name='mgear_temp_mesh')[0]
        # temp_skin_cluster = cmds.skinCluster(
        #     [root_joint], temp_mesh, toSelectedBones=False, maximumInfluences=1, skinMethod=0)[0]

        # select elements to export
        pm.select([root_joint])

        # Set frame range
        cmds.currentTime(start_frame)
        old_frame_rate = coreUtils.get_frame_rate()
        new_frame_rate = frame_rate
        # only set if frame rate changed
        mult_rate = new_frame_rate / old_frame_rate
        if mult_rate != 1:
            old_range = start_frame, end_frame
            start_frame = old_range[0] * mult_rate
            end_frame = old_range[1] * mult_rate
            coreUtils.set_frame_rate(frame_rate)

        pm.autoKeyframe(state=False)
        pfbx.FBXExportAnimationOnly(v=False)
        pfbx.FBXExportBakeComplexAnimation(v=True)
        pfbx.FBXExportBakeComplexStart(v=start_frame)
        pfbx.FBXExportBakeComplexEnd(v=end_frame)
        pfbx.FBXExportCameras(v=True)
        pfbx.FBXExportConstraints(v=True)
        pfbx.FBXExportLights(v=True)
        pfbx.FBXExportQuaternion(v="quaternion")
        pfbx.FBXExportAxisConversionMethod("none")
        pfbx.FBXExportApplyConstantKeyReducer(v=False)
        pfbx.FBXExportSmoothMesh(v=False)
        pfbx.FBXExportShapes(v=True)
        pfbx.FBXExportSkins(v=True)
        pfbx.FBXExportSkeletonDefinitions(v=True)
        pfbx.FBXExportEmbeddedTextures(v=False)
        pfbx.FBXExportInputConnections(v=True)
        pfbx.FBXExportInstances(v=True)
        pfbx.FBXExportUseSceneName(v=True)
        pfbx.FBXExportSplitAnimationIntoTakes(c=True)
        pfbx.FBXExportGenerateLog(v=False)
        pfbx.FBXExport(f=path, s=True)
    except Exception as exc:
        raise exc
    finally:
        # setup again original anim layer weights
        if anim_layer and original_anim_layer_weights:
            animLayers.set_layer_weights(original_anim_layer_weights)
            # Sets the animation layer back to default
            cmds.animLayer(anim_layer, edit=True, mute=animlayer_mute)

        if temp_skin_cluster and cmds.objExists(temp_skin_cluster):
            cmds.delete(temp_skin_cluster)
        if temp_mesh and cmds.objExists(temp_mesh):
            cmds.delete(temp_mesh)

        cmds.currentTime(current_frame)
        cmds.currentUnit(time=current_frame_range)

        pm.autoKeyframe(state=auto_key_state)
        pm.cycleCheck(evaluation=cycle_check)
        cmds.playbackOptions(min=original_start_frame, max=original_end_frame)

        # if the scene was not modified before doing our changes, we force it back now
        if scene_modified is False:
            cmds.file(modified=False)

        # enable viewport
        mel.eval("paneLayout -e -manage true $gMainPane")

    return path


def create_mgear_playblast(
    file_name="", folder=None, start_frame=None, end_frame=None, scale=75
):
    file_name = file_name or "playblast"
    file_name = os.path.splitext(os.path.basename(file_name))[0]
    file_name = "{}.avi".format(file_name)
    time_range = cmds.playbackOptions(
        query=True, minTime=True
    ), cmds.playbackOptions(query=True, maxTime=True)
    start_frame = start_frame if start_frame is not None else time_range[0]
    end_frame = end_frame if end_frame is not None else time_range[1]
    if end_frame <= start_frame:
        end_frame = start_frame + 1

    if not folder or not os.path.isdir(folder):
        folder = get_mgear_playblasts_folder()
        if not os.path.isdir(folder):
            os.makedirs(folder)
    if not os.path.isdir(folder):
        cmds.warning(
            'Was not possible to create mgear playblasts folder: "{}"'.format(
                folder
            )
        )
        return False
    full_path = os.path.join(folder, file_name)
    count = 1
    while os.path.isfile(full_path):
        _file_name = "{}_{}{}".format(
            os.path.splitext(file_name)[0],
            count,
            os.path.splitext(file_name)[1],
        )
        full_path = os.path.join(folder, _file_name)
        count += 1

    cmds.playbackOptions(
        animationStartTime=start_frame,
        minTime=start_frame,
        animationEndTime=end_frame,
        maxTime=end_frame,
    )
    cmds.currentTime(start_frame, edit=True)
    cmds.playblast(p=scale, filename=full_path, forceOverwrite=True)

    return True


def get_mgear_playblasts_folder():
    CSIDL_PERSONAL = 5  # My Documents
    SHGFP_TYPE_CURRENT = 0  # Get current, not default value
    buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(
        None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf
    )
    documents_folder = os.path.abspath(buf.value)
    playblasts_folder = os.path.join(documents_folder, "mgear_playblasts")

    return playblasts_folder


def open_mgear_playblast_folder():
    folder = get_mgear_playblasts_folder()
    if not folder or not os.path.isdir(folder):
        cmds.warning(
            'Was not possible to open mgear playblasts folder: "{}"'.format(
                folder
            )
        )
        return False

    if sys.platform.startswith("darwin"):
        subprocess.Popen(["open", folder])
    elif os.name == "nt":
        os.startfile(folder)
    elif os.name == "posix":
        subprocess.Popen(["xdg-open", folder])
    else:
        cmds.error("OS not supported: {}".format(os.name))

    return True


def get_geo_grp():
    """Return the geometry group (objectSet in Maya) of the rig.
    If more than one xxx_geo_grp is available will pop up a selection list

    Returns:
            PyNode: objectSet
    """
    geo_grp = None
    geo_groups = pm.ls("*:*_geo_grp", "*_geo_grp", type="objectSet")
    if geo_groups:
        if len(geo_groups) > 1:
            item = select_item(geo_groups, "Select Geo Group")
            if item:
                geo_grp = pm.PyNode(item)
        else:
            geo_grp = geo_groups[0]
    return geo_grp


def get_geo_root():
    geo_grp = get_geo_grp()
    if geo_grp:
        memb = geo_grp.members()
        if memb:
            return memb
        else:
            pm.displayWarning("Geo_grp is empty. Please set geo root manually")
    else:
        pm.displayWarning(
            "Not Geo_grp available, please set geo roots manually"
        )


def get_joint_org():
    jnt_org = None
    joint_orgs = pm.ls("*:jnt_org", "*jnt_org", type="transform")
    if joint_orgs:
        if len(joint_orgs) > 1:
            item = select_item(joint_orgs, "Select Joint Org Node")
            if item:
                jnt_org = pm.PyNode(item)
        else:
            jnt_org = joint_orgs[0]
    return jnt_org


def get_joint_root():
    jnt_org = get_joint_org()
    if jnt_org:
        return jnt_org.getChildren()
    else:
        pm.displayWarning(
            "Not Joint found under jnt_org, please set joint roots manually"
        )


def select_item(items, title):
    """Create modal dialog to select item from list and return the selected tiem

    Args:
            items (list): List of str items
            title (str): Tittle for the modoal dialo

    Returns:
            str: selected item
    """
    item = None
    select_dialog = SelectorDialog(items, title)

    result = select_dialog.exec_()

    if result == QtWidgets.QDialog.Accepted:
        item = select_dialog.item

    return item


def get_end_joint(start_joint):
    end_joint = None
    next_joint = start_joint
    while next_joint:
        child_list = (
            pm.listRelatives(next_joint, fullPath=True, c=True) or list()
        )
        child_joints = pm.ls(child_list, long=True, type="joint") or list()
        if child_joints:
            next_joint = child_joints[0]
        else:
            end_joint = next_joint
            next_joint = None

    return end_joint

# ------- namespaces ------


def _count_namespaces(name):
    # Custom function to count the number of ":" in a name
    return name.count(':')


def clean_namespaces(export_data):
    """
    Gets all available namespaces in scene.
    Checks each for objects that have it assigned.
    Removes the namespace from the object.
    """
    namespaces = get_scene_namespaces()

    # Sort namespaces by longest nested first
    namespaces = sorted(namespaces, key=_count_namespaces, reverse=True)

    for namespace in namespaces:
        print("  - {}".format(namespace))
        child_namespaces = om.MNamespace.getNamespaces(namespace, True)

        for chld_ns in child_namespaces:
            m_objs = om.MNamespace.getNamespaceObjects(chld_ns)
            for m_obj in m_objs:
                remove_namespace(m_obj)

        m_objs = om.MNamespace.getNamespaceObjects(namespace)
        for m_obj in m_objs:
            remove_namespace(m_obj)

    filtered_export_data = clean_export_namespaces(export_data)
    return filtered_export_data


def clean_export_namespaces(export_data):
    """
    Looks at all the joints and mesh data in the export data and removes
    any namespaces that exists.
    """
    
    for key in export_data.keys():

        # ignore filepath, as it contains ':', which will break the path
        if key == "file_path" or key == "color":
            continue

        value = export_data[key]

        print(key, value)

        if isinstance(value, list):
            for i in range(len(value)):
                value[i] = trim_namespace_from_name(value[i])
        elif isinstance(value, dict):
            value = clean_export_namespaces(value)
        elif isinstance(value, str):
            value = trim_namespace_from_name(value)

        export_data[key] = value

    return export_data


def count_namespaces(name):
    # Custom function to count the number of ":" in a name
    return name.count(':')


def trim_namespace_from_name(name):
    if name.find(":") >= 0:
        return name.split(":")[-1]
    return name


def remove_namespace(mobj):
    """
    Removes the namesspace that is currently assigned to the asset
    """
    dg = om.MFnDependencyNode(mobj)
    name = dg.name()
    dg.setName(name[len(dg.namespace):])


def get_scene_namespaces():
    """
    Gets all namespaces in the scene.
    """
    IGNORED_NAMESPACES = [":UI", ":shared", ":root"]
    spaces = om.MNamespace.getNamespaces(recurse=True)
    for ignored in IGNORED_NAMESPACES:
        if ignored in spaces:
            spaces.remove(ignored)

    return spaces


def get_scene_path():
    """
    Get the file path of the current scene.

    Returns:
            str: path of the current open scene file
    """
    return cmds.file(query=True, sceneName=True)


if __name__ == "__main__":
    if sys.version_info[0] == 2:
        reload(pfbx)
    else:
        import importlib

        importlib.reload(pfbx)

    # export_skeletal_mesh(
    #     "Root", "geo_root", r"C:\Users/Miquel/Desktop/testing_auto2.fbx"
    # )

    grp = get_joint_root()
    print(grp)
