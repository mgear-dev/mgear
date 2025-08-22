from functools import partial

import maya.cmds as cmds

from mgear.vendor.Qt import QtWidgets, QtCore, QtGui

from mgear.core import pyqt, utils as coreUtils, animLayers
from mgear.shifter.game_tools_fbx import fbx_export_node, utils


class AnimClipsListWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(AnimClipsListWidget, self).__init__(parent=parent)
        self._fbx_exporter = parent
        self._root_joint = None
        self._export_path = None
        self._file_name = None

        self.create_layout()
        self.create_connections()

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        anim_clip_options_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(anim_clip_options_layout)

        self._add_anim_clip_button = QtWidgets.QPushButton("Add Clip")
        anim_clip_options_layout.addWidget(self._add_anim_clip_button)

        self._delete_all_clips_button = QtWidgets.QPushButton(
            "Delete All Clips"
        )
        anim_clip_options_layout.addWidget(self._delete_all_clips_button)
        anim_clip_options_layout.addStretch()

        self._anim_clips_checkbox = QtWidgets.QCheckBox()
        self._anim_clips_checkbox.setChecked(True)
        anim_clip_options_layout.addWidget(self._anim_clips_checkbox)

        anim_clip_area = QtWidgets.QScrollArea()
        anim_clip_area.setWidgetResizable(True)
        anim_clip_content = QtWidgets.QWidget()
        anim_clip_area.setWidget(anim_clip_content)
        main_layout.addWidget(anim_clip_area)

        anim_clips_main_layout = QtWidgets.QVBoxLayout()
        anim_clips_main_layout.setSpacing(0)
        anim_clips_main_layout.setContentsMargins(0, 0, 0, 0)
        anim_clip_content.setLayout(anim_clips_main_layout)

        self._clips_layout = QtWidgets.QVBoxLayout()
        self._clips_layout.setSpacing(0)
        self._clips_layout.setContentsMargins(0, 0, 0, 0)
        anim_clips_main_layout.addLayout(self._clips_layout)
        anim_clips_main_layout.addStretch()

    def create_connections(self):
        self._anim_clips_checkbox.toggled.connect(
            self._on_toggled_anim_clips_checkbox
        )
        self._add_anim_clip_button.clicked.connect(
            self._on_add_animation_clip_button_clicked
        )
        self._delete_all_clips_button.clicked.connect(
            self._on_delete_all_animation_clips_button_clicked
        )

    def refresh(self):
        pyqt.clear_layout(self._clips_layout)

        if not self._fbx_exporter:
            return
        self._root_joint = self._fbx_exporter.get_root_joint()
        self._export_path = self._fbx_exporter.get_export_path()
        self._file_name = self._fbx_exporter.get_file_name()

        if not self._root_joint:
            return
        export_node = fbx_export_node.FbxExportNode.get()
        if not export_node:
            return

        for anim_clip_data in export_node.get_animation_clips(
            self._root_joint
        ):
            anim_clip_name = anim_clip_data.get("title", None)
            if not anim_clip_name:
                continue
            self._add_animation_clip(anim_clip_name)

    def _add_animation_clip(self, clip_name):
        # TODO: Add code to avoid adding anim clips with duplicated names

        anim_clip_widget = AnimClipWidget(clip_name, parent=self._fbx_exporter)
        self._clips_layout.addWidget(anim_clip_widget)
        return anim_clip_widget

    def _on_toggled_anim_clips_checkbox(self, flag):
        for i in range(self._clips_layout.count()):
            anim_clip_widget = self._clips_layout.itemAt(i).widget()
            anim_clip_widget.set_enabled(flag)

    def _on_add_animation_clip_button_clicked(self):
        if not self._root_joint:
            cmds.warning(
                "Could not add animation clip because no root joint is defined!"
            )
            return

        export_node = fbx_export_node.FbxExportNode.get()
        anim_clip_name = export_node.add_animation_clip(self._root_joint)
        if not anim_clip_name:
            cmds.warning("Was not possible to add new animation clip")
            return

        self._add_animation_clip(anim_clip_name)

    def _on_delete_all_animation_clips_button_clicked(self):
        if not self._root_joint:
            return

        export_node = fbx_export_node.FbxExportNode.get()
        if not export_node:
            return

        export_node.delete_all_animation_clips()

        self.refresh()


class AnimClipWidget(QtWidgets.QFrame):
    def __init__(self, clip_name=None, parent=None):
        super(AnimClipWidget, self).__init__(parent)
        self._fbx_exporter = parent
        self._clip_name = clip_name
        self._previous_name = clip_name

        self.window().setAttribute(QtCore.Qt.WA_AlwaysShowToolTips, True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setFixedHeight(45)

        self.create_layout()
        self.create_connections()
        self.refresh()

    def create_layout(self):
        def set_transparent_button(button):
            button.setStyleSheet(
                "QPushButton {background:transparent;border:0px;}"
            )
            return button

        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        clip_name_layout = QtWidgets.QHBoxLayout()
        clip_name_layout.setSpacing(1)
        clip_name_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(clip_name_layout)

        self._delete_button = QtWidgets.QPushButton()
        self._delete_button.setIcon(pyqt.get_icon("mgear_trash"))
        self._delete_button.setStatusTip("Delete Clip")
        self._delete_button.setMaximumSize(25, 25)
        set_transparent_button(self._delete_button)
        clip_name_layout.addWidget(self._delete_button)

        self._clip_name_lineedit = QtWidgets.QLineEdit()
        self._clip_name_lineedit.setStatusTip("Clip Name")
        clip_name_layout.addWidget(self._clip_name_lineedit)

        self._anim_layer_combo = AnimationLayerCB()
        self._anim_layer_combo.setStatusTip("Animation Layer")
        clip_name_layout.addWidget(self._anim_layer_combo)

        self._start_frame_box = QtWidgets.QLineEdit()
        self._start_frame_box.setValidator(QtGui.QIntValidator())
        self._start_frame_box.setStatusTip("Start Frame")
        self._start_frame_box.setFixedSize(40, 20)
        clip_name_layout.addWidget(self._start_frame_box)

        self._end_frame_box = QtWidgets.QLineEdit()
        self._end_frame_box.setValidator(QtGui.QIntValidator())
        self._end_frame_box.setStatusTip("End Frame")
        self._end_frame_box.setFixedSize(40, 20)
        clip_name_layout.addWidget(self._end_frame_box)

        self._set_range_button = QtWidgets.QPushButton()
        self._set_range_button.setIcon(pyqt.get_icon("mgear_film"))
        self._set_range_button.setStatusTip("Set Frame Range")
        self._set_range_button.setMaximumSize(25, 25)
        set_transparent_button(self._set_range_button)
        clip_name_layout.addWidget(self._set_range_button)

        self._play_button = QtWidgets.QPushButton()
        self._play_button.setIcon(pyqt.get_icon("mgear_play"))
        self._play_button.setStatusTip("Play Sequence")
        self._play_button.setMaximumSize(25, 25)
        set_transparent_button(self._play_button)
        clip_name_layout.addWidget(self._play_button)

        self._export_checkbox = QtWidgets.QCheckBox()
        self._export_checkbox.setChecked(True)
        self._export_checkbox.setStatusTip("Export Clip")
        clip_name_layout.addWidget(self._export_checkbox)

    def create_connections(self):
        self._export_checkbox.toggled.connect(self._on_update_anim_clip)
        self._clip_name_lineedit.textChanged.connect(self._on_update_anim_clip)
        self._delete_button.clicked.connect(self._on_delete_button_clicked)
        self._start_frame_box.textChanged.connect(self._on_update_anim_clip)
        self._end_frame_box.textChanged.connect(self._on_update_anim_clip)
        self._set_range_button.clicked.connect(
            self._on_set_range_button_clicked
        )
        self._anim_layer_combo.currentIndexChanged.connect(
            self._on_update_anim_clip
        )
        self._play_button.clicked.connect(self._on_play_button_clicked)
        self.customContextMenuRequested.connect(
            self._on_custom_context_menu_requested
        )

    def refresh(self):
        export_node = fbx_export_node.FbxExportNode.get()
        if not (export_node and self._fbx_exporter):
            self._clear()
            return

        root_joint = self._fbx_exporter.get_root_joint()
        anim_clip_data = export_node.find_animation_clip(
            root_joint, self._clip_name
        )

        with pyqt.block_signals(self._clip_name_lineedit):
            self._clip_name_lineedit.setText(
                anim_clip_data.get("title", "Untitled")
            )
        with pyqt.block_signals(self._start_frame_box):
            self._start_frame_box.setText(
                str(anim_clip_data.get("start_frame", ""))
            )
        with pyqt.block_signals(self._end_frame_box):
            self._end_frame_box.setText(
                str(anim_clip_data.get("end_frame", ""))
            )
        with pyqt.block_signals(self._export_checkbox):
            self._export_checkbox.setChecked(
                anim_clip_data.get("enabled", True)
            )
        with pyqt.block_signals(self._anim_layer_combo):
            self._anim_layer_combo.clear()
            # TODO: Maybe we should filter display layers that are set with override mode?
            anim_layers = animLayers.all_anim_layers_ordered()
            self._anim_layer_combo.addItems(["None"] + anim_layers)
            serialised_anim_layer = anim_clip_data.get("anim_layer", "None")

            if not serialised_anim_layer:
                serialised_anim_layer = "None"

            # If serialised animation layer does not exist, notify user.
            if self._anim_layer_combo.findText(serialised_anim_layer) > -1:
                self._anim_layer_combo.setCurrentText(serialised_anim_layer)
            else:
                cmds.warning(
                    "Animation Layer not found: {}".format(
                        serialised_anim_layer
                    )
                )

    def set_enabled(self, flag):
        self._export_checkbox.setChecked(flag)

    def _clear(self):
        self._clip_name_lineedit.setText("Untitled")
        self._start_frame_box.setText("")
        self._end_frame_box.setText("")
        self._export_checkbox.setChecked(False)

    def _on_delete_button_clicked(self):
        export_node = fbx_export_node.FbxExportNode.get()
        if not export_node:
            return

        root_joint = self._fbx_exporter.get_root_joint()
        if not root_joint:
            return

        export_node.delete_animation_clip(root_joint, self._clip_name)
        self.setParent(None)
        self.deleteLater()

    def _on_update_anim_clip(self):
        root_joint = self._fbx_exporter.get_root_joint()
        if not root_joint:
            return

        export_node = fbx_export_node.FbxExportNode.get()
        if not export_node:
            return

        anim_clip_data = fbx_export_node.FbxExportNode.ANIM_CLIP_DATA.copy()
        anim_clip_data["title"] = self._clip_name_lineedit.text()
        anim_clip_data["enabled"] = self._export_checkbox.isChecked()
        anim_clip_data["frame_rate"] = coreUtils.get_frame_rate()
        anim_clip_data["start_frame"] = int(self._start_frame_box.text())
        anim_clip_data["end_frame"] = int(self._end_frame_box.text())
        anim_layer = self._anim_layer_combo.currentText()
        anim_clip_data["anim_layer"] = (
            anim_layer if anim_layer and anim_layer != "None" else ""
        )

        export_node.update_animation_clip(
            root_joint, self._previous_name, anim_clip_data
        )
        self._previous_name = anim_clip_data["title"]

    def _on_delete_anim_clip(self):
        export_node = fbx_export_node.FbxExportNode.get()
        if not export_node:
            return

        root_joint = self._fbx_exporter.get_root_joint()
        if not root_joint:
            return

        result = export_node.delete_animation_clip(root_joint, self._clip_name)
        if not result:
            return

        self.setParent(None)
        self.deleteLater()

    def _on_set_range_button_clicked(self):
        min_frame = str(int(cmds.playbackOptions(query=True, min=True)))
        max_frame = str(int(cmds.playbackOptions(query=True, max=True)))
        self._start_frame_box.setText(min_frame)
        self._end_frame_box.setText(max_frame)

    def _on_play_button_clicked(self):
        start_time = str(int(cmds.playbackOptions(query=True, min=True)))
        end_time = str(int(cmds.playbackOptions(query=True, max=True)))
        anim_start_time = str(int(cmds.playbackOptions(query=True, ast=True)))
        anim_end_time = str(int(cmds.playbackOptions(query=True, aet=True)))
        start_frame = self._start_frame_box.text()
        end_frame = self._end_frame_box.text()

        if not (start_frame == start_time and end_frame == end_time) or not (
            start_frame == anim_start_time and end_frame == anim_end_time
        ):
            cmds.playbackOptions(
                animationStartTime=start_frame,
                minTime=start_frame,
                animationEndTime=end_frame,
                maxTime=end_frame,
            )
        elif cmds.play(query=True, state=True):
            cmds.play(state=False)
        else:
            cmds.play(forward=True)

    def _on_custom_context_menu_requested(self, pos):
        context_menu = QtWidgets.QMenu(parent=self)
        delete_anim_clip_action = context_menu.addAction("Delete")
        playblast_menu = QtWidgets.QMenu("Playblast", parent=self)
        playblast_25_action = playblast_menu.addAction("25%")
        playblast_50_action = playblast_menu.addAction("50%")
        playblast_75_action = playblast_menu.addAction("75%")
        playblast_100_action = playblast_menu.addAction("100%")
        playblast_menu.addSeparator()
        open_playblasts_folder_action = playblast_menu.addAction(
            "Open in Explorer"
        )

        context_menu.addAction(delete_anim_clip_action)
        context_menu.addMenu(playblast_menu)

        delete_anim_clip_action.triggered.connect(self._on_delete_anim_clip)
        playblast_25_action.triggered.connect(
            partial(utils.create_mgear_playblast, scale=25)
        )
        playblast_50_action.triggered.connect(
            partial(utils.create_mgear_playblast, scale=50)
        )
        playblast_75_action.triggered.connect(
            partial(utils.create_mgear_playblast, scale=75)
        )
        playblast_100_action.triggered.connect(
            partial(utils.create_mgear_playblast, scale=100)
        )
        open_playblasts_folder_action.triggered.connect(
            utils.open_mgear_playblast_folder
        )
        context_menu.exec_(self.mapToGlobal(pos))


class AnimationLayerCB(QtWidgets.QComboBox):
    """
    Custom overloaded QComboBox, this will automatically refresh the combobox everytime
    it shows the values. Keep the Combobox up to date with the AnimationLayers available.
    """

    def __init__(self, parent=None):
        super(AnimationLayerCB, self).__init__(parent=parent)

    def showPopup(self):
        super(AnimationLayerCB, self).showPopup()
        currentText = self.currentText()

        self.clear()

        anim_layers = animLayers.all_anim_layers_ordered()
        self.addItems(["None"] + anim_layers)

        self.setCurrentText(currentText)

        # TODO: Could to a check here to see if the layer still exists, else add a warning.
