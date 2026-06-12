from mgear.core import pyqt
from mgear.core import widgets as mgear_widget
from mgear.core import widgets as mwgt
from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from functools import partial
import os
import glob
from mgear.core.utils import one_undo

import maya.cmds as cmds

from . import setup


class SpringManager(MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin):
    """
    UI to collect configuration data for a node in Maya.
    """

    def __init__(self, parent=None):
        super(SpringManager, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.setWindowTitle("Spring Manager")
        min_w = 425
        min_h = 125
        self.setMinimumWidth(min_w)
        self.resize(min_w, min_h)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )

        if cmds.about(ntOS=True):
            flags = self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
            self.setWindowFlags(flags)
        elif cmds.about(macOS=True):
            self.setWindowFlags(QtCore.Qt.Tool)

        self.settings = QtCore.QSettings("MGear", "SpringManager")

        self.create_actions()
        self.create_widgets()
        self.create_layout()
        self.create_connections()

        self.configs = []

    def create_actions(self):
        # Bake actions
        self.bake_selected_action = QtWidgets.QAction("Bake Selected Spring", self)
        self.bake_all_action = QtWidgets.QAction("Bake All Springs", self)

        # Delete actions
        self.delete_selected_action = QtWidgets.QAction("Delete Selected Spring", self)
        self.delete_all_action = QtWidgets.QAction("Delete All Springs", self)

        # preset actions
        self.set_lib_action = QtWidgets.QAction("Set Library", self)
        self.store_preset_action = QtWidgets.QAction("Store Preset", self)
        self.refresh_presets_action = QtWidgets.QAction("Refresh Presets", self)
        self.delete_preset_action = QtWidgets.QAction("Delete Preset", self)
        # Select actions
        self.select_all_targets_action = QtWidgets.QAction("Select All Spring Targets", self)

    def create_widgets(self):
        # menu bar
        self.menu_bar = QtWidgets.QMenuBar()

        self.bake_menu = self.menu_bar.addMenu("Bake")
        self.bake_menu.addAction(self.bake_selected_action)
        self.bake_menu.addAction(self.bake_all_action)

        self.delete_menu = self.menu_bar.addMenu("Delete")
        self.delete_menu.addAction(self.delete_selected_action)
        self.delete_menu.addAction(self.delete_all_action)

        self.presets_menu = self.menu_bar.addMenu("Presets")
        self.presets_menu.addAction(self.set_lib_action)
        self.presets_menu.addAction(self.store_preset_action)
        self.presets_menu.addAction(self.refresh_presets_action)
        self.presets_menu.addAction(self.delete_preset_action)

        self.select_menu = self.menu_bar.addMenu("Select")
        self.select_menu.addAction(self.select_all_targets_action)

        # directions
        self.directions_group_box = QtWidgets.QGroupBox("Directions")

        self.directions = ["x", "y", "z", "-x", "-y", "-z"]
        self.direction_buttons = {}
        for direction in self.directions:
            btn = QtWidgets.QPushButton(direction)
            self.direction_buttons[direction] = btn

        # config sliders
        self.spin_sliders = {}
        self.collapsible_spring_params = mgear_widget.CollapsibleWidget(
            "Spring Parameters", expanded=False
        )

        options = [
            ("Total Intensity", "springTotalIntensity", 1),
            ("Spring Rig Scale", "springRigScale", 1),
            ("Translational Intensity", "springTranslationalIntensity", 0),
            ("Translational Damping", "springTranslationalDamping", 0.5),
            ("Translational Stiffness", "springTranslationalStiffness", 0.5,),
            ("Rotational Intensity", "springRotationalIntensity", 1),
            ("Rotational Damping", "springRotationalDamping", 0.5),
            ("Rotational Stiffness", "springRotationalStiffness", 0.5),
        ]
        self.spring_options_layout = QtWidgets.QFormLayout()
        self.spring_options_layout.setSizeConstraint(QtWidgets.QLayout.SetMaximumSize)

        for label_text, name, default_value in options:
            if name == "springRigScale":
                spin_range = 100
                slider_range = 10000
            else:
                spin_range = 1
                slider_range = 100
            spin = QtWidgets.QDoubleSpinBox()
            spin.setMinimumWidth(50)
            spin.setRange(0, spin_range)
            spin.setSingleStep(0.1)
            spin.setValue(default_value)
            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(0, slider_range)
            slider.setValue(default_value * 100)

            self.spring_options_layout.addRow(label_text, spin)
            self.spring_options_layout.addRow("", slider)

            self.spin_sliders[name] = (spin, slider)

        # presets
        self.presets_collapsible = mgear_widget.CollapsibleWidget(
            "Presets", expanded=False
        )

        self.presets_library_directory = self._get_presets_library_directory()
        self.presets_lib_directory_label = QtWidgets.QLabel("Library Path: {}".format(self.presets_library_directory))
        self.presets_lib_directory_label.setWordWrap(True)

        self.search_le = QtWidgets.QLineEdit()
        self.search_le.setPlaceholderText("Search Filter")

        self.list_view = QtWidgets.QListView()
        self.list_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.list_view.setSelectionMode(QtWidgets.QListView.ExtendedSelection)
        self.item_model = QtGui.QStandardItemModel(self)
        self.__proxy_model = QtCore.QSortFilterProxyModel(self)
        self.__proxy_model.setSourceModel(self.item_model)
        self.list_view.setModel(self.__proxy_model)



        self.set_library(self.presets_library_directory)

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)
        main_layout.setMenuBar(self.menu_bar)

        directions_grid_layout = QtWidgets.QGridLayout()
        for i, direction in enumerate(self.directions):
            directions_grid_layout.addWidget(self.direction_buttons[direction], i // 3, i % 3)

        self.directions_group_box.setLayout(directions_grid_layout)
        main_layout.addWidget(self.directions_group_box)

        self.collapsible_spring_params.addLayout(self.spring_options_layout)
        main_layout.addWidget(self.collapsible_spring_params)

        presets_layout = QtWidgets.QVBoxLayout()
        presets_layout.addWidget(self.presets_lib_directory_label)
        presets_layout.addWidget(self.search_le)
        presets_layout.addWidget(self.list_view)
        self.presets_collapsible.addLayout(presets_layout)

        main_layout.addWidget(self.presets_collapsible)

        expander = QtWidgets.QWidget()
        expander.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        main_layout.addWidget(expander)

    def create_connections(self):
        self.bake_selected_action.triggered.connect(setup.bake)
        self.bake_all_action.triggered.connect(setup.bake_all)

        self.delete_selected_action.triggered.connect(partial(setup.delete_spring_setup, None, True))
        self.delete_all_action.triggered.connect(setup.delete_all_springs)
        self.select_all_targets_action.triggered.connect(setup.select_all_springs_targets)

        self.set_lib_action.triggered.connect(partial(self.set_library, None))
        self.store_preset_action.triggered.connect(self.store_preset)
        self.refresh_presets_action.triggered.connect(self.update_presets)
        self.delete_preset_action.triggered.connect(self.delete_preset)

        self.search_le.textChanged.connect(self.filter_changed)
        self.list_view.doubleClicked.connect(self.apply_preset)
        self.list_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._component_menu)


        for btn in self.direction_buttons.values():
            btn.clicked.connect(self.collect_data)

        for spin, slider in self.spin_sliders.values():
            spin.valueChanged.connect(
                lambda value, slider=slider: slider.setValue(int(value * 100))
            )
            slider.valueChanged.connect(
                lambda value, spin=spin: spin.setValue(value * 0.01)
            )


    def set_node_from_selection(self):
        """
        Set node name from current Maya selection.
        """
        selected = pm.selected()
        self.node_le.setText(",".join([str(node) for node in selected]))

    def collect_data(self):
        """
        Collects all data into a list of config dictionaries.
        """
        self.configs = []
        # nodes = self.node_le.text().split(",")
        nodes = pm.selected()
        direction = self.sender().text()  # Assumes button clicked

        for node in nodes:
            config = {"node": node.name(), "direction": direction}
            for name, (spin, _) in self.spin_sliders.items():
                config[name] = spin.value()

            self.configs.append(config)
        for conf in self.configs:
            setup.create_spring(conf["node"], conf)

    def get_presets(self, directory):
        """
        Get a list of preset filenames in a directory, filtering by extension and file size.

        Args:
            directory (str): The path to the directory containing the presets.
            extension (str): The file extension to filter by.

        Returns:
            list: A list of preset filenames without extensions.
        """
        preset_paths = glob.glob(os.path.join(directory, "*{}".format(setup.SPRING_PRESET_EXTENSION)))
        presets = [
            os.path.splitext(os.path.basename(f))[0]
            for f in preset_paths
            if os.stat(f).st_size > 0
        ]
        return presets

    def read_preset_from_directory(self, directory):
        """
        Parses target directory and gets the files names
        Args:
            directory:

        Returns: (file_name)

        """
        presets = self.get_presets(directory)

        return tuple(presets)

    def set_library(self, directory=None):
        """
        Clears the preset list and populates a new one with the items of the given directory
        Args:
            directory:

        Returns:

        """
        if not directory:
            directory = pm.fileDialog2(fileMode=3)[0]

        try:
            if not os.path.isdir(directory):
                print("Directory does not exist. Creating...")
                os.makedirs(directory, exist_ok=True)

        except:
            pm.error("Could not create directory")
            return

        if not os.path.isdir(directory):
            pm.error("Invalid directory")
            return

        self.presets_library_directory = directory
        self.settings.setValue("presetsLibraryDirectory", directory)
        self.presets_lib_directory_label.setText("Library Path: {}".format(self.presets_library_directory))

        self.update_presets()

    def update_presets(self):
        self.item_model.clear()
        presets = self.read_preset_from_directory(self.presets_library_directory)
        for preset in presets:
            item = QtGui.QStandardItem(preset)
            file_path = "{}/{}{}".format(self.presets_library_directory, preset, setup.SPRING_PRESET_EXTENSION)
            target_nodes = setup.get_preset_targets(preset_file_path=file_path)
            tooltip_text = "Target nodes = " + ", ".join(target_nodes)
            item.setData(tooltip_text, QtCore.Qt.ToolTipRole)
            self.item_model.appendRow(item)

    def store_preset(self):
        file_name, dialog_result = QtWidgets.QInputDialog.getText(self, "Enter Preset Name", "Name:")
        if not dialog_result:
            return
        file_name = "/{}{}".format(file_name, setup.SPRING_PRESET_EXTENSION)
        setup.store_preset_from_selection(self.presets_library_directory + file_name)

        self.update_presets()

    @one_undo
    def apply_preset(self, clicked_item):
        """
        Applies preset to selected nodes
        Args:
            clicked_item:

        Returns:

        """
        item = self.item_model.itemFromIndex(self.__proxy_model.mapToSource(clicked_item))
        name = item.text()
        file_path = "{}/{}{}".format(self.presets_library_directory, name, setup.SPRING_PRESET_EXTENSION)
        affected_nodes = setup.apply_preset(preset_file_path=file_path, namespace_cb=self._namespace_confirmation_dialogue)
        print("Affected nodes = {}".format(affected_nodes))
        return affected_nodes

    def delete_preset(self):
        if not self.list_view.selectedIndexes():
            pm.error("Must select an item from the preset list")
            return

        list_selection = self.list_view.selectedIndexes()
        list_selection = [self._get_preset_name(i) for i in list_selection]

        if self._delete_confirmation_dialogue(list_selection) is False:
            return

        for item in list_selection:
            file_path = "{}/{}{}".format(self.presets_library_directory, item, setup.SPRING_PRESET_EXTENSION)
            if not os.path.exists(file_path):
                pm.error("File was not found. {}".format(file_path))
            os.remove(file_path)

        self.update_presets()

    def _component_menu(self, QPos):
        comp_widget = self.list_view
        current_selection = comp_widget.selectedIndexes()
        if current_selection is None:
            return
        self.comp_menu = QtWidgets.QMenu()
        parentPosition = comp_widget.mapToGlobal(QtCore.QPoint(0, 0))
        apply_preset_menu_item = self.comp_menu.addAction("Apply presets")
        bake_presets_menu_item = self.comp_menu.addAction("Bake presets")
        delete_presets_menu_item = self.comp_menu.addAction("Delete presets")
        self.comp_menu.addSeparator()
        select_targets_menu_item = self.comp_menu.addAction("Select targets")

        apply_preset_menu_item.triggered.connect(self.cm_apply_presets)
        bake_presets_menu_item.triggered.connect(self.cm_bake_presets)
        delete_presets_menu_item.triggered.connect(self.delete_preset)
        select_targets_menu_item.triggered.connect(self.cm_select_affected)

        self.comp_menu.move(parentPosition + QPos)
        self.comp_menu.show()

    @one_undo
    def cm_apply_presets(self):
        list_selection = self.list_view.selectedIndexes()
        for item in list_selection:
            self.apply_preset(item)

    @one_undo
    def cm_bake_presets(self):
        list_selection = self.list_view.selectedIndexes()
        nodes_to_bake = []
        for item in list_selection:
            nodes_to_bake.extend(self.apply_preset(item))

        start_time = pm.playbackOptions(query=True, minTime=True)
        end_time = pm.playbackOptions(query=True, maxTime=True)
        pm.currentTime(end_time)
        pm.currentTime(start_time)
        setup.bake(nodes_to_bake)

    @one_undo
    def cm_select_affected(self):
        list_selection = self.list_view.selectedIndexes()
        affected_nodes = []
        for qindex in list_selection:
            item = self.item_model.itemFromIndex(self.__proxy_model.mapToSource(qindex))
            name = item.text()
            file_path = "{}/{}{}".format(self.presets_library_directory, name, setup.SPRING_PRESET_EXTENSION)
            affected_nodes.extend(setup.get_preset_targets(preset_file_path=file_path, namespace_cb=self._namespace_confirmation_dialogue))
        pm.select(affected_nodes)

    def filter_changed(self, filter):
        regExp = QtCore.QRegExp(filter,
                                QtCore.Qt.CaseSensitive,
                                QtCore.QRegExp.Wildcard
                                )
        self.__proxy_model.setFilterRegExp(regExp)

    def _namespace_confirmation_dialogue(self, preset_namespace, selected_namespace):
        message_box = QtWidgets.QMessageBox()

        message_box.setWindowTitle("Namespace mismatch")
        message_box.setText("Namespace from selection does not match the namespace stored in the preset.")
        message_box.setInformativeText("Click Apply to map nodes from preset namespace '{}' ".format(preset_namespace)
                                       + "\n to selected namespace '{}'".format(selected_namespace))

        message_box.setStandardButtons(QtWidgets.QMessageBox.Apply | QtWidgets.QMessageBox.Ignore)

        return message_box.exec_() == QtWidgets.QMessageBox.Apply

    def _delete_confirmation_dialogue(self, items_to_delete):
        message_box = QtWidgets.QMessageBox()
        message_box.setWindowTitle("Confirm deletion")
        message_box.setText("Do you wish to delete the following items?")
        message_box.setInformativeText(", ".join(items_to_delete))

        message_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)

        return message_box.exec_() == QtWidgets.QMessageBox.Yes

    def _get_preset_name(self, proxy_index):
        model_item = self.item_model.itemFromIndex(self.__proxy_model.mapToSource(proxy_index))
        return model_item.text()

    def _get_presets_library_directory(self):
        value = self.settings.value("presetsLibraryDirectory")
        if value:
            return value
        else:
            value = pm.workspace(query=1, rootDirectory=True)
            value += 'data'
            return value


def openSpringManagerManager(*args):
    pyqt.showDialog(SpringManager, dockable=True)


if __name__ == "__main__":
    window = SpringManager()
    window.show()
