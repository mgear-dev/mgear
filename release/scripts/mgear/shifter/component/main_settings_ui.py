"""Main Settings UI - Common settings for all Shifter components."""

import mgear.core.pyqt as gqt
from mgear.vendor.Qt import QtCore, QtWidgets


class Ui_Form(object):
    """UI class for the main component settings."""

    def setupUi(self, Form):
        """Set up the UI widgets for component main settings.

        Args:
            Form: The parent widget/form to set up.
        """
        Form.setObjectName("Form")
        Form.resize(286, 518)

        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")

        # Bottom spacer
        spacerItem = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.gridLayout.addItem(spacerItem, 5, 0, 1, 1)

        # =====================================================================
        # Channels Host Settings GroupBox
        # =====================================================================
        self.groupBox = QtWidgets.QGroupBox(Form)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setObjectName("groupBox")
        self.groupBox.setTitle("Channels Host Settings")

        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")

        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")

        self.host_label = QtWidgets.QLabel(self.groupBox)
        self.host_label.setObjectName("host_label")
        self.host_label.setText("Host:")
        self.horizontalLayout_2.addWidget(self.host_label)

        self.host_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.host_lineEdit.setObjectName("host_lineEdit")
        self.horizontalLayout_2.addWidget(self.host_lineEdit)

        self.host_pushButton = QtWidgets.QPushButton(self.groupBox)
        self.host_pushButton.setObjectName("host_pushButton")
        self.host_pushButton.setText("<<")
        self.horizontalLayout_2.addWidget(self.host_pushButton)

        self.gridLayout_2.addLayout(self.horizontalLayout_2, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox, 2, 0, 1, 1)

        # =====================================================================
        # Color Settings GroupBox
        # =====================================================================
        self.groupBox_4 = QtWidgets.QGroupBox(Form)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_4.sizePolicy().hasHeightForWidth())
        self.groupBox_4.setSizePolicy(sizePolicy)
        self.groupBox_4.setObjectName("groupBox_4")
        self.groupBox_4.setTitle("Color Settings")

        self.gridLayout_8 = QtWidgets.QGridLayout(self.groupBox_4)
        self.gridLayout_8.setObjectName("gridLayout_8")

        self.gridLayout_7 = QtWidgets.QGridLayout()
        self.gridLayout_7.setObjectName("gridLayout_7")

        # FK Color row
        self.gridLayout_9 = QtWidgets.QGridLayout()
        self.gridLayout_9.setObjectName("gridLayout_9")

        self.fk_label_2 = QtWidgets.QLabel(self.groupBox_4)
        self.fk_label_2.setObjectName("fk_label_2")
        self.fk_label_2.setText("FK")
        self.gridLayout_9.addWidget(self.fk_label_2, 0, 0, 1, 1)

        self.color_fk_label = QtWidgets.QLabel(self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.color_fk_label.sizePolicy().hasHeightForWidth())
        self.color_fk_label.setSizePolicy(sizePolicy)
        self.color_fk_label.setMinimumSize(QtCore.QSize(0, 0))
        self.color_fk_label.setText("")
        self.color_fk_label.setObjectName("color_fk_label")
        self.gridLayout_9.addWidget(self.color_fk_label, 0, 1, 1, 1)

        self.color_fk_spinBox = QtWidgets.QSpinBox(self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.color_fk_spinBox.sizePolicy().hasHeightForWidth())
        self.color_fk_spinBox.setSizePolicy(sizePolicy)
        self.color_fk_spinBox.setMaximum(31)
        self.color_fk_spinBox.setObjectName("color_fk_spinBox")
        self.gridLayout_9.addWidget(self.color_fk_spinBox, 0, 2, 1, 1)

        self.RGB_fk_pushButton = QtWidgets.QPushButton(self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.RGB_fk_pushButton.sizePolicy().hasHeightForWidth())
        self.RGB_fk_pushButton.setSizePolicy(sizePolicy)
        self.RGB_fk_pushButton.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.RGB_fk_pushButton.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.RGB_fk_pushButton.setStyleSheet("")
        self.RGB_fk_pushButton.setText("")
        self.RGB_fk_pushButton.setObjectName("RGB_fk_pushButton")
        self.gridLayout_9.addWidget(self.RGB_fk_pushButton, 0, 3, 1, 1)

        self.RGB_fk_slider = QtWidgets.QSlider(self.groupBox_4)
        self.RGB_fk_slider.setMaximum(255)
        self.RGB_fk_slider.setOrientation(QtCore.Qt.Horizontal)
        self.RGB_fk_slider.setObjectName("RGB_fk_slider")
        self.gridLayout_9.addWidget(self.RGB_fk_slider, 0, 4, 1, 1)

        self.gridLayout_7.addLayout(self.gridLayout_9, 1, 0, 1, 1)

        # IK Color row
        self.gridLayout_10 = QtWidgets.QGridLayout()
        self.gridLayout_10.setObjectName("gridLayout_10")

        self.ik_label = QtWidgets.QLabel(self.groupBox_4)
        self.ik_label.setObjectName("ik_label")
        self.ik_label.setText("IK")
        self.gridLayout_10.addWidget(self.ik_label, 0, 0, 1, 1)

        self.color_ik_label = QtWidgets.QLabel(self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.color_ik_label.sizePolicy().hasHeightForWidth())
        self.color_ik_label.setSizePolicy(sizePolicy)
        self.color_ik_label.setMinimumSize(QtCore.QSize(0, 0))
        self.color_ik_label.setText("")
        self.color_ik_label.setObjectName("color_ik_label")
        self.gridLayout_10.addWidget(self.color_ik_label, 0, 1, 1, 1)

        self.color_ik_spinBox = QtWidgets.QSpinBox(self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.color_ik_spinBox.sizePolicy().hasHeightForWidth())
        self.color_ik_spinBox.setSizePolicy(sizePolicy)
        self.color_ik_spinBox.setMaximum(31)
        self.color_ik_spinBox.setObjectName("color_ik_spinBox")
        self.gridLayout_10.addWidget(self.color_ik_spinBox, 0, 2, 1, 1)

        self.RGB_ik_pushButton = QtWidgets.QPushButton(self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.RGB_ik_pushButton.sizePolicy().hasHeightForWidth())
        self.RGB_ik_pushButton.setSizePolicy(sizePolicy)
        self.RGB_ik_pushButton.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.RGB_ik_pushButton.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.RGB_ik_pushButton.setStyleSheet("")
        self.RGB_ik_pushButton.setText("")
        self.RGB_ik_pushButton.setObjectName("RGB_ik_pushButton")
        self.gridLayout_10.addWidget(self.RGB_ik_pushButton, 0, 3, 1, 1)

        self.RGB_ik_slider = QtWidgets.QSlider(self.groupBox_4)
        self.RGB_ik_slider.setMaximum(255)
        self.RGB_ik_slider.setOrientation(QtCore.Qt.Horizontal)
        self.RGB_ik_slider.setObjectName("RGB_ik_slider")
        self.gridLayout_10.addWidget(self.RGB_ik_slider, 0, 4, 1, 1)

        self.gridLayout_7.addLayout(self.gridLayout_10, 1, 1, 1, 1)

        # Color override checkboxes
        self.overrideColors_checkBox = QtWidgets.QCheckBox(self.groupBox_4)
        self.overrideColors_checkBox.setObjectName("overrideColors_checkBox")
        self.overrideColors_checkBox.setText("Override Colors")
        self.gridLayout_7.addWidget(self.overrideColors_checkBox, 0, 0, 1, 1)

        self.useRGB_checkBox = QtWidgets.QCheckBox(self.groupBox_4)
        self.useRGB_checkBox.setObjectName("useRGB_checkBox")
        self.useRGB_checkBox.setText("Use RGB Colors")
        self.gridLayout_7.addWidget(self.useRGB_checkBox, 0, 1, 1, 1)

        self.gridLayout_8.addLayout(self.gridLayout_7, 2, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox_4, 4, 0, 1, 1)

        # =====================================================================
        # Main Settings GroupBox (Name, Side, Index, Connector)
        # =====================================================================
        self.mainSettings_groupBox = QtWidgets.QGroupBox(Form)
        self.mainSettings_groupBox.setTitle("")
        self.mainSettings_groupBox.setObjectName("mainSettings_groupBox")

        self.gridLayout_4 = QtWidgets.QGridLayout(self.mainSettings_groupBox)
        self.gridLayout_4.setObjectName("gridLayout_4")

        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")

        # Name
        self.name_label = QtWidgets.QLabel(self.mainSettings_groupBox)
        self.name_label.setObjectName("name_label")
        self.name_label.setText("Name:")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.name_label)

        self.name_lineEdit = QtWidgets.QLineEdit(self.mainSettings_groupBox)
        self.name_lineEdit.setObjectName("name_lineEdit")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.name_lineEdit)

        # Side
        self.side_label = QtWidgets.QLabel(self.mainSettings_groupBox)
        self.side_label.setObjectName("side_label")
        self.side_label.setText("Side:")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.side_label)

        self.side_comboBox = QtWidgets.QComboBox(self.mainSettings_groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.side_comboBox.sizePolicy().hasHeightForWidth())
        self.side_comboBox.setSizePolicy(sizePolicy)
        self.side_comboBox.setObjectName("side_comboBox")
        self.side_comboBox.addItem("Center")
        self.side_comboBox.addItem("Left")
        self.side_comboBox.addItem("Right")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.side_comboBox)

        # Component Index
        self.componentIndex_label = QtWidgets.QLabel(self.mainSettings_groupBox)
        self.componentIndex_label.setObjectName("componentIndex_label")
        self.componentIndex_label.setText("Component Index:")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.componentIndex_label)

        self.componentIndex_spinBox = QtWidgets.QSpinBox(self.mainSettings_groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.componentIndex_spinBox.sizePolicy().hasHeightForWidth())
        self.componentIndex_spinBox.setSizePolicy(sizePolicy)
        self.componentIndex_spinBox.setObjectName("componentIndex_spinBox")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.componentIndex_spinBox)

        # Connector
        self.conector_label = QtWidgets.QLabel(self.mainSettings_groupBox)
        self.conector_label.setObjectName("conector_label")
        self.conector_label.setText("Connector:")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.conector_label)

        self.connector_comboBox = QtWidgets.QComboBox(self.mainSettings_groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.connector_comboBox.sizePolicy().hasHeightForWidth())
        self.connector_comboBox.setSizePolicy(sizePolicy)
        self.connector_comboBox.setObjectName("connector_comboBox")
        self.connector_comboBox.addItem("standard")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.connector_comboBox)

        self.gridLayout_4.addLayout(self.formLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.mainSettings_groupBox, 0, 0, 1, 1)

        # =====================================================================
        # Custom Controllers Group GroupBox
        # =====================================================================
        self.groupBox_2 = QtWidgets.QGroupBox(Form)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_2.sizePolicy().hasHeightForWidth())
        self.groupBox_2.setSizePolicy(sizePolicy)
        self.groupBox_2.setObjectName("groupBox_2")
        self.groupBox_2.setTitle("Custom Controllers Group")

        self.gridLayout_5 = QtWidgets.QGridLayout(self.groupBox_2)
        self.gridLayout_5.setObjectName("gridLayout_5")

        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")

        self.subGroup_lineEdit = QtWidgets.QLineEdit(self.groupBox_2)
        self.subGroup_lineEdit.setObjectName("subGroup_lineEdit")
        self.subGroup_lineEdit.setToolTip(
            "<html><head/><body><p>Name for a custom controllers Group (Maya set) "
            "for the component controllers.</p>"
            '<p align="center"><span style=" font-weight:600;">i.e</span>: '
            'Setting the name "arm" will create a sub group (sub set in Mayas terminology) '
            'with the name "rig_arm_grp". This group will be under the "rig_controllers_grp"</p>'
            "<p>Leave this option empty for the default behaviour.</p></body></html>"
        )
        self.horizontalLayout_3.addWidget(self.subGroup_lineEdit)

        self.gridLayout_5.addLayout(self.horizontalLayout_3, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox_2, 3, 0, 1, 1)

        # =====================================================================
        # Joint Settings GroupBox
        # =====================================================================
        self.jointSettings_groupBox = QtWidgets.QGroupBox(Form)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.jointSettings_groupBox.sizePolicy().hasHeightForWidth())
        self.jointSettings_groupBox.setSizePolicy(sizePolicy)
        self.jointSettings_groupBox.setObjectName("jointSettings_groupBox")
        self.jointSettings_groupBox.setTitle("Joint Settings")

        self.gridLayout_3 = QtWidgets.QGridLayout(self.jointSettings_groupBox)
        self.gridLayout_3.setObjectName("gridLayout_3")

        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")

        # Parent Joint Index row
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setContentsMargins(-1, -1, -1, 0)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")

        self.useJointIndex_checkBox = QtWidgets.QCheckBox(self.jointSettings_groupBox)
        self.useJointIndex_checkBox.setObjectName("useJointIndex_checkBox")
        self.useJointIndex_checkBox.setText("Parent Joint Index")
        self.horizontalLayout_5.addWidget(self.useJointIndex_checkBox)

        self.parentJointIndex_spinBox = QtWidgets.QSpinBox(self.jointSettings_groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.parentJointIndex_spinBox.sizePolicy().hasHeightForWidth())
        self.parentJointIndex_spinBox.setSizePolicy(sizePolicy)
        self.parentJointIndex_spinBox.setMinimum(-1)
        self.parentJointIndex_spinBox.setMaximum(999999)
        self.parentJointIndex_spinBox.setProperty("value", -1)
        self.parentJointIndex_spinBox.setObjectName("parentJointIndex_spinBox")
        self.horizontalLayout_5.addWidget(self.parentJointIndex_spinBox)

        self.verticalLayout.addLayout(self.horizontalLayout_5)

        # Joint Names row
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.jointNames_label = QtWidgets.QLabel(self.jointSettings_groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.jointNames_label.sizePolicy().hasHeightForWidth())
        self.jointNames_label.setSizePolicy(sizePolicy)
        self.jointNames_label.setMinimumSize(QtCore.QSize(0, 0))
        self.jointNames_label.setObjectName("jointNames_label")
        self.jointNames_label.setText("Joint Names")
        self.horizontalLayout.addWidget(self.jointNames_label)

        self.jointNames_pushButton = QtWidgets.QPushButton(self.jointSettings_groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.jointNames_pushButton.sizePolicy().hasHeightForWidth())
        self.jointNames_pushButton.setSizePolicy(sizePolicy)
        self.jointNames_pushButton.setObjectName("jointNames_pushButton")
        self.jointNames_pushButton.setText("Configure")
        self.horizontalLayout.addWidget(self.jointNames_pushButton)

        self.verticalLayout.addLayout(self.horizontalLayout)

        # Orientation Offset GroupBox
        self.groupBox_3 = QtWidgets.QGroupBox(self.jointSettings_groupBox)
        self.groupBox_3.setObjectName("groupBox_3")
        self.groupBox_3.setTitle("Orientation Offset XYZ")

        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.groupBox_3)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")

        self.joint_offset_x_doubleSpinBox = QtWidgets.QDoubleSpinBox(self.groupBox_3)
        self.joint_offset_x_doubleSpinBox.setMinimum(-360.0)
        self.joint_offset_x_doubleSpinBox.setMaximum(360.0)
        self.joint_offset_x_doubleSpinBox.setSingleStep(90.0)
        self.joint_offset_x_doubleSpinBox.setObjectName("joint_offset_x_doubleSpinBox")
        self.joint_offset_x_doubleSpinBox.setToolTip("Rotation Offset X")
        self.horizontalLayout_4.addWidget(self.joint_offset_x_doubleSpinBox)

        self.joint_offset_y_doubleSpinBox = QtWidgets.QDoubleSpinBox(self.groupBox_3)
        self.joint_offset_y_doubleSpinBox.setMinimum(-360.0)
        self.joint_offset_y_doubleSpinBox.setMaximum(360.0)
        self.joint_offset_y_doubleSpinBox.setSingleStep(90.0)
        self.joint_offset_y_doubleSpinBox.setObjectName("joint_offset_y_doubleSpinBox")
        self.joint_offset_y_doubleSpinBox.setToolTip("Rotation Offset Y")
        self.horizontalLayout_4.addWidget(self.joint_offset_y_doubleSpinBox)

        self.joint_offset_z_doubleSpinBox = QtWidgets.QDoubleSpinBox(self.groupBox_3)
        self.joint_offset_z_doubleSpinBox.setMinimum(-360.0)
        self.joint_offset_z_doubleSpinBox.setMaximum(360.0)
        self.joint_offset_z_doubleSpinBox.setSingleStep(90.0)
        self.joint_offset_z_doubleSpinBox.setObjectName("joint_offset_z_doubleSpinBox")
        self.joint_offset_z_doubleSpinBox.setToolTip("Rotation Offset Z")
        self.horizontalLayout_4.addWidget(self.joint_offset_z_doubleSpinBox)

        self.verticalLayout.addWidget(self.groupBox_3)
        self.gridLayout_3.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.jointSettings_groupBox, 1, 0, 1, 1)

        QtCore.QMetaObject.connectSlotsByName(Form)
