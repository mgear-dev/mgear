import importlib
import json
import os
import timeit
from functools import partial

import maya.cmds as cmds
import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mgear.vendor.Qt import QtWidgets, QtCore

from mgear.core import (
    pyqt,
    pyFBX as pfbx,
    string,
    widgets,
)
import mgear.shifter.game_tools_disconnect as gtDisc
from mgear.shifter.game_tools_fbx import (
    anim_clip_widgets,
    fbx_export_node,
    partitions_outliner,
    utils,
    partition_thread
)
from mgear.uegear import commands as uegear


class FBXExporter(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(FBXExporter, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowTitle("Shifter's FBX Export")
        min_w = 300
        default_w = 400
        default_h = 1000
        self.setMinimumWidth(min_w)
        self.resize(default_w, default_h)

        self.create_layout()
        self.create_connections()
        self._load_node_data_to_widget()

    def closeEvent(self, event):
        self._save_data_to_export_node()
        super(FBXExporter, self).closeEvent(event)

    def dockCloseEventTriggered(self):
        # FIXME: Move the save_data before calling the super close. Check all saving works!
        super(FBXExporter, self).dockCloseEventTriggered()
        self._save_data_to_export_node()

    def create_layout(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.setSpacing(2)

        self.create_menu_bar()
        self.create_source_elements_widget()
        self.create_settings_widget()
        self.create_file_path_widget()
        self.create_unreal_import_widget()
        self.create_export_widget()

        # TODO: need for settings manager but currently not in use, consider removing
        self.widget_dict = {
            "geo_roots": self.geo_root_list,
            "joint_root": self.joint_root_lineedit,
            "up_axis": self.up_axis_combobox,
            "file_type": self.file_type_combobox,
            "fbx_version": self.fbx_version_combobox,
            "remove_namespace": self.remove_namespace_checkbox,
            "scene_clean": self.clean_scene_checkbox,
            "file_path": self.file_path_lineedit,
            "file_name": self.file_name_lineedit,
            "skinning": self.skinning_checkbox,
            "blendshapes": self.blendshapes_checkbox,
            "use_partitions": self.partitions_checkbox,
            "partitions": self.partitions_outliner,
            "anim_clips": self.anim_clips_listwidget,
            "fbx_export_presets": self.fbx_export_presets_combobox,
            "ue_enabled": self.ue_import_cbx,
            "ue_file_path": self.ue_file_path_lineedit,
            "ue_active_skeleton": self.ue_skeleton_listwgt,
            "cull_joints": self.culljoints_checkbox,
        }

    def create_menu_bar(self):
        # menu bar
        self.menu_bar = QtWidgets.QMenuBar()
        self.main_layout.setMenuBar(self.menu_bar)

        # file actions
        self.file_menu = self.menu_bar.addMenu("File")
        self.file_export_preset_action = QtWidgets.QAction(
            "Export Shifter FBX Preset", self
        )
        self.file_export_preset_action.setIcon(pyqt.get_icon("mgear_log-out"))
        self.file_import_preset_action = QtWidgets.QAction(
            "Import Shifter FBX Preset", self
        )
        self.file_import_preset_action.setIcon(pyqt.get_icon("mgear_log-in"))
        self.file_menu.addAction(self.file_export_preset_action)
        self.file_menu.addAction(self.file_import_preset_action)

    def create_source_elements_widget(self):
        def create_button(
            layout, label="", icon=None, max_width=40, max_height=20
        ):
            button = QtWidgets.QPushButton(label)
            button.setMaximumSize(max_width, max_height)
            if icon:
                button.setIcon(pyqt.get_icon(icon))
            layout.addWidget(button)
            return button

        # main collapsible widget layout
        source_collap_wgt = widgets.CollapsibleWidget("Source Elements")
        source_collap_wgt.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        )
        self.main_layout.addWidget(source_collap_wgt)

        source_layout = QtWidgets.QGridLayout()
        source_layout.setSpacing(2)
        source_collap_wgt.addLayout(source_layout)

        # geo root layout
        geo_layout = QtWidgets.QVBoxLayout()
        source_layout.addLayout(geo_layout, 0, 0)

        geo_label = QtWidgets.QLabel("Geo Root")
        geo_layout.addWidget(geo_label)
        self.geo_root_list = QtWidgets.QListWidget()
        self.geo_root_list.setSelectionMode(
            QtWidgets.QListWidget.ExtendedSelection
        )
        geo_layout.addWidget(self.geo_root_list)

        geo_buttons_layout = QtWidgets.QVBoxLayout()
        source_layout.addLayout(geo_buttons_layout, 0, 1)

        geo_buttons_layout.addStretch()
        self.geo_set_btn = create_button(
            geo_buttons_layout, icon="mgear_mouse-pointer"
        )
        self.geo_add_btn = create_button(geo_buttons_layout, icon="mgear_plus")
        self.geo_rem_btn = create_button(
            geo_buttons_layout, icon="mgear_minus"
        )
        self.geo_auto_set_btn = create_button(geo_buttons_layout, label="Auto")
        geo_buttons_layout.addStretch()

        # joint root layout
        joint_layout = QtWidgets.QVBoxLayout()
        source_layout.addLayout(joint_layout, 1, 0)

        joint_label = QtWidgets.QLabel("Joint Root")
        joint_layout.addWidget(joint_label)
        self.joint_root_lineedit = QtWidgets.QLineEdit()
        joint_layout.addWidget(self.joint_root_lineedit)

        joint_buttons_layout = QtWidgets.QVBoxLayout()
        source_layout.addLayout(joint_buttons_layout, 1, 1)
        self.joint_set_btn = create_button(
            joint_buttons_layout, icon="mgear_mouse-pointer"
        )
        self.joint_auto_set_btn = create_button(
            joint_buttons_layout, label="Auto"
        )

    def create_settings_widget(self):
        # main collapsible widget layout
        settings_collap_wgt = widgets.CollapsibleWidget("Settings")
        settings_collap_wgt.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        )
        self.main_layout.addWidget(settings_collap_wgt)
        settings_tab = QtWidgets.QTabWidget()
        settings_collap_wgt.addWidget(settings_tab)

        # fbx settings tab
        fbx_tab = QtWidgets.QWidget()
        settings_tab.addTab(fbx_tab, "FBX")
        settings_layout = QtWidgets.QGridLayout(fbx_tab)

        up_label = QtWidgets.QLabel("Up Axis")
        self.up_axis_combobox = QtWidgets.QComboBox()
        self.up_axis_combobox.addItems(["Y", "Z"])
        settings_layout.addWidget(up_label, 0, 0)
        settings_layout.addWidget(self.up_axis_combobox, 0, 1)

        file_type_label = QtWidgets.QLabel("File Type")
        self.file_type_combobox = QtWidgets.QComboBox()
        self.file_type_combobox.addItems(["Binary", "ASCII"])
        settings_layout.addWidget(file_type_label, 0, 2)
        settings_layout.addWidget(self.file_type_combobox, 0, 3)

        fbx_version_label = QtWidgets.QLabel("FBX Version")
        self.fbx_version_combobox = QtWidgets.QComboBox()
        self.fbx_version_combobox.addItems(pfbx.get_fbx_versions())
        settings_layout.addWidget(fbx_version_label, 1, 0)
        settings_layout.addWidget(self.fbx_version_combobox, 1, 1)

        fbx_preset_label = QtWidgets.QLabel("FBX Preset")
        self.fbx_export_presets_combobox = QtWidgets.QComboBox()
        self.populate_fbx_presets_combobox()
        settings_layout.addWidget(fbx_preset_label, 1, 2)
        settings_layout.addWidget(self.fbx_export_presets_combobox, 1, 3)

        # fbx conditioning, settings tab
        fbx_sdk_tab = QtWidgets.QWidget()
        settings_tab.addTab(fbx_sdk_tab, "FBX Conditioning")
        fbx_sdk_layout = QtWidgets.QVBoxLayout(fbx_sdk_tab)

        self.remove_namespace_checkbox = QtWidgets.QCheckBox(
            "Remove Namespace"
        )
        self.remove_namespace_checkbox.setChecked(True)
        self.clean_scene_checkbox = QtWidgets.QCheckBox(
            "Joint and Geo Root Child of Scene Root + Clean Up Scene"
        )
        self.clean_scene_checkbox.setChecked(True)
        fbx_sdk_layout.addWidget(self.remove_namespace_checkbox)
        fbx_sdk_layout.addWidget(self.clean_scene_checkbox)

    def create_file_path_widget(self):
        # main collapsible widget layout
        file_path_collap_wgt = widgets.CollapsibleWidget("File Path")
        file_path_collap_wgt.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        )
        self.main_layout.addWidget(file_path_collap_wgt)
        path_main_layout = QtWidgets.QVBoxLayout()
        path_main_layout.setSpacing(2)
        file_path_collap_wgt.addLayout(path_main_layout)

        # export path
        file_path_layout = QtWidgets.QHBoxLayout()
        file_path_layout.setContentsMargins(1, 1, 1, 1)
        path_main_layout.addLayout(file_path_layout)

        directory_label = QtWidgets.QLabel("Directory ")
        self.file_path_lineedit = QtWidgets.QLineEdit()
        self.file_set_btn = widgets.create_button(icon="mgear_folder")
        file_path_layout.addWidget(directory_label)
        file_path_layout.addWidget(self.file_path_lineedit)
        file_path_layout.addWidget(self.file_set_btn)

        # export file name
        file_name_layout = QtWidgets.QHBoxLayout()
        file_name_layout.setContentsMargins(1, 1, 1, 1)
        path_main_layout.addLayout(file_name_layout)

        file_name_label = QtWidgets.QLabel("File Name")
        self.file_name_lineedit = QtWidgets.QLineEdit()
        file_name_layout.addWidget(file_name_label)
        file_name_layout.addWidget(self.file_name_lineedit)

    def create_unreal_import_widget(self):
        self.ue_import_collap_wgt = widgets.CollapsibleWidget(
            "Unreal Engine Import"
        )
        self.ue_import_collap_wgt.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        )
        self.main_layout.addWidget(self.ue_import_collap_wgt)

        self.ue_import_cbx = QtWidgets.QCheckBox("Enable Unreal Engine Import")
        self.ue_import_collap_wgt.addWidget(self.ue_import_cbx)

        ue_path_main_layout = QtWidgets.QVBoxLayout()
        ue_path_main_layout.addSpacing(2)
        self.ue_import_collap_wgt.addLayout(ue_path_main_layout)

        ue_file_path_layout = QtWidgets.QHBoxLayout()
        ue_file_path_layout.setContentsMargins(1, 1, 1, 1)
        ue_path_main_layout.addLayout(ue_file_path_layout)

        ue_directory_label = QtWidgets.QLabel("Directory ")
        self.ue_file_path_lineedit = QtWidgets.QLineEdit()
        self.ue_file_set_btn = widgets.create_button(icon="mgear_folder")
        ue_file_path_layout.addWidget(ue_directory_label)
        ue_file_path_layout.addWidget(self.ue_file_path_lineedit)
        ue_file_path_layout.addWidget(self.ue_file_set_btn)

        ue_skeleton_label = QtWidgets.QLabel("UE Skeletons")
        self.ue_skeleton_listwgt = QtWidgets.QListWidget()
        ue_path_main_layout.addWidget(ue_skeleton_label)
        ue_path_main_layout.addWidget(self.ue_skeleton_listwgt)

    def populate_unreal_skeletons(self):
        """
        Executes this code when UE is enabled or disabled.
        - Updates the available skeletons.
        - Selects the skeleton that exists on the FBX Export Node.
        """
        # update attribute on fbx maya node
        export_node = self._get_or_create_export_node()
        export_node.save_root_data(
            "ue_enabled", self.ue_import_cbx.isChecked()
        )

        # clears selected Items, if disabled
        if not self.ue_import_cbx.isChecked():
            for item in self.ue_skeleton_listwgt.selectedItems():
                item.setSelected(False)
            return

        # clears and populates the skeleton list
        self.ue_skeleton_listwgt.clear()
        skeleton_data = uegear.get_skeletal_data()
        for entry in skeleton_data:
            self.ue_skeleton_listwgt.addItem(str(entry["Key"]))

        # select the active skeleton that exists on the fbx node
        if self.ue_import_cbx.isChecked():
            active_skeleton = export_node.get_ue_active_skeleton()
            if active_skeleton:
                for i in range(self.ue_skeleton_listwgt.count()):
                    item = self.ue_skeleton_listwgt.item(i)
                    if item.text() == active_skeleton:
                        item.setSelected(True)
                    else:
                        item.setSelected(False)

    def create_export_widget(self):
        export_collap_wgt = widgets.CollapsibleWidget("Export")
        export_collap_wgt.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.main_layout.addWidget(export_collap_wgt)

        self.export_tab = QtWidgets.QTabWidget()
        export_collap_wgt.addWidget(self.export_tab)

        self.create_skeletal_mesh_tab()
        self.create_animation_tab()

    def create_skeletal_mesh_tab(self):
        # main collapsible widget layout
        skeletal_mesh_tab = QtWidgets.QWidget()
        self.export_tab.addTab(skeletal_mesh_tab, "Skeletal Mesh")
        skeletal_mesh_layout = QtWidgets.QVBoxLayout(skeletal_mesh_tab)

        # progress bar
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        self.default_progress_bar()
        self.progress_bar.setHidden(True)

        # deformers options
        deformers_label = QtWidgets.QLabel("Deformers")
        skeletal_mesh_layout.addWidget(deformers_label)

        deformers_layout = QtWidgets.QHBoxLayout()
        skeletal_mesh_layout.addLayout(deformers_layout)

        self.skinning_checkbox = QtWidgets.QCheckBox("Skinning")
        self.skinning_checkbox.setChecked(True)
        self.blendshapes_checkbox = QtWidgets.QCheckBox("Blendshapes")
        self.blendshapes_checkbox.setChecked(True)
        self.partitions_checkbox = QtWidgets.QCheckBox("Partitions")
        self.partitions_checkbox.setChecked(True)
        self.culljoints_checkbox = QtWidgets.QCheckBox("Cull Joints")
        self.culljoints_checkbox.setChecked(False)
        deformers_layout.addWidget(self.skinning_checkbox)
        deformers_layout.addWidget(self.blendshapes_checkbox)
        deformers_layout.addWidget(self.partitions_checkbox)
        deformers_layout.addWidget(self.culljoints_checkbox)

        # partitions layout
        self.partitions_label = QtWidgets.QLabel("Partitions")
        skeletal_mesh_layout.addWidget(self.partitions_label)
        partitions_layout = QtWidgets.QHBoxLayout()
        skeletal_mesh_layout.addLayout(partitions_layout)

        # partitions outliner
        self.partitions_outliner = partitions_outliner.PartitionsOutliner()
        partitions_layout.addWidget(self.partitions_outliner)

        # partition buttons
        partition_buttons_layout = QtWidgets.QVBoxLayout()
        partition_buttons_layout.addStretch()
        partitions_layout.addLayout(partition_buttons_layout)

        self.skmesh_add_btn = QtWidgets.QPushButton()
        self.skmesh_add_btn.setIcon(pyqt.get_icon("mgear_plus"))
        partition_buttons_layout.addWidget(self.skmesh_add_btn)

        self.skmesh_rem_btn = QtWidgets.QPushButton()
        self.skmesh_rem_btn.setIcon(pyqt.get_icon("mgear_minus"))
        partition_buttons_layout.addWidget(self.skmesh_rem_btn)
        partition_buttons_layout.addStretch()

        # export button
        self.skmesh_export_btn = QtWidgets.QPushButton(
            "Export SkeletalMesh/SkinnedMesh"
        )
        self.skmesh_export_btn.setStyleSheet(
            "QPushButton {background:rgb(70, 100, 150);}"
        )
        skeletal_mesh_layout.addWidget(self.skmesh_export_btn)
        skeletal_mesh_layout.addWidget(self.progress_bar)

    def update_progress_bar(self, value):
        self.progress_bar.setValue(int(value))

    def create_animation_tab(self):
        # export animation
        animation_tab = QtWidgets.QWidget()
        self.export_tab.addTab(animation_tab, "Animation")
        animation_layout = QtWidgets.QVBoxLayout(animation_tab)

        self.anim_clips_listwidget = anim_clip_widgets.AnimClipsListWidget(
            parent=self
        )
        animation_layout.addWidget(self.anim_clips_listwidget)

        self.anim_export_btn = QtWidgets.QPushButton("Export Animations")
        self.anim_export_btn.setStyleSheet(
            "QPushButton {background:rgb(150, 35, 50);}"
        )
        animation_layout.addWidget(self.anim_export_btn)

    def create_connections(self):
        # menu connections
        self.file_export_preset_action.triggered.connect(self.export_fbx_presets)
        self.file_import_preset_action.triggered.connect(self.import_fbx_presets)

        # source element connections
        self.geo_set_btn.clicked.connect(
            partial(
                self._add_list_items_from_sel,
                self.geo_root_list,
                "transform",
                clear=True,
            )
        )
        self.geo_add_btn.clicked.connect(
            partial(
                self._add_list_items_from_sel, self.geo_root_list, "transform"
            )
        )
        self.geo_rem_btn.clicked.connect(
            partial(self._remove_list_items_from_sel, self.geo_root_list)
        )
        self.geo_auto_set_btn.clicked.connect(
            partial(self._auto_set_geo_roots, clear=True)
        )

        self.joint_set_btn.clicked.connect(
            partial(
                self._set_lineedit_text_from_sel,
                self.joint_root_lineedit,
                "joint",
            )
        )
        self.joint_auto_set_btn.clicked.connect(
            partial(self._auto_set_joint_root)
        )

        # file path connections
        self.file_set_btn.clicked.connect(self.set_folder_path)
        self.file_name_lineedit.textChanged.connect(self.normalize_name)

        self.file_path_lineedit.textChanged.connect(self.set_fbx_directory)
        self.file_name_lineedit.textChanged.connect(self.set_fbx_file)

        # ue file path connection
        self.ue_file_set_btn.clicked.connect(self.set_ue_folder_path)

        # Disables all unreal skeletal fields unless the user enables the checkbox
        self.ue_file_path_lineedit.setReadOnly(
            self.ue_import_cbx.checkState() == QtCore.Qt.Unchecked
        )
        self.ue_import_cbx.stateChanged.connect(
            lambda state: self.ue_file_path_lineedit.setReadOnly(
                state == QtCore.Qt.Unchecked
            )
        )
        self.ue_file_path_lineedit.setEnabled(
            self.ue_import_cbx.checkState() != QtCore.Qt.Unchecked
        )
        self.ue_import_cbx.stateChanged.connect(
            lambda state: self.ue_file_path_lineedit.setEnabled(
                state != QtCore.Qt.Unchecked
            )
        )
        self.ue_file_set_btn.setEnabled(
            self.ue_import_cbx.checkState() != QtCore.Qt.Unchecked
        )
        self.ue_import_cbx.stateChanged.connect(
            lambda state: self.ue_file_set_btn.setEnabled(
                state != QtCore.Qt.Unchecked
            )
        )
        self.ue_skeleton_listwgt.setEnabled(
            self.ue_import_cbx.checkState() != QtCore.Qt.Unchecked
        )
        self.ue_import_cbx.stateChanged.connect(
            lambda state: self.ue_skeleton_listwgt.setEnabled(
                state != QtCore.Qt.Unchecked
            )
        )
        self.ue_import_cbx.stateChanged.connect(self.populate_unreal_skeletons)
        self.ue_skeleton_listwgt.itemClicked.connect(self.ue_skeleton_updated)
        self.ue_file_path_lineedit.editingFinished.connect(
            self.ue_filepath_updated
        )

        # skeletal mesh connections
        self.partitions_checkbox.toggled.connect(self.set_use_partitions)
        self.skmesh_add_btn.clicked.connect(self.add_skeletal_mesh_partition)
        self.skmesh_rem_btn.clicked.connect(
            self.remove_skeletal_mesh_partition
        )
        self.skmesh_export_btn.clicked.connect(self.export_skeletal_mesh)

        # animation connection
        self.anim_export_btn.clicked.connect(self.export_animation_clips)

        # partition skinning connection
        self.skinning_checkbox.toggled.connect(self.partition_skinning_toggled)
        self.blendshapes_checkbox.toggled.connect(
            self.partition_blendshape_toggled
        )
        self.culljoints_checkbox.toggled.connect(self.cull_joints_toggled)

    def get_root_joint(self):
        root_joint = self.joint_root_lineedit.text().split(",")
        return root_joint[0] if root_joint else None

    def get_export_path(self):
        return self.file_path_lineedit.text()

    def get_file_name(self):
        return self.file_name_lineedit.text()

    def get_remove_namespace(self):
        return self.remove_namespace_checkbox.isChecked()

    def get_scene_clean(self):
        return self.clean_scene_checkbox.isChecked()

    def normalize_name(self):
        name = string.removeInvalidCharacter2(self.file_name_lineedit.text())
        self.file_name_lineedit.setText(name)

    def export_fbx_presets(self):
        dialog = QtWidgets.QFileDialog()
        export_file = dialog.getSaveFileName()[0]
        if not export_file:
            return False
        file_name, file_ext = os.path.splitext(export_file)
        if not file_ext or file_ext != ".json":
            export_file = "{}.json".format(file_name)
        export_data = self._save_data_to_export_node()
        with open(export_file, "w") as f:
            json.dump(export_data, f)
        return export_data

    def import_fbx_presets(self):
        dialog = QtWidgets.QFileDialog()
        import_file = dialog.getOpenFileName()[0]
        _, file_ext = os.path.splitext(import_file)
        if not import_file or file_ext != ".json":
            return False
        with open(import_file, "r") as f:
            import_data = json.load(f)

        # populates the fbx export maya node with json data
        export_node = self._get_or_create_export_node()
        export_node.save_data(import_data)

        self._set_tool_data(import_data)
        return import_data

    def populate_fbx_presets_combobox(self):
        combobox = self.fbx_export_presets_combobox
        filepaths = pfbx.get_fbx_export_presets()

        for path in filepaths:
            fbx_filename = os.path.basename(path)
            fbx_base_filename, _ = os.path.splitext(fbx_filename)
            combobox.addItem(fbx_base_filename, userData=path)
        # Force user defined as the default preset
        combobox.setCurrentText("User defined")

    def set_folder_path(self):
        folder_path = pm.fileDialog2(fileMode=3)
        if folder_path:
            self.file_path_lineedit.setText(
                string.normalize_path(folder_path[0])
            )

    def ue_filepath_updated(self):
        path = self.ue_file_path_lineedit.text()
        # update attribute on fbx maya node
        export_node = self._get_or_create_export_node()
        export_node.save_root_data("ue_file_path", path)

    def ue_skeleton_updated(self):
        selected_skeletons = self.ue_skeleton_listwgt.selectedItems()
        if len(selected_skeletons) == 1:
            # update attribute on fbx maya node
            export_node = self._get_or_create_export_node()
            export_node.save_root_data(
                "ue_active_skeleton", selected_skeletons[0].text()
            )
        elif len(selected_skeletons) == 0:
            # update attribute on fbx maya node
            export_node = self._get_or_create_export_node()
            export_node.save_root_data("ue_active_skeleton", "")

    def set_ue_folder_path(self):
        folders = uegear.get_selected_content_browser_folder(relative=True)
        if len(folders) == 1:
            # Removes the 'All' as we want an unreal package path
            components = folders[0].split("/")
            components.remove("")
            ue_package_path = os.path.sep + os.path.sep.join(components[1:])
            path = string.normalize_path(ue_package_path)
            self.ue_file_path_lineedit.setText(path)

            # update attribute on fbx maya node
            export_node = self._get_or_create_export_node()
            export_node.save_root_data("ue_file_path", path)

    def set_use_partitions(self, flag):
        self.partitions_outliner.setEnabled(flag)
        self.partitions_label.setEnabled(flag)
        self.skmesh_add_btn.setEnabled(flag)
        self.skmesh_rem_btn.setEnabled(flag)

    def cull_joints_toggled(self, flag):
        cull_joint_active = self.culljoints_checkbox.isChecked()
        export_node = self._get_or_create_export_node()
        export_node.save_root_data("cull_joints", cull_joint_active)

    def partition_skinning_toggled(self):
        """Updates the Maya FBX Node, when checkbox it changed"""
        skinning_active = self.skinning_checkbox.isChecked()
        export_node = self._get_or_create_export_node()
        export_node.save_root_data("skinning", skinning_active)

    def partition_blendshape_toggled(self):
        """Updates the Maya FBX Node, when checkbox it changed"""
        skinning_active = self.blendshapes_checkbox.isChecked()
        export_node = self._get_or_create_export_node()
        export_node.save_root_data("blendshapes", skinning_active)

    def add_skeletal_mesh_partition(self):
        export_node = self._get_or_create_export_node()
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "New Partition",
            "New Partition",
            QtWidgets.QLineEdit.Normal,
            "New Partition",
        )
        if not (name and ok):
            return
        result = export_node.add_new_skeletal_mesh_partition(name, [])
        if not result:
            return
        self.partitions_outliner.reset_contents()

    def remove_skeletal_mesh_partition(self):
        selected_partition_items = self.partitions_outliner.selectedItems()
        if not selected_partition_items:
            return

        for selected_partition_item in selected_partition_items:
            if selected_partition_item.node.is_master:
                return

        response = cmds.confirmDialog(
            title="Confirm",
            message="Confirm Deletion",
            button=["Yes", "No"],
            defaultButton="Yes",
            cancelButton="No",
            dismissString="No",
        )
        if response == "Yes":
            for selected_partition_item in selected_partition_items:
                selected_partition_item.delete_node()

    def export_skeletal_mesh(self):
        # Check if UE import is enabled, and if a directory is specified.
        # - If no directory is specified, fail.
        if (
            self.ue_import_cbx.isChecked()
            and self.ue_file_path_lineedit.text() == ""
        ):
            cmds.warning("Please specify an import location.")
            cmds.confirmDialog(
                title="Export Failed",
                message="Please specify an Unreal package path directory.",
                messageAlign="center",
                button=["Okay"],
                cancelButton="Okay",
                dismissString="Okay",
            )
            return False

        print("----- Exporting Skeletal Meshes -----")
        export_node = self._get_or_create_export_node()

        geo_roots = self._get_listwidget_item_names(self.geo_root_list)
        if not geo_roots:
            cmds.warning("No geo roots defined!")
            return False
        joint_root = self.get_root_joint()
        if not joint_root:
            cmds.warning("No Joint Root defined!")
            return False
        print("\t>>> Geo Roots: {}".format(geo_roots))
        print("\t>>> Joint Root: {}".format(joint_root))

        self._auto_set_file_path()
        file_path = self.file_path_lineedit.text()
        file_name = self.file_name_lineedit.text()

        # Check file path exists, else creates it
        if not os.path.exists(file_path):
            os.makedirs(file_path)
            if not os.path.exists(file_path):
                return False

        if not (file_path and file_name):
            cmds.warning("Not valid file path and name defined!")
            return False

        # retrieve export config
        export_config = self._get_current_tool_data()

        use_partitions = self.partitions_checkbox.isChecked()
        if use_partitions:
            export_config["partitions"] = self._prefilter_partitions()

        preset_file_path = self._get_preset_file_path()
        print("\t>>> Preset File Path: {}".format(preset_file_path))

        self.default_progress_bar()
        self.progress_bar.setHidden(False)

        # Creates a Thread to perform the maya batch in.
        self.partition_thread = partition_thread.PartitionThread(export_config)
        # Settup Thread Signals
        self.partition_thread.completed.connect(self._import_into_unreal)
        self.partition_thread.progress_signal.connect(self.update_progress_bar)
        # Show the process is starting
        self.update_progress_bar(5)
        self.partition_thread.init_data()
        self.partition_thread.start()

        return True

    def update_progress_bar(self, value: int):
        """
        Updates the progress bar in the GUI.
        """
        value = int(value)
        self.progress_bar.setValue(value)

        # if value == 100:
        #     self.progress_bar.setHidden(True)

    def error_progress_bar(self):
        """
        Sets the progress bar to be red, errored
        """
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #9c1e1e;
            }
        """)
        self.progress_bar.update()

    def default_progress_bar(self):
        """
        Sets the progress bar to its default green colour.
        """
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        self.progress_bar.update()


    def _import_into_unreal(self, export_config, success):
        """
        Event triggered when the Thread has completed successfully.

        Impports the asset into unreal, and checks if it should import using 
        an existing skeleton.

        Recieves the export configuration from the Thread that was completed
        """
        if not success:
            print("ERROR: Export Failed")
            self.error_progress_bar()
            return

        use_partitions = export_config.get("use_partitions", True)
        partitions = export_config.get("partitions", dict())
        file_name = export_config.get("file_name", "")
        file_path = export_config.get("file_path", "")

        master_fbx_path = os.path.join(file_path, file_name) + ".fbx"

        # Unreal Import, if enabled.
        if self.ue_import_cbx.isChecked():
            # If skeleton is option is enabled, then import an SKM and
            # share the base skeleton in Unreal.
            skeleton_path = None
            if len(self.ue_skeleton_listwgt.selectedItems()) > 0:
                skeleton_path = self.ue_skeleton_listwgt.selectedItems()[0].text()
            unreal_folder = self.ue_file_path_lineedit.text()

            if use_partitions:
                for p in partitions.keys():
                    result_partition = master_fbx_path.replace(
                        ".fbx", "_{}.fbx".format(p)
                    )
                    partition_file_name = file_name + "_{}".format(p)
                    uegear.export_skeletal_mesh_to_unreal(
                        fbx_path=result_partition,
                        unreal_package_path=unreal_folder,
                        name=partition_file_name,
                        skeleton_path=skeleton_path,
                    )
            else:
                uegear.export_skeletal_mesh_to_unreal(
                    fbx_path=master_fbx_path,
                    unreal_package_path=unreal_folder,
                    name=file_name,
                    skeleton_path=skeleton_path,
               )

        # Complete
        self.update_progress_bar(100)

    def _prefilter_partitions(self):
        """
        Helper function that retrieves all partitions, and filters out the ones
        that are deactivated.
        """
        export_node = self._get_or_create_export_node()
        # Master partition data is retrieved from UI
        partitions = {}
        master_partition = self.partitions_outliner.get_master_partition()
        partitions.update(master_partition)
        partitions.update(export_node.get_partitions())
        print("\t>>> Partitions:")
        
        # Loops over partitions, and removes any disabled partitions, from being exported.
        keys = list(partitions.keys())
        for partition_name in reversed(keys):
            partition_data = partitions[partition_name]
            enabled = partition_data.get("enabled", True)
            skeletal_meshes = partition_data.get("skeletal_meshes", [])

            if not (enabled and skeletal_meshes):
                partitions.pop(partition_name)
                print("\t\t[!Partition Disabled!] - {}: {}".format(partition_name, skeletal_meshes))
                continue

            print("\t\t{}: {}".format(partition_name, skeletal_meshes))
        return partitions

    def set_fbx_directory(self):
        path = self.file_path_lineedit.text()
        export_node = self._get_or_create_export_node()
        export_node.save_root_data("file_path", path)

    def set_fbx_file(self):
        path = self.file_name_lineedit.text()
        export_node = self._get_or_create_export_node()
        export_node.save_root_data("file_name", path)

    def set_fbx_directory(self):
        path = self.file_path_lineedit.text()
        export_node = self._get_or_create_export_node()
        export_node.save_root_data("file_path", path)

    def set_fbx_file(self):
        path = self.file_name_lineedit.text()
        export_node = self._get_or_create_export_node()
        export_node.save_root_data("file_name", path)

    def export_animation_clips(self):

        # Check if UE import is enabled, and if a skeleton is selected.
        # - If no skeleton is selected, fail.
        if (
            self.ue_import_cbx.isChecked()
            and len(self.ue_skeleton_listwgt.selectedItems()) == 0
        ):
            cmds.warning(
                "Please select a skeleton, when importing into Unreal."
            )
            cmds.confirmDialog(
                title="Export Failed",
                message="Please select a skeleton, when importing into Unreal.",
                messageAlign="center",
                button=["Okay"],
                cancelButton="Okay",
                dismissString="Okay",
            )
            return False

        print("----- Exporting Animation Clips -----")
        export_node = self._get_or_create_export_node()

        joint_root = self.get_root_joint()
        if not joint_root:
            cmds.warning("No Joint Root defined!")
            return False
        print("\t>>> Joint Root: {}".format(joint_root))

        self._auto_set_file_path()
        file_path = self.file_path_lineedit.text()
        file_name = self.file_name_lineedit.text()
        if not (file_path and file_name):
            cmds.warning("Not valid file path and name defined!")
            return False

        preset_file_path = self._get_preset_file_path()
        print("\t>>> Preset File Path: {}".format(preset_file_path))

        export_config = self._get_current_tool_data()
        anim_clip_data = export_node.get_animation_clips(joint_root)

        # Stores the selected objects, before performing the export.
        # These objects will be selected again, upon completion of
        # exporting.
        original_selection = cmds.ls(selection=True)

        # Save a temporary scene, perform all formatting to that scene,
        # then load the original scene after exporting fbx's
        file_path = export_config.get("file_path", "")
        if file_path == "":
            print("Error no file path specified")
            return False
        os.makedirs(file_path, exist_ok=True)

        # Stash temporary file path
        # Save new temporary scene
        # Alter data in temporary scene
        _scene_path = utils.get_scene_path()
        _temporary_ma_path = os.path.join(file_path, "temporary_anim_export.ma")
        cmds.file(rename=_temporary_ma_path)
        cmds.file(save=True, type="mayaAscii", force=True)

        if self.get_remove_namespace():
            print("Removing all namespaces..")
            utils.clean_namespaces(export_config)
            print("  [Namespace] Complete")

        # if self.get_scene_clean():
        #     print("Cleaning Scene..")
        #     # Performs the same code that "Delete Rig + Keep Joints" does
        #     gtDisc.disconnect_joints()
        #     for rig_root in gtDisc.get_rig_root_from_set():
        #         jnt_org = rig_root.jnt_vis.listConnections(type="transform")[0]
        #         joints = jnt_org.getChildren()
        #         if joints:
        #             pm.parent(joints, world=True)
        #         pm.delete(rig_root.rigGroups.listConnections(type="objectSet"))
        #         pm.delete(pm.ls(type="mgear_matrixConstraint"))
        #         pm.delete(rig_root)
        #     print("  [Clean Scene] Complete")

        # Parent skeleton root directly to world
        root_joint = export_config.get("joint_root", "")
        cmds.parent(root_joint, world=True)

        # Store the fbx locations that were successfully exported.
        export_fbx_paths = []

        # Exports each clip
        for clip_data in anim_clip_data:

            # skip disabled clips.
            if not clip_data["enabled"]:
                continue

            result = utils.export_animation_clip(export_config, clip_data)
            if not result:
                print(
                    "\t!!! >>> Failed to export clip: {}".format(
                        clip_data["title"]
                    )
                )
            else:
                export_fbx_paths.append(result)

        # Load temporary scene after all exportation
        # Set temporary scene file path to stashed scene file path
        # Clean up temporary .ma file
        cmds.file(_temporary_ma_path, open=True, force=True, save=False)
        cmds.file(rename=_scene_path)
        cmds.file(modified=False)
        os.remove(_temporary_ma_path)

        if original_selection:
            pm.select(original_selection)

        # Unreal Import, if enabled.
        if self.ue_import_cbx.isChecked():
            skeleton_path = self.ue_skeleton_listwgt.selectedItems()[0].text()
            unreal_folder = self.ue_file_path_lineedit.text()

            for path in export_fbx_paths:
                name = os.path.basename(path)
                animation_name = ".".join(name.split(".")[:-1])
                result = uegear.export_animation_to_unreal(
                    path, unreal_folder, animation_name, skeleton_path
                )
        return True

    # helper methods
    def _get_or_create_export_node(self):
        """
        Gets the Maya fbx export node, that contains all the ui data.
        """
        return (
            fbx_export_node.FbxExportNode.get()
            or fbx_export_node.FbxExportNode.create()
        )

    def _save_data_to_export_node(self, data=None):
        export_node = self._get_or_create_export_node()
        export_data = data if data else export_node.parse_export_data()
        current_data = self._get_current_tool_data()
        export_data.update(current_data)
        export_node.save_data(export_data)
        return export_data

    def _load_node_data_to_widget(self):
        export_node = self._get_or_create_export_node()
        node_data = export_node.parse_export_data()
        self._set_tool_data(node_data)

    def _get_listwidget_item_names(self, listwidget):
        return [listwidget.item(i).text() for i in range(listwidget.count())]

    def _get_preset_file_path(self):
        preset_file_path = ""
        current_export_preset = self.fbx_export_presets_combobox.currentText()
        if current_export_preset and current_export_preset != "User defined":
            preset_file_path = self.fbx_export_presets_combobox.itemData(
                self.fbx_export_presets_combobox.currentIndex()
            )
        return preset_file_path

    def _get_current_tool_data(self):
        current_data = {
            "geo_roots": self._get_listwidget_item_names(self.geo_root_list),
            "joint_root": self.joint_root_lineedit.text(),
            "up_axis": self.up_axis_combobox.currentText(),
            "file_type": self.file_type_combobox.currentText(),
            "fbx_version": self.fbx_version_combobox.currentText(),
            "remove_namespace": self.remove_namespace_checkbox.isChecked(),
            "scene_clean": self.clean_scene_checkbox.isChecked(),
            "file_path": self.file_path_lineedit.text(),
            "file_name": self.file_name_lineedit.text(),
            "skinning": self.skinning_checkbox.isChecked(),
            "blendshapes": self.blendshapes_checkbox.isChecked(),
            "use_partitions": self.partitions_checkbox.isChecked(),
            "export_tab": self.export_tab.currentIndex(),
            "ue_enabled": self.ue_import_cbx.isChecked(),
            "ue_file_path": self.ue_file_path_lineedit.text(),
            "ue_active_skeleton": "",
            "cull_joints": self.culljoints_checkbox.isChecked(),
        }

        # converting qt list widget data to text
        selected_skeleton = self.ue_skeleton_listwgt.selectedItems()
        if len(selected_skeleton) > 0:
            current_data["ue_active_skeleton"] = selected_skeleton[0].text()

        return current_data

    def _set_tool_data(self, data, reset=False):
        if reset:
            data = {}
        self.geo_root_list.clear()
        self.geo_root_list.addItems(data.get("geo_roots", []))
        self.joint_root_lineedit.setText(data.get("joint_root", ""))
        self.up_axis_combobox.setCurrentText(data.get("up_axis", "Y"))
        self.file_type_combobox.setCurrentText(data.get("file_type", "Binary"))
        self.fbx_version_combobox.setCurrentText(
            data.get("fbx_version", "FBX 2020")
        )
        self.remove_namespace_checkbox.setChecked(
            data.get("remove_namespace", False)
        )
        self.clean_scene_checkbox.setChecked(data.get("scene_clean", False))
        self.file_path_lineedit.setText(data.get("file_path", ""))
        self.file_name_lineedit.setText(data.get("file_name", ""))
        self.skinning_checkbox.setChecked(data.get("skinning", False))
        self.blendshapes_checkbox.setChecked(data.get("blendshapes", False))
        self.partitions_checkbox.setChecked(data.get("use_partitions", False))
        self.export_tab.setCurrentIndex(data.get("export_tab", 0))
        self.culljoints_checkbox.setChecked(data.get("cull_joints", False))

        self.ue_import_cbx.setChecked(data.get("ue_enabled", False))
        self.ue_file_path_lineedit.setText(data.get("ue_file_path", ""))
        # Update Skeleton selection if it exists
        if data.get("ue_active_skeleton", None):
            active_skeleton = data["ue_active_skeleton"]
            for i in range(self.ue_skeleton_listwgt.count()):
                item = self.ue_skeleton_listwgt.item(i)
                if item.text() == active_skeleton:
                    item.setSelected(True)
                else:
                    item.setSelected(False)
        else:
            self.ue_skeleton_listwgt.clearSelection()

        self.partitions_outliner.reset_contents()
        self.anim_clips_listwidget.refresh()

        # Force the population of the Master partitions.
        item_names = self._get_listwidget_item_names(self.geo_root_list)
        self.partitions_outliner.set_geo_roots(item_names)

    def _update_geo_roots_data(self):
        export_node = self._get_or_create_export_node()
        item_names = self._get_listwidget_item_names(self.geo_root_list)
        export_node.save_root_data("geo_roots", item_names)
        self.partitions_outliner.set_geo_roots(item_names)

    def _update_joint_root_data(self):
        export_node = self._get_or_create_export_node()
        joint_name = self.joint_root_lineedit.text()
        export_node.save_root_data("joint_root", joint_name)
        self.anim_clips_listwidget.refresh()

    def _auto_set_geo_roots(self, clear=False):
        geo_roots = []
        if clear:
            self.geo_root_list.clear()
        if not self.geo_root_list.count():
            geo_roots.append(utils.get_geo_root())
        self.geo_root_list.addItems(geo_roots)
        self._update_geo_roots_data()

    def _auto_set_joint_root(self):
        joint_roots = utils.get_joint_root()
        joint_name = joint_roots[0].name() if joint_roots else ""
        self.joint_root_lineedit.setText(joint_name)
        self._update_joint_root_data()

    def _auto_set_file_path(self):
        if self.file_path_lineedit.text() or self.file_name_lineedit.text():
            return
        file_path = pm.fileDialog2(fileMode=0, fileFilter="FBX(*.fbx)")
        if not file_path:
            return
        file_path = file_path[0]
        dir_name = os.path.dirname(file_path)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        self.file_path_lineedit.setText(string.normalize_path(dir_name))
        self.file_name_lineedit.setText(file_name)

    def _filter_selection_by_type(self, type_filter=None):
        """Return the element names if match the correct type

        Args:
            type_filter (str, optional): Type to filter: for example "joint"
                                         or "transform"

        Returns:
            list[str]: list of filtered node names.

        """
        filter_sel = []
        sel = pm.selected()
        if not sel:
            pm.displayWarning("Nothing selected")
            return filter_sel

        for node in sel:
            if type_filter:
                sel_type = sel[0].type()
                if type_filter != sel_type:
                    pm.displayWarning(
                        "Selected element is not of type: {}".format(
                            type_filter
                        )
                    )
                    continue
            filter_sel.append(node.name())

        return filter_sel

    def _add_list_items_from_sel(self, listwidget, type_filter, clear=False):
        """Adds list widget items from selected element filtered by type

        Args:
            listwidget (QListWidget): QT list widget object
            type_filter (str): Type to filter: for example "joint"
                               or "transform"
        """
        if clear:
            listwidget.clear()
        item_names = self._get_listwidget_item_names(listwidget)
        node_names = self._filter_selection_by_type(type_filter)
        for node_name in node_names:
            if not clear and node_name in item_names:
                continue
            listwidget.addItem(node_name)
        if listwidget == self.geo_root_list:
            self._update_geo_roots_data()

    def _remove_list_items_from_sel(self, listwidget):
        """Removes list widget items from selected list items

        Args:
            listwidget (QListWidget): QT list widget object
        """
        selected_items = listwidget.selectedItems()
        for selected_item in selected_items:
            listwidget.takeItem(listwidget.row(selected_item))
        if listwidget == self.geo_root_list:
            self._update_geo_roots_data()

    def _set_lineedit_text_from_sel(self, lineedit, type_filter):
        """Set line edit text from selected element filtered by type

        Args:
            lineedit (QLineEdit): QT line edit object
            type_filter (str): Type to filter: for example "joint"
                               or "transform"
        """
        text = self._filter_selection_by_type(type_filter)
        text = text[0] if text else ""
        lineedit.setText(text)
        if type_filter == "joint":
            self._update_joint_root_data()


def openFBXExporter(*args):
    return pyqt.showDialog(FBXExporter, dockable=True)


if __name__ == "__main__":
    from mgear.shifter.game_tools_fbx import widgets

    import sys

    if sys.version_info[0] == 2:
        reload(widgets)
    else:
        importlib.reload(widgets)

    start = timeit.default_timer()
    openFBXExporter()
    end = timeit.default_timer()
    timeConsumed = end - start
    print("{} time elapsed running".format(timeConsumed))
