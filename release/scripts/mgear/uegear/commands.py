#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains all commands available for ueGear
"""

from __future__ import print_function, division, absolute_import

import os
import tempfile
import traceback

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as OpenMaya

from mgear.vendor.Qt import QtWidgets

from mgear.core import utils as mUtils
from mgear.core import attribute

from mgear.uegear import log, tag, bridge, io, ioutils
from mgear.uegear import utils as ueUtils
from mgear.uegear import camera as ueCamera

# DEBUGGING
import importlib

importlib.reload(mUtils)
importlib.reload(ueUtils)


logger = log.uegear_logger

def get_unreal_version():
    """Gets the Unreal version for the active session"""
    print("[mGear] Retrieving Unreal Engine Version.")

    uegear_bridge = bridge.UeGearBridge()

    result = uegear_bridge.execute(
        "get_unreal_version"
    ).get("ReturnValue", "")

    return result

def content_project_directory():
    """
    Returns the current Unreal Engine project root directory.

    :return: Unreal Engine project root directory.
    :rtype: str
    """

    uegear_bridge = bridge.UeGearBridge()

    return uegear_bridge.execute("project_content_directory").get(
        "ReturnValue", ""
    )


def import_selected_assets_from_unreal():
    """
    Imports current selected Content Browser Unreal assets into the Maya scene.

    :return: True if import selected assets from Unreal operation was successful; False otherwise.
    :rtype: bool
    """

    uegear_bridge = bridge.UeGearBridge()

    # export FBX file into a temporal folder
    temp_folder = tempfile.gettempdir()
    asset_export_datas = uegear_bridge.execute(
        "export_selected_assets", parameters={"directory": temp_folder}
    ).get("ReturnValue", list())

    if not asset_export_datas:
        logger.warning(
            "Was not possible to export selected assets from Unreal"
        )
        return False

    for asset_export_data in asset_export_datas:
        # import asset from FBX file
        fbx_file = asset_export_data.get("fbx_file", None)
        if not fbx_file or not os.path.isfile(fbx_file):
            logger.warning(
                "No FBX file found for asset data: {}".format(
                    asset_export_data
                )
            )
            continue
        logger.info('Importing Asset from FBX file: "{}"'.format(fbx_file))
        imported_nodes = ueUtils.import_fbx(fbx_file)

        # tag imported transform nodes from FBX
        transform_nodes = cmds.ls(imported_nodes, type="transform")
        for transform_node in transform_nodes:
            asset_type = asset_export_data.get("asset_type", "")
            asset_name = asset_export_data.get("name", "")
            asset_path = asset_export_data.get("path", "")
            if asset_type:
                tag.apply_tag(
                    transform_node, tag.TAG_ASSET_TYPE_ATTR_NAME, asset_type
                )
            else:
                tag.auto_tag(transform_node)
            if asset_name:
                tag.apply_tag(
                    transform_node, tag.TAG_ASSET_NAME_ATTR_NAME, asset_name
                )
            if asset_path:
                tag.apply_tag(
                    transform_node, tag.TAG_ASSET_PATH_ATTR_NAME, asset_path
                )

    return True


def export_selected_assets_to_unreal(
    export_directory=None, export_in_original_path=True
):
    """
    Exports current selected assets in Maya scene into Unreal Engine Content Browser.

    :return: True if export selected assets to Unreal operation was successful; False otherwise.
    :rtype: bool
    """

    # TODO: For now, only static meshes are exported into Unreal
    # TODO: Add support for Skeletal Meshes (Skinned Meshes)

    uegear_bridge = bridge.UeGearBridge()

    temp_folder = tempfile.gettempdir()

    # retrieve a dictionary with the assets that can be exported.
    nodes_to_export = cmds.ls(sl=True, long=True)
    objects_map = io.exportable_assets(nodes=nodes_to_export)
    if not objects_map:
        logger.warning(
            'No exportable assets found in nodes to export: "{}". Make sure assets are tagged.'.format(
                nodes_to_export
            )
        )
        return False

    # retrieve the static meshes nodes to export as assets into Unreal Engine
    static_meshes = objects_map.get(tag.TagTypes.StaticMesh, list())
    if not static_meshes:
        logger.warning("No static meshes to update")
        return False

    # Retrieve current Unreal Engine project directory
    content_path = uegear_bridge.execute("project_content_directory").get(
        "ReturnValue", ""
    )
    if not content_path or not os.path.isdir(content_path):
        logger.warning(
            "Was not possible to retrieve current Unreal project content path"
        )
        return False

    import_path_for_new_assets = ""

    for static_mesh in static_meshes:
        asset_path = tag.tag_values(
            tag_name=tag.TAG_ASSET_PATH_ATTR_NAME, nodes=[static_mesh]
        )
        asset_path = asset_path[0] if asset_path else ""
        asset_exists = uegear_bridge.execute(
            "does_asset_exist", parameters={"asset_path": asset_path}
        ).get("ReturnValue", False)

        if not asset_exists:
            asset_file_name = static_mesh.split("|")[-1]
            logger.info(
                'Asset "{}" does not exists within current Unreal Project! New asset will be created...'.format(
                    asset_file_name
                )
            )

            export_file_name = "{}.fbx".format(asset_file_name)

            if not export_directory:
                asset_export_path = ueUtils.join_path(
                    temp_folder, export_file_name
                )
            else:
                asset_export_path = ueUtils.join_path(
                    export_directory, export_file_name
                )

            if export_directory:
                asset_export_directory = os.path.dirname(asset_export_path)
                if not os.path.isdir(asset_export_directory):
                    logger.info(
                        "Export directory does not exist, trying to create it: {}".format(
                            asset_export_directory
                        )
                    )
                    result = ueUtils.create_folder(asset_export_directory)
                    if not result:
                        logger.warning(
                            'Was not possible to create original export path: "{}" | temp folder will be used instead...'.format(
                                asset_export_directory
                            )
                        )
                        asset_export_path = ueUtils.join_path(
                            temp_folder, "{}.fbx".format(asset_file_name)
                        )
            asset_export_directory = os.path.dirname(asset_export_path)

            # export FBX file into disk
            fbx_file_path = ioutils.export_static_mesh(
                asset_export_directory, static_mesh, file_name=export_file_name
            )
            if not os.path.isfile(fbx_file_path):
                logger.warning(
                    'Something went wrong while exporting asset FBX file: "{}"'.format(
                        fbx_file_path
                    )
                )
                continue

            if not import_path_for_new_assets or not os.path.isdir(
                import_path_for_new_assets
            ):
                import_path_for_new_assets = QtWidgets.QFileDialog.getExistingDirectory(
                    None,
                    "Select Folder where Unreal Asset (.uasset) will be located",
                    content_path,
                )
            if not import_path_for_new_assets or not os.path.isdir(
                import_path_for_new_assets
            ):
                logger.warning(
                    'Path where Unreal Asset (.uasset) will be located does not exist: "{}"'.format(
                        import_path_for_new_assets
                    )
                )
                continue

            try:
                relative_path = os.path.relpath(
                    import_path_for_new_assets, content_path
                )
            except ValueError:
                logger.warning(
                    "Selected Path is not in the proper project drive. Skipping import..."
                )
                continue
            if ".." in relative_path:
                logger.warning(
                    "Selected Path does not belong to current Unreal project directory. Skipping import..."
                )
                continue
            relative_path = (
                content_path if relative_path == "." else relative_path
            )
            asset_path = ueUtils.join_path(
                "Game",
                relative_path,
                "{}.{}".format(asset_file_name, asset_file_name),
            )

            # TODO: Import options should be configurable by the user (through UI? or passing JSON import option files?)
            import_options = {
                "destination_name": asset_file_name,
                "import_materials": False,
                "import_textures": False,
                "save": False,
            }
            result = uegear_bridge.execute(
                "import_static_mesh",
                parameters={
                    "fbx_file": fbx_file_path,
                    "import_path": import_path_for_new_assets,
                    "import_options": str(import_options),
                },
            ).get("ReturnValue", False)
            if not result:
                logger.warning(
                    "Was not possible to export asset: {}. Please check Unreal Engine Output Log".format(
                        static_mesh
                    )
                )
                continue

            tag.apply_tag(
                static_mesh, tag.TAG_ASSET_NAME_ATTR_NAME, asset_file_name
            )
            tag.apply_tag(
                static_mesh, tag.TAG_ASSET_PATH_ATTR_NAME, asset_path
            )

        else:
            # Verify .uasset file for the asset exists within current Unreal Engine project directory
            asset_file_name = os.path.basename(asset_path).split(".")[0]
            uasset_file_name = asset_file_name + ".uasset"
            content_uasset_path = ueUtils.join_path(
                content_path,
                os.path.dirname(asset_path).replace("/Game/", "/"),
                uasset_file_name,
            )
            if not os.path.isfile(content_uasset_path):
                logger.warning(
                    '.uasset file was not found: "{}"'.format(
                        content_uasset_path
                    )
                )
                continue

            export_file_name = "{}.fbx".format(asset_file_name)

            if not export_directory and export_in_original_path:
                # We try to retrieve the export path from the metadata of the Asset within Unreal Engine project
                asset_export_path = uegear_bridge.execute(
                    "asset_export_path", parameters={"asset_path": asset_path}
                ).get("ReturnValue", "")
                export_file_name = "{}.fbx".format(
                    os.path.basename(asset_export_path).split(".")[0]
                )
            else:
                if not export_directory:
                    asset_export_path = ueUtils.join_path(
                        temp_folder, export_file_name
                    )
                else:
                    asset_export_path = ueUtils.join_path(
                        export_directory, export_file_name
                    )

            # if it is not possible to find/create the original FBX export path we export the asset into a temp folder
            if export_directory or export_in_original_path:
                asset_export_directory = os.path.dirname(asset_export_path)
                if not os.path.isdir(asset_export_directory):
                    logger.info(
                        "Export directory does not exist, trying to create it: {}".format(
                            asset_export_directory
                        )
                    )
                    result = ueUtils.create_folder(asset_export_directory)
                    if not result:
                        logger.warning(
                            'Was not possible to create original export path: "{}" | temp folder will be used instead...'.format(
                                asset_export_directory
                            )
                        )
                        asset_export_path = ueUtils.join_path(
                            temp_folder, "{}.fbx".format(asset_file_name)
                        )
            asset_export_directory = os.path.dirname(asset_export_path)

            # export FBX file into disk
            fbx_file_path = ioutils.export_static_mesh(
                asset_export_directory, static_mesh, file_name=export_file_name
            )
            if not os.path.isfile(fbx_file_path):
                logger.warning(
                    'Something went wrong while exporting asset FBX file: "{}"'.format(
                        fbx_file_path
                    )
                )
                continue

            # TODO: Import options should be retrieved from the .uasset file located in Unreal
            import_options = {
                "destination_name": asset_file_name,
                "replace_existing": True,
                "save": False,
            }
            result = uegear_bridge.execute(
                "import_static_mesh",
                parameters={
                    "fbx_file": fbx_file_path,
                    "import_path": os.path.dirname(content_uasset_path),
                    "import_options": str(import_options),
                },
            ).get("ReturnValue", False)
            if not result:
                logger.warning(
                    "Was not possible to export asset: {}. Please check Unreal Engine Output Log".format(
                        static_mesh
                    )
                )
                continue

    return True


def export_cameras(cameras=None):
    # TODO: WIP
    """
    This method is still under heavy development, as the surrounding API does not
    yet have all the needed functionality implemented.

    If this does not get implemented, please remove it.
    """
    # FIXME: export_layout_json, does not support camera objects

    cameras = ueUtils.force_list(cameras or ueUtils.get_selected_cameras())
    if not cameras:
        logger.warning("No cameras to export")
        return False

    temp_folder = tempfile.gettempdir()
    cameras_file = io.export_layout_json(
        nodes=cameras, output_path=temp_folder
    )

    print("Camera Export Debug: {}".format(cameras_file))

    return False  # Early exit for debugging reasons

    result = self.execute(
        "import_maya_data_from_file", parameters={"data_file": cameras_file}
    )
    ueUtils.safe_delete_file(cameras_file)

    return True


def export_layout_to_unreal(self, nodes=None):
    """
    Export nodes into a ueGear layout file and imports that layout into current opened Unreal level.

    :param str or list(str) or None nodes: list of nodes to include into the layout file. If not given, all current
            selected nodes will be added.
    :return: True if the export layout to Unreal operation was successful; False otherwise.
    :rtype: bool
    """

    nodes = ueUtils.force_list(nodes or cmds.ls(sl=True, long=True))
    if not nodes:
        logger.warning("No layout nodes selected to export")
        return False

    temp_folder = tempfile.gettempdir()
    layout_file = io.export_layout_json(nodes=nodes, output_path=temp_folder)
    result = self.execute(
        "import_maya_layout_from_file", parameters={"layout_file": layout_file}
    )
    ueUtils.safe_delete_file(layout_file)

    return True


def import_layout_from_unreal(export_assets=True):
    """
    Imports the selected objects from the Unreal Level into Maya.
    """
    uegear_bridge = bridge.UeGearBridge()

    temp_folder = tempfile.gettempdir()
    temp_assets_folder = ueUtils.clean_path(
        os.path.join(temp_folder, "uegear_temp_assets")
    )
    if os.path.isdir(temp_assets_folder):
        ueUtils.safe_delete_folder(temp_assets_folder)
    ueUtils.ensure_folder_exists(temp_assets_folder)

    result = uegear_bridge.execute(
        "export_maya_layout",
        parameters={
            "directory": temp_assets_folder,
            "export_assets": export_assets,
        },
    ).get("ReturnValue", "")

    if not (result and os.path.isfile(result)):
        return False

    layout_data = ueUtils.read_json_file(result)
    if not layout_data:
        return False

    for actor_data in layout_data:
        fbx_file = actor_data.get("assetExportPath", None)
        if not fbx_file or not os.path.isfile(fbx_file):
            continue

        # Check if object already exists in scene...

        # Cannot assume the name of the object is what it is named in maya.
        # To veryify the object we need to find all objects with the same GUID
        dag_path = mUtils.get_dag_path(actor_data["name"])

        # Check if object has the same guid and actor name
        asset_guid = actor_data.get("guid", "")
        actor_name = actor_data["name"]

        # Find all tagged objects that have the specific guid
        matching_guid_objs = tag.find_tagged_nodes(
            tag_name=tag.TAG_ASSET_GUID_ATTR_NAME, tag_value=asset_guid
        )

        # If GUID, Actor Name and Asset Path are all equal, then object is stale.
        for obj in matching_guid_objs:
            dag_path = mUtils.get_dag_path(obj)
            guid_match = tag.tag_match(
                dag_path, asset_guid, tag.TAG_ASSET_GUID_ATTR_NAME
            )
            name_match = tag.tag_match(
                dag_path, actor_name, tag.TAG_ACTOR_NAME_ATTR_NAME
            )

            #   Object passed all checks, it is stale and needs to be deleted.
            if guid_match and name_match:
                dag_mod = OpenMaya.MDagModifier()
                dag_mod.deleteNode(OpenMaya.MFnDagNode(dag_path).object())
                dag_mod.doIt()

        imported_nodes = ueUtils.import_static_fbx(fbx_file)

        transform_nodes = cmds.ls(imported_nodes, type="transform")
        transform_node = ueUtils.get_first_in_list(transform_nodes)
        if not transform_node:
            continue

        for transform_node in transform_nodes:
            asset_guid = actor_data.get("guid", "")
            asset_type = actor_data.get("assetType", "")
            asset_name = actor_data.get("assetName", "")
            asset_path = actor_data.get("assetPath", "")
            actor_name = actor_data["name"]
            translation = actor_data["translation"]
            rotation = actor_data["rotation"]
            scale = actor_data["scale"]

            # Apply unreal meta data as tags
            tag.apply_tag(
                transform_node, tag.TAG_ASSET_GUID_ATTR_NAME, asset_guid
            )
            if asset_type:
                tag.apply_tag(
                    transform_node, tag.TAG_ASSET_TYPE_ATTR_NAME, asset_type
                )
            else:
                tag.auto_tag(transform_node)
            tag.apply_tag(
                transform_node, tag.TAG_ASSET_NAME_ATTR_NAME, asset_name
            )
            tag.apply_tag(
                transform_node, tag.TAG_ASSET_PATH_ATTR_NAME, asset_path
            )
            tag.apply_tag(
                transform_node, tag.TAG_ACTOR_NAME_ATTR_NAME, actor_name
            )
            transform_node = cmds.rename(transform_node, actor_name)

            # Converts the unreal matrix into maya matrix
            obj_trans_matrix = OpenMaya.MTransformationMatrix()
            obj_trans_matrix.setTranslation(
                OpenMaya.MVector(translation), OpenMaya.MSpace.kWorld
            )
            obj_trans_matrix.setRotation(OpenMaya.MEulerRotation(rotation))
            obj_trans_matrix.setScale(
                OpenMaya.MVector(scale), OpenMaya.MSpace.kWorld
            )

            maya_trans_matrix = (
                ueUtils.convert_transformationmatrix_Unreal_to_Maya(
                    obj_trans_matrix
                )
            )

            dag_path = mUtils.get_dag_path(transform_node)
            if dag_path:
                transform_fn = OpenMaya.MFnTransform(dag_path)
                transform_fn.setTransformation(
                    OpenMaya.MTransformationMatrix(maya_trans_matrix)
                )

    # Clean up temporary location
    ueUtils.safe_delete_folder(temp_assets_folder)

    return True


def update_selected_transforms():
    """
    Updates matching Unreal objects within current level with the transforms of the currently selected
    objects within Maya scene.
    """

    uegear_bridge = bridge.UeGearBridge()

    selected_nodes = cmds.ls( selection=True )
    world_up = cmds.optionVar(query="upAxisDirection")

    old_rotation_orders = list()
    for node_name in selected_nodes:
        rot_order_index = cmds.getAttr(f"{node_name}.rotateOrder")
        old_rotation_orders.append(rot_order_index)
        cmds.setAttr(f"{node_name}.rotateOrder", 0) # XYZ

    try:
        objects = cmds.ls(sl=True, sn=True)
        for obj in objects:
            ue_world_transform = (
                ueUtils.get_unreal_engine_transform_for_maya_node(obj)
            )

            actor_guids = tag.tag_values(tag.TAG_ASSET_GUID_ATTR_NAME, [obj])
            if actor_guids == None:
                print("WARNING: Could not find guid: {}".format(obj))
                continue
            actor_guid = actor_guids[0]

            result = uegear_bridge.execute(
                "set_actor_world_transform",
                parameters={
                    "actor_guid": actor_guid,
                    "translation": str(ue_world_transform["rotatePivot"]),
                    "rotation": str(ue_world_transform["rotation"]),
                    "scale": str(ue_world_transform["scale"]),
                    "world_up": str(world_up),
                },
            )
    finally:
        for i, selected_node in enumerate(selected_nodes):
            cmds.setAttr(f"{node_name}.rotateOrder", old_rotation_orders[i])


# NOT IMPLEMENTED
def import_sequencer_cameras_timeline_from_unreal():
    """
    Imports the current active sequencer data from Unreal into Maya.
    Imports:
        - All Camera Tracks from Sequencer
    Updates:
        - Mayas Timerange, to match that of the sequencer.
        - Maya FPS, to match that of the dequencer.
    """
    print("Import Sequencer's Cameras and Timeline data - In Development")

    # [ ] Get active Sequencer in Unreal, else return
    # [ ] Get Cameras in Sequencer, else return
    # [ ] Get Sequencer Data, else return

    # Unreal Cameras exported to location
    # export FBX file into a temporal folder
    temp_folder = tempfile.gettempdir()
    raise NotImplementedError


def import_selected_cameras_from_unreal():
    """
    Triggers the Unreal bridge call, to export the selected Camera
    tracks in the active sequencer, and import it into Maya.
    """
    print("[mGear] Importing Selected Sequencer Cameras from Unreal...")

    uegear_bridge = bridge.UeGearBridge()

    # export FBX file into a temporal folder
    temp_folder = tempfile.gettempdir()

    # Send Unreal Command

    # UE - Get fps, to validate maya and unreal match
    sequencer_fps = uegear_bridge.execute(
        "get_selected_sequencer_fps", parameters={}
    ).get("ReturnValue", list())
    if not sequencer_fps:
        logger.warning(
            "Was not possible to retrieve Sequencer FPS from Unreal"
        )
        return False

    # UE - Export selected Camera
    asset_export_datas = uegear_bridge.execute(
        "export_selected_sequencer_cameras",
        parameters={"directory": temp_folder},
    ).get("ReturnValue", list())
    if not asset_export_datas:
        logger.warning(
            "Was not possible to export selected camera from Unreal"
        )
        return False

    # Check FPS in Maya and Sequencer match, else suggest update.
    print("[mGear] Unreal Sequencer FPS {}".format(sequencer_fps))
    current_frame_rate = mUtils.get_frame_rate()

    if sequencer_fps != current_frame_rate:
        # Create a pop-up dialog and to alert user
        result = cmds.confirmDialog(
            title="Frame Rates Do Not Match",
            message="The Sequencer FPS, do not match those of the current Maya scene. \n\nDo you wish to update Maya's fps?",
            button=["Yes", "No"],
            defaultButton="Yes",
            cancelButton="No",
            dismissString="No",
        )

        if result == "No":
            return
        else:
            mUtils.set_frame_rate(sequencer_fps)

    # Loop over Unreal result

    for asset_export_data in asset_export_datas:
        # import asset from FBX file
        fbx_file = asset_export_data.get("fbx_file", None)
        if not fbx_file or not os.path.isfile(fbx_file):
            logger.warning(
                "No FBX file found for asset data: {}".format(
                    asset_export_data
                )
            )
            continue
        logger.info('Importing Asset from FBX file: "{}"'.format(fbx_file))
        imported_nodes = ueUtils.import_fbx(fbx_file)

        # TODO: Check if Camera with the same name and metadata exists in the Level
        #   [ ] Update it
        #  - I would recommend not deleting it incase it has been added to layers or grouping.
        #   Deleting would be the most destructive outcome.

        # tag imported transform nodes from FBX
        transform_nodes = cmds.ls(imported_nodes, type="transform")
        for transform_node in transform_nodes:
            asset_type = asset_export_data.get("asset_type", "")
            asset_name = asset_export_data.get("name", "")
            asset_path = asset_export_data.get("path", "")
            if asset_type:
                tag.apply_tag(
                    transform_node, tag.TAG_ASSET_TYPE_ATTR_NAME, asset_type
                )
            else:
                tag.auto_tag(transform_node)
            if asset_name:
                tag.apply_tag(
                    transform_node, tag.TAG_ASSET_NAME_ATTR_NAME, asset_name
                )
            if asset_path:
                tag.apply_tag(
                    transform_node, tag.TAG_ASSET_PATH_ATTR_NAME, asset_path
                )

        # Check if camera contains filmback attribute, if it does then we convert the curve data and apply it to the
        # `Sensor Height` `Sensor Width`
        # transform node is always a camera, as we are only importing a camera.
        for camera_name in transform_nodes:
            ueCamera.unreal_to_maya_sensor_conversion(camera_name)

    return True


def update_sequencer_camera_from_maya():
    print("[mGear] Updating Sequencer, using selected Maya Camera")

    uegear_bridge = bridge.UeGearBridge()

    # Retrieve a dictionary with the assets that can be exported.
    nodes_to_export = cmds.ls(sl=True, long=True)
    objects_map = io.exportable_assets(nodes=nodes_to_export)
    if not objects_map:
        msg = 'No exportable assets found in nodes to export: "{}".'
        msg += "Make sure assets are tagged."
        logger.warning(msg.format(nodes_to_export))
        return False

    # Retrieve the Camera nodes to update active sequencer
    cameras = objects_map.get(tag.TagTypes.Camera, list())
    if not cameras:
        logger.warning("No cameras to update")
        return False

    # Create a list of AssetPaths, Camera Name, export_path
    ue_camera_names = tag.tag_values(tag.TAG_ASSET_NAME_ATTR_NAME, cameras)
    camera_sequence_paths = tag.tag_values(
        tag.TAG_ASSET_PATH_ATTR_NAME, cameras
    )
    camera_export_path = dict()

    # Export Camera to temp location
    temp_folder = tempfile.gettempdir()

    # Export FBX file into disk
    for i in range(len(cameras)):
        camera_name = ue_camera_names[i]

        if " " in camera_name:
            modified_camera_name = camera_name.replace(" ", "_")
        else:
            modified_camera_name = camera_name
        fbx_file_path = os.path.join(temp_folder, modified_camera_name + ".fbx")

        maya_cam_name = nodes_to_export[i]

        try:
            mel.eval("FBXExportCameras - v 1")
            cmds.select(maya_cam_name, replace=True)
            cmds.file(fbx_file_path, force=True, typ="FBX export", pr=True, es=True, mbl=True)

            msg = "Camera '{}' exported as FBX to '{}'"
            print(msg.format(camera_name, fbx_file_path))
        except Exception as e:
            print("Error exporting camera: {}".format(str(e)))
            continue

        if not os.path.isfile(fbx_file_path):
            msg = 'Something went wrong while exporting asset FBX file: "{}"'
            logger.warning(msg.format(fbx_file_path))
            continue

        camera_export_path[camera_name] = fbx_file_path

        uegear_bridge.execute(
            "update_sequencer_camera_from_maya",
            parameters={
                "camera_name": camera_name,
                "sequencer_package": camera_sequence_paths[i],
                "fbx_path": fbx_file_path,
            },
        ).get("ReturnValue", False)

    # Clean up temporary data
    for path in camera_export_path.values():
        try:
            os.remove(path)
        except PermissionError as p_e:
            print(p_e)
        except IOError as io_e:
            print(io_e)


def get_skeletal_data(skeletal_mesh=False):
    """
    Queries Unreal for all the Skeletons or Skeletal Meshes that exist in the project.

    :param bool skeletal_mesh: If True return SkeletalMesh data, False return Skeleton data.
    :return: The package_name and asset_name. Stored in an Array of Key,Value pairs.
    :rtype: [{}]
    """
    print("[mGear] Retrieving Skeletal Data.")

    uegear_bridge = bridge.UeGearBridge()

    result = uegear_bridge.execute(
        "get_skeletons_data", parameters={"skeletal_mesh": skeletal_mesh}
    ).get("ReturnValue", [])

    return result


def get_selected_content_browser_folder(relative=False):
    """
    Returns the selected folder object in Unreals Content Browser.

    :return: Path to the selected folders in the content browser.
    :rtype: [str]
    """
    print("[mGear] Retrieving Selected Content Browser Folder.")

    uegear_bridge = bridge.UeGearBridge()

    result = uegear_bridge.execute(
        "selected_content_browser_directory", parameters={"relative": relative}
    ).get("ReturnValue", [])

    return result


def export_animation_to_unreal(
    animation_path, unreal_folder_path, animation_name, skeleton_path
):
    print("[mGear] Importing Animation paths into Unreal.")

    uegear_bridge = bridge.UeGearBridge()

    result = uegear_bridge.execute(
        "import_animation",
        parameters={
            "animation_path": animation_path,
            "dest_path": unreal_folder_path,
            "name": animation_name,
            "skeleton_path": skeleton_path,
        },
    ).get("ReturnValue", [])

    return result


def export_skeletal_mesh_to_unreal(
    fbx_path, unreal_package_path, name, skeleton_path=None
):
    """
    Examples
        fbx_path = "/Computer/Documents/scenes/mgear_fbx_export/Butcher.fbx"
        dest_path = "/Game/Character/Boy_4"
        name = "Boy_4"
    """
    uegear_bridge = bridge.UeGearBridge()

    options = str(
        {
            "destination_name": name,
            "skeleton": skeleton_path,
            "mesh_type_to_import": True,  # this is a weird implementation
            "skeletal_mesh_import_data": str(
                {
                    "preserve_smoothing_groups": True,
                    "import_morph_targets": True,
                    "convert_scene": True,
                }
            ),
        }
    )

    result = uegear_bridge.execute(
        "import_skeletal_mesh",
        parameters={
            "fbx_file": fbx_path,
            "import_path": unreal_package_path,
            "import_options": options,
        },
    ).get("ReturnValue", [])

    return result
