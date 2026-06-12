import os
import json

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mgear.vendor.Qt import QtGui, QtWidgets
from mgear.core import pyqt, widgets
from mgear.shifter.rig_builder import builder

from functools import partial
import mgear.pymaya as pm


class RigBuilderUI(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    """
    A UI class for building mGear rigs from .sgt files.
    """

    def __init__(self):
        super(RigBuilderUI, self).__init__()
        self.setWindowTitle("mGear Rig Builder")
        self.setMinimumWidth(400)
        self.setAcceptDrops(True)
        self.resize(900, 650)

        self.builder = builder.RigBuilder()
        self.create_actions()
        self.create_layout()
        self.create_connections()

    def create_actions(self):
        self.import_action = QtWidgets.QAction("Import Config")
        self.export_action = QtWidgets.QAction("Export Config")

    def create_layout(self):
        """Creates the main layout widgets of the tool."""

        self.menu_bar = QtWidgets.QMenuBar()
        self.file_menu = self.menu_bar.addMenu("File")
        self.file_menu.addAction(self.import_action)
        self.file_menu.addAction(self.export_action)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.setMenuBar(self.menu_bar)

        # Output Folder UI
        output_folder_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(output_folder_layout)

        self.output_folder_line_edit = QtWidgets.QLineEdit()
        self.output_folder_button = widgets.create_button(
            icon="mgear_folder", width=25
        )

        output_folder_layout.addWidget(QtWidgets.QLabel("Output Folder"))
        output_folder_layout.addWidget(self.output_folder_line_edit)
        output_folder_layout.addWidget(self.output_folder_button)

        # Run Validators checkboxes
        run_validators_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(run_validators_layout)

        self.run_validators_checkbox = QtWidgets.QCheckBox(
            "Run Pyblish Validators"
        )
        self.run_validators_checkbox.setChecked(True)
        run_validators_layout.addWidget(self.run_validators_checkbox)
        run_validators_layout.addStretch()

        self.results_popup_checkbox = QtWidgets.QCheckBox(
            "Open Results Pop-Up"
        )
        self.results_popup_checkbox.setChecked(True)
        run_validators_layout.addWidget(self.results_popup_checkbox)
        run_validators_layout.addStretch()

        self.publish_label = QtWidgets.QLabel("Publish Passed Rigs Only")
        self.publish_passed_checkbox = QtWidgets.QCheckBox(
            "Publish Passed Rigs Only"
        )
        run_validators_layout.addWidget(self.publish_passed_checkbox)

        if not builder.PYBLISH_READY:
            self.run_validators_checkbox.setEnabled(False)
            self.run_validators_checkbox.setChecked(False)
            self.on_run_validators_checkbox_changed()

        # File Table UI
        self.table_widget = QtWidgets.QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(
            [".sgt File", "Output Name", "Custom Output Path", " "]
        )

        self.table_widget.setEditTriggers(
            QtWidgets.QAbstractItemView.AllEditTriggers
        )
        # Resize the first column to fit its content
        self.table_widget.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents
        )
        # Make the last column stretch to fill the remaining space
        self.table_widget.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.Stretch
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeToContents
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            3, QtWidgets.QHeaderView.ResizeToContents
        )

        self.layout.addWidget(self.table_widget)

        # Pre-scrtip
        pre_script_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(pre_script_layout)

        self.pre_script_line_edit = QtWidgets.QLineEdit()
        self.pre_script_button = widgets.create_button(
            icon="mgear_folder", width=25
        )

        pre_script_layout.addWidget(QtWidgets.QLabel("Pre Script"))
        pre_script_layout.addWidget(self.pre_script_line_edit)
        pre_script_layout.addWidget(self.pre_script_button)

        # Post-scrtip
        post_script_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(post_script_layout)

        self.post_script_line_edit = QtWidgets.QLineEdit()
        self.post_script_button = widgets.create_button(
            icon="mgear_folder", width=25
        )

        post_script_layout.addWidget(QtWidgets.QLabel("Post Script"))
        post_script_layout.addWidget(self.post_script_line_edit)
        post_script_layout.addWidget(self.post_script_button)

        # Add, Remove, and Build buttons
        self.add_button = QtWidgets.QPushButton("Add")
        self.remove_button = QtWidgets.QPushButton("Remove")
        self.build_button = QtWidgets.QPushButton("Build")

        self.layout.addWidget(self.add_button)
        self.layout.addWidget(self.remove_button)
        self.layout.addWidget(self.build_button)

    def create_connections(self):
        """Connects buttons to their functions."""

        self.import_action.triggered.connect(partial(self.import_config, ""))
        self.export_action.triggered.connect(self.export_config)

        self.output_folder_button.clicked.connect(
            self.on_output_folder_clicked
        )
        self.run_validators_checkbox.toggled.connect(
            self.on_run_validators_checkbox_changed
        )
        self.add_button.clicked.connect(self.on_add_button_clicked)
        self.remove_button.clicked.connect(self.on_remove_button_clicked)
        self.build_button.clicked.connect(self.on_build_button_clicked)

        self.pre_script_button.clicked.connect(self.set_pre_script)
        self.post_script_button.clicked.connect(self.set_post_script)

    def set_script(self, lineEdit):
        """Sets the output folder for exported builds."""
        options = QtWidgets.QFileDialog.Options()
        file_filter = "Python Files (*.py)"
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Python File", "", file_filter, options=options
        )
        if file_name:
            lineEdit.setText(file_name)

    def set_pre_script(self):
        self.set_script(self.pre_script_line_edit)

    def set_post_script(self):
        self.set_script(self.post_script_line_edit)

    def on_output_folder_clicked(self):
        """Sets the output folder for exported builds."""
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Output Folder"
        )
        if folder_path:
            self.output_folder_line_edit.setText(folder_path)

    def on_run_validators_checkbox_changed(self):
        """Enables/disables options for Pyblish validators."""
        runState = self.run_validators_checkbox.isChecked()
        self.results_popup_checkbox.setEnabled(runState)
        self.publish_passed_checkbox.setEnabled(runState)

    def on_add_button_clicked(self):
        """Adds selected .sgt files from the list."""
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Select .sgt Files", "", "*.sgt"
        )
        if file_paths:
            for file_path in file_paths:
                self.add_file(file_path)

    def on_remove_button_clicked(self):
        """Removes selected .sgt files from the list."""
        selected_ranges = self.table_widget.selectedRanges()

        # Get unique rows to be removed
        rows_to_remove = set()
        for selected_range in selected_ranges:
            rows_to_remove.update(
                range(selected_range.topRow(), selected_range.bottomRow() + 1)
            )

        # Sort in reverse so that removing lower index doesn't affect higher index
        for row in sorted(rows_to_remove, reverse=True):
            self.table_widget.removeRow(row)

    def on_build_button_clicked(self):
        """Runs the rig build and validators, if specified."""
        data = self.collect_table_data()
        validate = self.run_validators_checkbox.isChecked()
        passed_rigs_only = self.publish_passed_checkbox.isChecked()
        results_dict = self.builder.execute_build_logic(
            data, validate=validate, passed_only=passed_rigs_only
        )
        if (
            self.run_validators_checkbox.isChecked()
            and self.results_popup_checkbox.isChecked()
        ):
            self.create_results_popup(results_dict)

    def collect_table_data(self):
        """Collects data from the table widget and outputs it as JSON.

        Returns:
            str: A JSON string containing the collected data
        """
        data = {}
        row_count = self.table_widget.rowCount()
        data["output_folder"] = self.output_folder_line_edit.text().strip()
        data["pre_script"] = self.pre_script_line_edit.text().strip()
        data["post_script"] = self.post_script_line_edit.text().strip()
        data["rows"] = []

        for i in range(row_count):
            file_path_item = self.table_widget.item(i, 0)
            output_name_item = self.table_widget.item(i, 1)
            custom_output_path_item = self.table_widget.item(i, 2)

            file_path = file_path_item.text().strip() if file_path_item else ""
            output_name = (
                output_name_item.text().strip() if output_name_item else ""
            )
            custom_output_path = (
                custom_output_path_item.text().strip()
                if custom_output_path_item
                else ""
            )

            data["rows"].append(
                {
                    "file_path": file_path,
                    "output_name": output_name,
                    "custom_output_path": custom_output_path,
                }
            )

        return json.dumps(data, indent=4)

    def add_file(self, file_path):
        """Adds a .sgt file to the main table.

        Args:
            file_path (str): Path of .sgt file
        """
        row_position = self.table_widget.rowCount()
        self.table_widget.insertRow(row_position)

        # For .sgt file path
        file_item = QtWidgets.QTableWidgetItem(file_path)
        self.table_widget.setItem(row_position, 0, file_item)

        # For Output Name
        output_name = os.path.splitext(os.path.basename(file_path))[0]
        output_item = QtWidgets.QTableWidgetItem(output_name)
        self.table_widget.setItem(row_position, 1, output_item)

        custom_output_path = QtWidgets.QTableWidgetItem("")
        self.table_widget.setItem(row_position, 2, custom_output_path)

        set_custom_output_bttn = widgets.create_button(
            icon="mgear_folder", setMax=False, size=37.5
        )

        self.table_widget.setCellWidget(
            row_position, 3, set_custom_output_bttn
        )
        set_custom_output_bttn.clicked.connect(
            partial(self.on_custom_path_clicked, custom_output_path)
        )

    def create_results_popup(self, results_dict):
        """Launches a pop-up containing validator results.

        Args:
            results_dict (dict): validator result data generated by RigBuilder
        """
        popup = ResultsPopupDialog(results_dict)
        popup.exec()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            file_path = str(url.toLocalFile())
            if file_path.lower().endswith(".sgt"):
                self.add_file(file_path)
            if file_path.lower().endswith(".srb"):
                self.import_config(file_path=file_path)

    def import_config(self, file_path=""):
        data = builder.RigBuilder.load_config_data_from_file(
            file_path=file_path
        )

        self.output_folder_line_edit.setText(data["output_folder"])
        self.pre_script_line_edit.setText(data["pre_script"])
        try:
            self.post_script_line_edit.setText(data["post_script"])
        except KeyError:
            pm.displayInfo("Post Script not available in Config")

        self.table_widget.clearContents()
        data_rows = data["rows"]

        for row in data_rows:
            row_position = self.table_widget.rowCount()
            self.table_widget.insertRow(row_position)

            file_item = QtWidgets.QTableWidgetItem(row["file_path"])
            self.table_widget.setItem(row_position, 0, file_item)

            # For Output Name
            output_name = row["output_name"]
            output_item = QtWidgets.QTableWidgetItem(output_name)
            self.table_widget.setItem(row_position, 1, output_item)

            try:
                custom_output_path = row["custom_output_path"]
            except KeyError:
                custom_output_path = ""
            custom_output_path_item = QtWidgets.QTableWidgetItem(
                custom_output_path
            )
            self.table_widget.setItem(row_position, 2, custom_output_path_item)

            set_custom_output_bttn = widgets.create_button(
                icon="mgear_folder", setMax=False, size=37.5
            )

            self.table_widget.setCellWidget(
                row_position, 3, set_custom_output_bttn
            )
            set_custom_output_bttn.clicked.connect(
                partial(self.on_custom_path_clicked, custom_output_path_item)
            )

    def export_config(self):
        data_string = self.collect_table_data()
        builder.RigBuilder.write_config_data_to_file(data_string)

    def on_custom_path_clicked(self, custom_path_widget):
        """Sets the output folder for exported builds."""
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Output Folder"
        )
        if folder_path:
            custom_path_widget.setText(folder_path)


class ResultsPopupDialog(QtWidgets.QDialog):
    """
    A custom pop-up to display Pyblish validator results.
    """

    def __init__(self, results):
        super(ResultsPopupDialog, self).__init__()
        self.setWindowTitle("Validator Results")
        self.setSizeGripEnabled(True)
        self.resize(800, 400)

        self.results_dict = results
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.create_results_view()

    def create_results_view(self):
        """Creates the main tree layout."""
        self.results_tree = QtWidgets.QTreeView()
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setWordWrap(True)
        self.layout.addWidget(self.results_tree)

        model = QtGui.QStandardItemModel()
        model.setHorizontalHeaderLabels(["Rig Name", "Check Name", "Result"])
        self.results_tree.setModel(model)

        for rig_name, checks_dict in self.results_dict.items():
            self.add_result_entry(model, rig_name, checks_dict)

        for row in range(model.rowCount()):
            idx = model.index(row, 0)
            self.results_tree.setExpanded(idx, True)

    def add_result_entry(self, model, rig_name, checks_dict):
        """Adds a collapsible entry of results for each rig."""
        group_root = QtGui.QStandardItem(rig_name)
        model.appendRow(group_root)
        summary_string = "All checks passed!"

        for i, (check_name, check_data) in enumerate(checks_dict.items()):
            result_string = "Passed" if check_data.get("success") else "Failed"
            error = check_data.get("error")
            if error is not None:
                result_string += " - {}".format(error)
                summary_string = "Some checks failed, please review errors."
            check_item = QtGui.QStandardItem(check_name)
            result_item = QtGui.QStandardItem(result_string)
            group_root.setChild(i, 1, check_item)
            group_root.setChild(i, 2, result_item)

        summary_item = QtGui.QStandardItem(summary_string)
        model.setItem(group_root.row(), 2, summary_item)


def openRigBuilderUI(*args):
    pyqt.showDialog(RigBuilderUI, dockable=True)


if __name__ == "__main__":
    window = RigBuilderUI()
    window.show()
