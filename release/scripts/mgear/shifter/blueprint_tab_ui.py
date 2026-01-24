"""Blueprint Tab UI - Tab for configuring blueprint guide inheritance."""

import mgear.core.pyqt as gqt
QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


class Ui_BlueprintTab(object):
    """UI class for the Blueprint configuration tab."""

    def setupUi(self, Form):
        """Set up the UI widgets for the Blueprint tab.

        Args:
            Form: The parent widget/form to set up.
        """
        Form.setObjectName("BlueprintTab")
        Form.resize(500, 400)

        self.mainLayout = QtWidgets.QVBoxLayout(Form)
        self.mainLayout.setObjectName("mainLayout")

        # =====================================================================
        # Enable Blueprint GroupBox
        # =====================================================================
        self.blueprint_groupBox = QtWidgets.QGroupBox(Form)
        self.blueprint_groupBox.setObjectName("blueprint_groupBox")
        self.blueprint_groupBox.setTitle("Blueprint Guide")

        self.blueprint_layout = QtWidgets.QVBoxLayout(self.blueprint_groupBox)
        self.blueprint_layout.setObjectName("blueprint_layout")

        # Enable checkbox
        self.useBlueprint_checkBox = QtWidgets.QCheckBox(self.blueprint_groupBox)
        self.useBlueprint_checkBox.setObjectName("useBlueprint_checkBox")
        self.useBlueprint_checkBox.setText("Enable Blueprint Guide")
        self.useBlueprint_checkBox.setToolTip(
            "When enabled, settings will be inherited from the blueprint guide file.\n"
            "Use the 'Use Local Override' checkboxes on each section to customize specific settings."
        )
        self.blueprint_layout.addWidget(self.useBlueprint_checkBox)

        # Path selection layout
        self.path_layout = QtWidgets.QHBoxLayout()
        self.path_layout.setObjectName("path_layout")

        self.blueprint_label = QtWidgets.QLabel(self.blueprint_groupBox)
        self.blueprint_label.setObjectName("blueprint_label")
        self.blueprint_label.setText("Blueprint Path:")
        self.path_layout.addWidget(self.blueprint_label)

        self.blueprint_lineEdit = QtWidgets.QLineEdit(self.blueprint_groupBox)
        self.blueprint_lineEdit.setObjectName("blueprint_lineEdit")
        self.blueprint_lineEdit.setPlaceholderText("Relative or absolute path to .sgt file")
        self.blueprint_lineEdit.setToolTip(
            "Path to the blueprint guide template (.sgt file).\n\n"
            "Supports:\n"
            "- Absolute paths: C:/projects/guides/blueprint.sgt\n"
            "- Relative paths: resolved using MGEAR_SHIFTER_CUSTOMSTEP_PATH environment variable"
        )
        self.path_layout.addWidget(self.blueprint_lineEdit)

        self.blueprint_pushButton = QtWidgets.QPushButton(self.blueprint_groupBox)
        self.blueprint_pushButton.setObjectName("blueprint_pushButton")
        self.blueprint_pushButton.setText("...")
        self.blueprint_pushButton.setMaximumWidth(30)
        self.blueprint_pushButton.setToolTip("Browse for blueprint guide file")
        self.path_layout.addWidget(self.blueprint_pushButton)

        self.blueprint_layout.addLayout(self.path_layout)

        # Status label
        self.blueprint_status_label = QtWidgets.QLabel(self.blueprint_groupBox)
        self.blueprint_status_label.setObjectName("blueprint_status_label")
        self.blueprint_status_label.setText("")
        self.blueprint_status_label.setWordWrap(True)
        self.blueprint_layout.addWidget(self.blueprint_status_label)

        self.mainLayout.addWidget(self.blueprint_groupBox)

        # =====================================================================
        # Information GroupBox
        # =====================================================================
        self.info_groupBox = QtWidgets.QGroupBox(Form)
        self.info_groupBox.setObjectName("info_groupBox")
        self.info_groupBox.setTitle("How Blueprint Guides Work")

        self.info_layout = QtWidgets.QVBoxLayout(self.info_groupBox)
        self.info_layout.setObjectName("info_layout")

        self.info_label = QtWidgets.QLabel(self.info_groupBox)
        self.info_label.setObjectName("info_label")
        self.info_label.setWordWrap(True)
        self.info_label.setText(
            "<p>A <b>Blueprint Guide</b> is a serialized guide template (.sgt file) "
            "that serves as a base configuration for your rig settings.</p>"
            "<p><b>How it works:</b></p>"
            "<ol>"
            "<li>Enable the blueprint and select an .sgt file</li>"
            "<li>By default, all sections will inherit settings from the blueprint</li>"
            "<li>Use 'Local Override' checkboxes on each section to customize specific settings</li>"
            "<li>When a section is overridden, it uses local values instead of blueprint values</li>"
            "</ol>"
            "<p><b>Benefits:</b></p>"
            "<ul>"
            "<li>Standardize rig settings across multiple characters</li>"
            "<li>Only override what's different per character</li>"
            "<li>Changes to the blueprint automatically propagate to all characters using it</li>"
            "</ul>"
        )
        self.info_layout.addWidget(self.info_label)

        self.mainLayout.addWidget(self.info_groupBox)

        # =====================================================================
        # Bottom Spacer
        # =====================================================================
        spacerItem = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.mainLayout.addItem(spacerItem)

        QtCore.QMetaObject.connectSlotsByName(Form)
