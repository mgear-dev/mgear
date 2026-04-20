import os

import maya.cmds as cmds

from mgear.core import pyFBX as pfbx


class FbxSdkGameToolsWrapper(object):
    def __init__(self, filename):
        self._filename = filename
        self._scene = None
        self._sdk_manager = None
        self._root_node = None
        self._scene_nodes = list()

        if pfbx.FBX_SDK:
            (
                self._sdk_manager,
                self._scene,
            ) = pfbx.FbxCommon.InitializeSdkObjects()
            pfbx.FbxCommon.LoadScene(self._sdk_manager, self._scene, filename)
            self._root_node = self._scene.GetRootNode()
            self._scene_nodes = self.get_scene_nodes()

    def close(self):
        if not pfbx.FBX_SDK or not self._sdk_manager:
            return

        self._sdk_manager.Destroy()

    def save(
        self,
        path=None,
        mode="ascii",
        close=False,
        embed_media=False,
        file_version=None,
        preset_path=None,
        deformations=None,
        skins=None,
        blendshapes=None,
    ):

        if not pfbx.FBX_SDK:
            return False

        file_format = -1
        if mode == "binary":
            file_format = 0

        exporter = pfbx.fbx.FbxExporter.Create(self._scene, "")
        if (
            file_format < 0
            or file_format
            >= self._sdk_manager.GetIOPluginRegistry().GetWriterFormatCount()
        ):
            file_format = (
                self._sdk_manager.GetIOPluginRegistry().GetNativeWriterFormat()
            )
            if not embed_media:
                format_count = (
                    self._sdk_manager.GetIOPluginRegistry().GetWriterFormatCount()
                )
                for format_index in range(format_count):
                    if self._sdk_manager.GetIOPluginRegistry().WriterIsFBX(
                        format_index
                    ):
                        desc = self._sdk_manager.GetIOPluginRegistry().GetWriterFormatDescription(
                            format_index
                        )
                        if "ascii" in desc:
                            file_format = format_index
                            break

        if not self._sdk_manager.GetIOSettings():
            ios = pfbx.fbx.FbxIOSettings.Create(
                self._sdk_manager, pfbx.fbx.IOSROOT
            )
            self._sdk_manager.SetIOSettings(ios)

        self._sdk_manager.GetIOSettings().SetBoolProp(
            pfbx.fbx.EXP_FBX_MATERIAL, True
        )
        self._sdk_manager.GetIOSettings().SetBoolProp(
            pfbx.fbx.EXP_FBX_TEXTURE, True
        )
        self._sdk_manager.GetIOSettings().SetBoolProp(
            pfbx.fbx.EXP_FBX_EMBEDDED, embed_media
        )
        self._sdk_manager.GetIOSettings().SetBoolProp(
            pfbx.fbx.EXP_FBX_SHAPE, True
        )
        self._sdk_manager.GetIOSettings().SetBoolProp(
            pfbx.fbx.EXP_FBX_GOBO, True
        )
        self._sdk_manager.GetIOSettings().SetBoolProp(
            pfbx.fbx.EXP_FBX_ANIMATION, True
        )
        self._sdk_manager.GetIOSettings().SetBoolProp(
            pfbx.fbx.EXP_FBX_GLOBAL_SETTINGS, True
        )

        if deformations is not None:
            self._sdk_manager.GetIOSettings().SetBoolProp(
                "Deformations", deformations
            )
        if skins is not None:
            self._sdk_manager.GetIOSettings().SetBoolProp("Skins", skins)
        if blendshapes is not None:
            self._sdk_manager.GetIOSettings().SetBoolProp(
                "Blend Shapes", blendshapes
            )

        # override FBX settins from FBX preset file path (if it exists)
        if preset_path and os.path.isfile(preset_path):
            self._sdk_manager.GetIOSettings().ReadXMLFile(preset_path)

        save_path = path or self._filename
        result = exporter.Initialize(
            save_path, file_format, self._sdk_manager.GetIOSettings()
        )
        if result is False:
            exporter.Destroy()
            return False

        if file_version is not None:
            exporter.SetFileExportVersion(
                file_version, pfbx.fbx.FbxSceneRenamer.eNone
            )
        result = exporter.Export(self._scene)

        exporter.Destroy()

        if close:
            self.close()

        return True

    def get_file_format(self, format_name):

        if not pfbx.FBX_SDK:
            return None

        io_plugin_registry = self._sdk_manager.GetIOPluginRegistry()
        for format_id in range(io_plugin_registry.GetWriterFormatCount()):
            if io_plugin_registry.WriterIsFBX(format_id):
                desc = io_plugin_registry.GetWriterFormatDescription(format_id)
                if format_name in desc:
                    return format_id

        # Default format is auto
        return -1

    def get_scene_nodes(self):

        if not pfbx.FBX_SDK:
            return list()

        def _get_scene_nodes(_node):
            self._scene_nodes.append(_node)
            for i in range(_node.GetChildCount()):
                _get_scene_nodes(_node.GetChild(i))

        self._scene_nodes = list()
        for i in range(self._root_node.GetChildCount()):
            _get_scene_nodes(self._root_node.GetChild(i))

        return self._scene_nodes

    def get_type_nodes(self, type):

        if not pfbx.FBX_SDK or not self._scene:
            return list()

        nodes = list()
        for i in range(self._scene.RootProperty.GetSrcObjectCount()):
            node = self._scene.RootProperty.GetSrcObject(i)
            if not node:
                continue
            if node.GetTypeName() == type:
                nodes.append(node)

        return nodes

    def get_meshes(self):
        return self.get_type_nodes("Mesh")

    def get_joints(self):
        return self.get_type_nodes("LimbNode")

    def _cast_property(fbx_property):

        if not pfbx.FBX_SDK:
            return None

        unsupported_types = [
            pfbx.fbx.eFbxUndefined,
            pfbx.fbx.eFbxChar,
            pfbx.fbx.eFbxUChar,
            pfbx.fbx.eFbxShort,
            pfbx.fbx.eFbxUShort,
            pfbx.fbx.eFbxUInt,
            pfbx.fbx.eFbxLongLong,
            pfbx.fbx.eFbxHalfFloat,
            pfbx.fbx.eFbxDouble4x4,
            pfbx.fbx.eFbxEnum,
            pfbx.fbx.eFbxTime,
            pfbx.fbx.eFbxReference,
            pfbx.fbx.eFbxBlob,
            pfbx.fbx.eFbxDistance,
            pfbx.fbx.eFbxDateTime,
            pfbx.fbx.eFbxTypeCount,
        ]

        casted_property = None

        # property is not supported or mapped yet
        property_type = fbx_property.GetPropertyDataType().GetType()
        if property_type in unsupported_types:
            return None

        if property_type == pfbx.fbx.eFbxBool:
            casted_property = pfbx.fbx.FbxPropertyBool1(fbx_property)
        elif property_type == pfbx.fbx.eFbxDouble:
            casted_property = pfbx.fbx.FbxPropertyDouble1(fbx_property)
        elif property_type == pfbx.fbx.eFbxDouble2:
            casted_property = pfbx.fbx.FbxPropertyDouble2(fbx_property)
        elif property_type == pfbx.fbx.eFbxDouble3:
            casted_property = pfbx.fbx.FbxPropertyDouble3(fbx_property)
        elif property_type == pfbx.fbx.eFbxDouble4:
            casted_property = pfbx.fbx.FbxPropertyDouble4(fbx_property)
        elif property_type == pfbx.fbx.eFbxInt:
            casted_property = pfbx.fbx.FbxPropertyInteger1(fbx_property)
        elif property_type == pfbx.fbx.eFbxFloat:
            casted_property = pfbx.fbx.FbxPropertyFloat1(fbx_property)
        elif property_type == pfbx.fbx.eFbxString:
            casted_property = pfbx.fbx.FbxPropertyString(fbx_property)
        else:
            raise ValueError(
                "未知属性类型: {0} {1}".format(
                    property.GetPropertyDataType().GetName(), property_type
                )
            )

        return casted_property

    def get_property_value(self, fbx_property):
        casted_property = (
            self.cast_property(fbx_property)
            if fbx_property and fbx_property.IsValid()
            else None
        )
        return casted_property.Get() if casted_property else None

    def clean_scene(
        self, no_export_tag="no_export", world_control_name="world_ctl"
    ):
        self.remove_non_exportable_nodes(no_export_tag=no_export_tag)
        self.remove_world_control(control_name=world_control_name)

    def remove_non_exportable_nodes(self, no_export_tag="no_export"):

        nodes_to_delete = list()
        scene_nodes = self.get_scene_nodes()
        for node in scene_nodes:
            property_value = self.get_property_value(
                node.FindProperty(no_export_tag)
            )
            if property_value is True:
                nodes_to_delete.append(node)
        for node_to_delete in nodes_to_delete:
            self._scene.DisconnectSrcObject(node_to_delete)
            self._scene.RemoveNode(node_to_delete)

        # force the update of the internal cache of scene nodes
        self.get_scene_nodes()

    def remove_world_control(self, control_name="world_ctl"):

        node_to_delete = None
        scene_nodes = self.get_scene_nodes()
        for node in scene_nodes:
            if node.GetName() == control_name:
                node_to_delete = node
                break
        if not node_to_delete:
            return False

        self._scene.DisconnectSrcObject(node_to_delete)
        self._scene.RemoveNode(node_to_delete)

        # force the update of the internal cache of scene nodes
        self.get_scene_nodes()

    def remove_namespaces(self):

        scene_nodes = self.get_scene_nodes()
        for node in scene_nodes:
            orig_name = node.GetName()
            split_by_colon = orig_name.split(":")
            if len(split_by_colon) > 1:
                new_name = split_by_colon[-1:][0]
                node.SetName(new_name)

        return True

    def parent_to_world(self, node_name, remove_top_parent=False):

        node_to_parent_to_world = None
        scene_nodes = self.get_scene_nodes()
        for node in scene_nodes:
            if node.GetName() == node_name:
                node_to_parent_to_world = node
                break
        if not node_to_parent_to_world:
            return False

        parent = node_to_parent_to_world.GetParent()
        if parent is not None and parent != self._root_node:
            self._root_node.AddChild(node_to_parent_to_world)

        top_parent = None
        if parent and parent != self._root_node and remove_top_parent:
            _parent = parent.GetParent()
            while True:
                top_parent = _parent
                try:
                    _parent = _parent.GetParent()
                except AttributeError:
                    _parent = self._root_node
                    break
                if _parent == self._root_node:
                    break
        if top_parent:
            self._scene.DisconnectSrcObject(top_parent)
            self._scene.RemoveNode(top_parent)

        # force the update of the internal cache of scene nodes
        self.get_scene_nodes()

    def export_skeletal_mesh(
        self,
        file_name,
        mesh_names,
        hierarchy_joints,
        deformations=None,
        skins=None,
        blendshapes=None,
    ):

        # if not pfbx.FBX_SDK:
        #     cmds.warning(
        #         "Export Skeletal Mesh functionality is only available if Python FBX SDK is available!"
        #     )
        #     return None

        # TODO: Check how we can retrieve the long name using FBX SDK
        short_mesh_names = [
            mesh_name.split("|")[-1] for mesh_name in mesh_names
        ]

        meshes_to_export = list()
        meshes_to_delete = list()
        meshes_nodes = self.get_meshes()
        for mesh_node in meshes_nodes:
            if mesh_node.GetName() in short_mesh_names:
                meshes_to_export.append(mesh_node)
            else:
                if mesh_node.GetName():
                    meshes_to_delete.append(mesh_node)
        if not meshes_to_export:
            cmds.warning(
                '未找到名为 "{}" 的网格可供导出！'.format(mesh_names)
            )
            return None

        # ensure hierarchy has no duplicated joints
        hierarchy = set(list(hierarchy_joints))

        skeleton_joints = list()
        joints_to_remove = list()
        scene_joints = self.get_joints()
        for scene_joint in scene_joints:
            if not scene_joint or scene_joint.GetName() not in hierarchy:
                if not scene_joint.GetName():
                    continue
                joints_to_remove.append(scene_joint)
            else:
                skeleton_joints.append(scene_joint)
        if len(hierarchy) != len(skeleton_joints):
            cmds.warning(
                "关节不匹配 ({} / {})".format(
                    len(hierarchy), len(skeleton_joints)
                )
            )
            return None

        for mesh_to_delete in meshes_to_delete:
            self._scene.DisconnectSrcObject(mesh_to_delete)
            self._scene.RemoveNode(mesh_to_delete)

        for joint_to_delete in joints_to_remove:
            self._scene.DisconnectSrcObject(joint_to_delete)
            self._scene.RemoveNode(joint_to_delete)

        save_path = os.path.join(
            os.path.dirname(self._filename),
            "{}_{}.fbx".format(
                os.path.splitext(os.path.basename(self._filename))[0],
                file_name,
            ),
        )
        self.save(
            save_path,
            deformations=deformations,
            skins=skins,
            blendshapes=blendshapes,
        )
