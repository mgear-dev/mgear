"""Guide Settings UI - Main settings tab for Shifter guide configuration."""

import mgear.core.pyqt as gqt
QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


class Ui_Form(object):
    """UI class for the Guide Settings tab."""

    def setupUi(self, Form):
        """Set up the UI widgets for the Guide Settings form.

        Args:
            Form: The parent widget/form to set up.
        """
        Form.setObjectName("Form")
        Form.resize(750, 1104)
        Form.setWindowTitle("Form")

        # Main vertical layout to allow inserting blueprint header at top
        self.mainLayout = QtWidgets.QVBoxLayout(Form)
        self.mainLayout.setObjectName("mainLayout")
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        # Container widget for the grid layout
        self.gridContainer = QtWidgets.QWidget(Form)
        self.gridLayout_2 = QtWidgets.QGridLayout(self.gridContainer)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.mainLayout.addWidget(self.gridContainer)

        # =====================================================================
        # Rig Settings GroupBox (row 0)
        # =====================================================================
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setObjectName("groupBox")
        self.groupBox.setTitle("Rig Settings")
        self.groupBox.setCheckable(True)
        self.groupBox.setChecked(False)  # Default to inherit from blueprint
        # Create a reference for consistent naming with other override checkboxes
        self.override_rigSettings_checkBox = self.groupBox

        self.gridLayout_3 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_3.setObjectName("gridLayout_3")

        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")

        # Rig Name
        self.rigName_label = QtWidgets.QLabel(self.groupBox)
        self.rigName_label.setObjectName("rigName_label")
        self.rigName_label.setText("Rig Name")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.rigName_label)

        self.rigName_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.rigName_lineEdit.setObjectName("rigName_lineEdit")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.rigName_lineEdit)

        # Debug Mode
        self.mode_label = QtWidgets.QLabel(self.groupBox)
        self.mode_label.setObjectName("mode_label")
        self.mode_label.setText("Debug Mode")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.mode_label)

        self.mode_comboBox = QtWidgets.QComboBox(self.groupBox)
        self.mode_comboBox.setObjectName("mode_comboBox")
        self.mode_comboBox.addItem("Final")
        self.mode_comboBox.addItem("WIP")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.mode_comboBox)

        # Guide Build Steps
        self.step_label = QtWidgets.QLabel(self.groupBox)
        self.step_label.setObjectName("step_label")
        self.step_label.setText("Guide Build Steps:")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.step_label)

        self.step_comboBox = QtWidgets.QComboBox(self.groupBox)
        self.step_comboBox.setObjectName("step_comboBox")
        self.step_comboBox.addItem("All Steps")
        self.step_comboBox.addItem("Objects")
        self.step_comboBox.addItem("Attributes")
        self.step_comboBox.addItem("Operators")
        self.step_comboBox.addItem("Connect")
        self.step_comboBox.addItem("Joints")
        self.step_comboBox.addItem("Finalize")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.step_comboBox)

        self.gridLayout_3.addLayout(self.formLayout, 0, 0, 1, 1)
        self.gridLayout_2.addWidget(self.groupBox, 0, 0, 1, 1)

        # =====================================================================
        # Animation Channels Settings GroupBox (row 1)
        # =====================================================================
        self.groupBox_6 = QtWidgets.QGroupBox(Form)
        self.groupBox_6.setObjectName("groupBox_6")
        self.groupBox_6.setTitle("Animation Channels Settings")
        self.groupBox_6.setCheckable(True)
        self.groupBox_6.setChecked(False)  # Default to inherit from blueprint
        self.override_animChannels_checkBox = self.groupBox_6

        self.gridLayout_8 = QtWidgets.QGridLayout(self.groupBox_6)
        self.gridLayout_8.setObjectName("gridLayout_8")

        self.proxyChannels_checkBox = QtWidgets.QCheckBox(self.groupBox_6)
        self.proxyChannels_checkBox.setObjectName("proxyChannels_checkBox")
        self.proxyChannels_checkBox.setText("Add Internal Proxy Channels")
        self.gridLayout_8.addWidget(self.proxyChannels_checkBox, 0, 0, 1, 1)

        self.classicChannelNames_checkBox = QtWidgets.QCheckBox(self.groupBox_6)
        self.classicChannelNames_checkBox.setObjectName("classicChannelNames_checkBox")
        self.classicChannelNames_checkBox.setText("Use Classic Channel Names (All channels will have unique names.)")
        self.classicChannelNames_checkBox.setToolTip(
            '<html><head/><body><p>If this option is checked. The channel name will have unique full name. </p>'
            '<p align="center"><span style=" font-weight:600;">i.e: "arm_L0_blend"</span><br/></p>'
            '<p>If the option is unchecked. The channel will use the simple name. </p>'
            '<p align="center"><span style=" font-weight:600;">i.e: "arm_blend"</span><br/></p>'
            '<p><span style=" font-weight:600;">NOTE</span>: With the option unchecked. If the channel host (uiHost) '
            'have 2 or more componets of the same type. The connection will be shared amoung all the componets '
            'with the same name channel. </p>'
            '<p><span style=" font-weight:600;">i.e:</span> If we have 2 arms, the channels will be shared for both '
            'arms. To avoid this behaviour with the unchecked option, please use a unique channel host for each '
            'component.</p></body></html>'
        )
        self.gridLayout_8.addWidget(self.classicChannelNames_checkBox, 2, 0, 1, 1)

        self.attrPrefix_checkBox = QtWidgets.QCheckBox(self.groupBox_6)
        self.attrPrefix_checkBox.setObjectName("attrPrefix_checkBox")
        self.attrPrefix_checkBox.setText("Use Component Instance Name for Attributes Prefix")
        self.attrPrefix_checkBox.setToolTip(
            '<html><head/><body><p>If this option is checked. The attribute prefix will use the '
            '<span style=" font-style:italic; text-decoration: underline;">component instance name</span> '
            'and not the <span style=" font-style:italic; text-decoration: underline;">component type name</span>.</p>'
            '<p>For example, if the "<span style=" font-weight:600;">arm_2jnt_01</span>" component is used and the '
            'Classic Channel Names option is unchecked. The name of the IK/FK blend will be '
            '"<span style=" font-weight:600;">arm_blend</span>" </p>'
            '<p>This will match the default name of the '
            '<span style=" font-style:italic; text-decoration: underline;">component type</span> '
            '"<span style=" font-weight:600;">arm</span>" but if we change the name of the '
            '<span style=" font-style:italic; text-decoration: underline;">component instance</span> for other: '
            'for example "<span style=" font-weight:600;">limb</span>" the attribute name will not change.</p>'
            '<p>With this option checked the attribute name will match the '
            '<span style=" font-style:italic; text-decoration: underline;">component instance name</span> '
            '"<span style=" font-weight:600;">limb</span>" so the name of the attribute will be '
            '"<span style=" font-weight:600;">limb_blend</span>" and not the component type name.</p>'
            '<p>this will also affect the way that the attributes are shared when we have a shared UI host.</p>'
            '</body></html>'
        )
        self.gridLayout_8.addWidget(self.attrPrefix_checkBox, 3, 0, 1, 1)

        self.gridLayout_2.addWidget(self.groupBox_6, 1, 0, 1, 1)

        # =====================================================================
        # Base Rig Control GroupBox (row 2)
        # =====================================================================
        self.groupBox_7 = QtWidgets.QGroupBox(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_7.sizePolicy().hasHeightForWidth())
        self.groupBox_7.setSizePolicy(sizePolicy)
        self.groupBox_7.setObjectName("groupBox_7")
        self.groupBox_7.setTitle("Base Rig Control")
        self.groupBox_7.setCheckable(True)
        self.groupBox_7.setChecked(False)  # Default to inherit from blueprint
        self.override_baseRigControl_checkBox = self.groupBox_7

        self.verticalLayout_baseRig = QtWidgets.QVBoxLayout(self.groupBox_7)
        self.verticalLayout_baseRig.setObjectName("verticalLayout_baseRig")

        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")

        self.worldCtl_checkBox = QtWidgets.QCheckBox(self.groupBox_7)
        self.worldCtl_checkBox.setObjectName("worldCtl_checkBox")
        self.worldCtl_checkBox.setText("Use World Ctl or Custom Name")
        self.worldCtl_checkBox.setToolTip(
            '<html><head/><body><p>Shifter creates by default a Base control called '
            '"<span style=" font-weight:600;">global_C0_ctl</span>". </p>'
            '<p>Since this control is not accesible from any guide locator. Is not possible to add it as a '
            'space reference.</p>'
            '<p>If this option is active, The base control will be named '
            '"<span style=" font-weight:600;">world_ctl</span>" and we can add '
            '"<span style=" font-weight:600;">global_C0_ctl</span>" as a regular "Control_01" component. </p>'
            '<p>This way we can use it as space reference.</p>'
            '<p>The biped guide template is configured with this structure.</p></body></html>'
        )
        self.horizontalLayout_9.addWidget(self.worldCtl_checkBox)

        self.worldCtl_lineEdit = QtWidgets.QLineEdit(self.groupBox_7)
        self.worldCtl_lineEdit.setObjectName("worldCtl_lineEdit")
        self.worldCtl_lineEdit.setText("world_ctl")
        self.horizontalLayout_9.addWidget(self.worldCtl_lineEdit)

        self.verticalLayout_baseRig.addLayout(self.horizontalLayout_9)
        self.gridLayout_2.addWidget(self.groupBox_7, 2, 0, 1, 1)

        # =====================================================================
        # Skinning Settings GroupBox (row 3)
        # =====================================================================
        self.groupBox_2 = QtWidgets.QGroupBox(Form)
        self.groupBox_2.setObjectName("groupBox_2")
        self.groupBox_2.setTitle("Skinning Settings")
        self.groupBox_2.setCheckable(True)
        self.groupBox_2.setChecked(False)  # Default to inherit from blueprint
        self.override_skinning_checkBox = self.groupBox_2

        self.gridLayout_4 = QtWidgets.QGridLayout(self.groupBox_2)
        self.gridLayout_4.setObjectName("gridLayout_4")

        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")

        self.importSkin_checkBox = QtWidgets.QCheckBox(self.groupBox_2)
        self.importSkin_checkBox.setObjectName("importSkin_checkBox")
        self.importSkin_checkBox.setText("Import Skin")
        self.verticalLayout.addWidget(self.importSkin_checkBox)

        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.skin_label = QtWidgets.QLabel(self.groupBox_2)
        self.skin_label.setObjectName("skin_label")
        self.skin_label.setText("Skin Path")
        self.horizontalLayout.addWidget(self.skin_label)

        self.skin_lineEdit = QtWidgets.QLineEdit(self.groupBox_2)
        self.skin_lineEdit.setObjectName("skin_lineEdit")
        self.horizontalLayout.addWidget(self.skin_lineEdit)

        self.loadSkinPath_pushButton = QtWidgets.QPushButton(self.groupBox_2)
        self.loadSkinPath_pushButton.setObjectName("loadSkinPath_pushButton")
        self.loadSkinPath_pushButton.setText("Load Path")
        self.horizontalLayout.addWidget(self.loadSkinPath_pushButton)

        self.verticalLayout.addLayout(self.horizontalLayout)
        self.gridLayout_4.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.gridLayout_2.addWidget(self.groupBox_2, 3, 0, 1, 1)

        # =====================================================================
        # Joint Settings GroupBox (row 4)
        # =====================================================================
        self.groupBox_3 = QtWidgets.QGroupBox(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_3.sizePolicy().hasHeightForWidth())
        self.groupBox_3.setSizePolicy(sizePolicy)
        self.groupBox_3.setObjectName("groupBox_3")
        self.groupBox_3.setTitle("Joint Settings")
        self.groupBox_3.setCheckable(True)
        self.groupBox_3.setChecked(False)  # Default to inherit from blueprint
        self.override_jointSettings_checkBox = self.groupBox_3

        self.gridLayout_5 = QtWidgets.QGridLayout(self.groupBox_3)
        self.gridLayout_5.setObjectName("gridLayout_5")

        self.jointRig_checkBox = QtWidgets.QCheckBox(self.groupBox_3)
        self.jointRig_checkBox.setObjectName("jointRig_checkBox")
        self.jointRig_checkBox.setText("Separated Joint Structure")
        self.gridLayout_5.addWidget(self.jointRig_checkBox, 0, 0, 1, 1)

        self.jointWorldOri_checkBox = QtWidgets.QCheckBox(self.groupBox_3)
        self.jointWorldOri_checkBox.setEnabled(True)
        self.jointWorldOri_checkBox.setObjectName("jointWorldOri_checkBox")
        self.jointWorldOri_checkBox.setText("Force World Oriented")
        self.jointWorldOri_checkBox.setToolTip(
            "<html><head/><body><p>Force all the joint to be oriented in World Space</p></body></html>"
        )
        self.gridLayout_5.addWidget(self.jointWorldOri_checkBox, 1, 0, 1, 1)

        self.force_uniScale_checkBox = QtWidgets.QCheckBox(self.groupBox_3)
        self.force_uniScale_checkBox.setObjectName("force_uniScale_checkBox")
        self.force_uniScale_checkBox.setText("Force uniform scaling in all joints by connection all axis to Z axis")
        self.gridLayout_5.addWidget(self.force_uniScale_checkBox, 2, 0, 1, 1)

        self.connect_joints_checkBox = QtWidgets.QCheckBox(self.groupBox_3)
        self.connect_joints_checkBox.setObjectName("connect_joints_checkBox")
        self.connect_joints_checkBox.setText("Connect to existing joints.")
        self.connect_joints_checkBox.setToolTip(
            '<html><head/><body><p>When this option is active, mGear Shifter will try to connect to existing joints '
            'in the scene</p>'
            '<p><span style=" font-weight:600;">WARNING</span>: The joints need to have the rotation values freeze '
            'to 0, 0, 0. If not we will connect using constrains instead of matrix connections </p>'
            "<p>Use Maya's Modify >> Freeze Transformation command to Freeze rotation. Open the command options "
            'and ensure only Rotation is freeze, before execute the command</p>'
            '<p>Freeze joint rotations steps:</p>'
            '<p>1. Select all joints to freeze</p>'
            "<p>2. Open Maya's Modify >> Freeze Transformation options and ensure only rotation is checked</p>"
            '<p>3. Apply Modify >> Freeze Transformation</p>'
            '<p><br/></p></body></html>'
        )
        self.gridLayout_5.addWidget(self.connect_joints_checkBox, 3, 0, 1, 1)

        self.gridLayout_2.addWidget(self.groupBox_3, 4, 0, 1, 1)

        # =====================================================================
        # Post Build Data Collector GroupBox (row 5)
        # =====================================================================
        self.groupBox_8 = QtWidgets.QGroupBox(Form)
        self.groupBox_8.setObjectName("groupBox_8")
        self.groupBox_8.setTitle("Post Build Data Collector")
        self.groupBox_8.setCheckable(True)
        self.groupBox_8.setChecked(False)  # Default to inherit from blueprint
        self.override_dataCollector_checkBox = self.groupBox_8

        self.gridLayout_12 = QtWidgets.QGridLayout(self.groupBox_8)
        self.gridLayout_12.setObjectName("gridLayout_12")

        # External file data collector
        self.verticalLayout_5 = QtWidgets.QVBoxLayout()
        self.verticalLayout_5.setObjectName("verticalLayout_5")

        self.dataCollector_checkBox = QtWidgets.QCheckBox(self.groupBox_8)
        self.dataCollector_checkBox.setObjectName("dataCollector_checkBox")
        self.dataCollector_checkBox.setText("Collect Data on External File")
        self.dataCollector_checkBox.setToolTip(
            '<html><head/><body><p>Collected data will be stored in the root joint of the rig, if exist.</p>'
            '<p>The root joint is the first joint created in the rig. Not necessary to be called "root"</p>'
            '<p>If a path is provided the data will be also stored on an external JSON file</p></body></html>'
        )
        self.verticalLayout_5.addWidget(self.dataCollector_checkBox)

        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")

        self.dataCollector_label = QtWidgets.QLabel(self.groupBox_8)
        self.dataCollector_label.setObjectName("dataCollector_label")
        self.dataCollector_label.setText("Data Path")
        self.horizontalLayout_3.addWidget(self.dataCollector_label)

        self.dataCollectorPath_lineEdit = QtWidgets.QLineEdit(self.groupBox_8)
        self.dataCollectorPath_lineEdit.setObjectName("dataCollectorPath_lineEdit")
        self.horizontalLayout_3.addWidget(self.dataCollectorPath_lineEdit)

        self.dataCollectorPath_pushButton = QtWidgets.QPushButton(self.groupBox_8)
        self.dataCollectorPath_pushButton.setObjectName("dataCollectorPath_pushButton")
        self.dataCollectorPath_pushButton.setText("...")
        self.horizontalLayout_3.addWidget(self.dataCollectorPath_pushButton)

        self.verticalLayout_5.addLayout(self.horizontalLayout_3)
        self.gridLayout_12.addLayout(self.verticalLayout_5, 0, 0, 1, 1)

        # Embedded data collector
        self.verticalLayout_6 = QtWidgets.QVBoxLayout()
        self.verticalLayout_6.setObjectName("verticalLayout_6")

        self.dataCollectorEmbbeded_checkBox = QtWidgets.QCheckBox(self.groupBox_8)
        self.dataCollectorEmbbeded_checkBox.setObjectName("dataCollectorEmbbeded_checkBox")
        self.dataCollectorEmbbeded_checkBox.setText(
            "Collect Data Embbeded on Root or custom joint (Warning: FBX Ascii format is not supported)"
        )
        self.dataCollectorEmbbeded_checkBox.setToolTip(
            '<html><head/><body><p>Collected data will be stored in the root joint of the rig, if exist.</p>'
            '<p>The root joint is the first joint created in the rig. Not necessary to be called "root"</p>'
            '<p>If a path is provided the data will be also stored on an external JSON file</p></body></html>'
        )
        self.verticalLayout_6.addWidget(self.dataCollectorEmbbeded_checkBox)

        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")

        self.dataCollectorEmbbeded_label = QtWidgets.QLabel(self.groupBox_8)
        self.dataCollectorEmbbeded_label.setObjectName("dataCollectorEmbbeded_label")
        self.dataCollectorEmbbeded_label.setText("Custom Joint or Transform")
        self.horizontalLayout_4.addWidget(self.dataCollectorEmbbeded_label)

        self.dataCollectorCustomJoint_lineEdit = QtWidgets.QLineEdit(self.groupBox_8)
        self.dataCollectorCustomJoint_lineEdit.setObjectName("dataCollectorCustomJoint_lineEdit")
        self.horizontalLayout_4.addWidget(self.dataCollectorCustomJoint_lineEdit)

        self.dataCollectorPathEmbbeded_pushButton = QtWidgets.QPushButton(self.groupBox_8)
        self.dataCollectorPathEmbbeded_pushButton.setObjectName("dataCollectorPathEmbbeded_pushButton")
        self.dataCollectorPathEmbbeded_pushButton.setText("<<<")
        self.horizontalLayout_4.addWidget(self.dataCollectorPathEmbbeded_pushButton)

        self.verticalLayout_6.addLayout(self.horizontalLayout_4)
        self.gridLayout_12.addLayout(self.verticalLayout_6, 1, 0, 1, 1)

        self.gridLayout_2.addWidget(self.groupBox_8, 5, 0, 1, 1)

        # =====================================================================
        # Color Settings GroupBox (row 6)
        # =====================================================================
        self.groupBox_5 = QtWidgets.QGroupBox(Form)
        self.groupBox_5.setObjectName("groupBox_5")
        self.groupBox_5.setTitle("Color Settings")
        self.groupBox_5.setCheckable(True)
        self.groupBox_5.setChecked(False)  # Default to inherit from blueprint
        self.override_colorSettings_checkBox = self.groupBox_5

        self.gridLayout_7 = QtWidgets.QGridLayout(self.groupBox_5)
        self.gridLayout_7.setObjectName("gridLayout_7")

        # Color grid layout
        self.gridLayout_9 = QtWidgets.QGridLayout()
        self.gridLayout_9.setObjectName("gridLayout_9")

        # Column headers: Left, Center, Right
        self.label = QtWidgets.QLabel(self.groupBox_5)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.label.setText("Left")
        self.gridLayout_9.addWidget(self.label, 0, 0, 1, 1)

        self.label_2 = QtWidgets.QLabel(self.groupBox_5)
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.label_2.setText("Center")
        self.gridLayout_9.addWidget(self.label_2, 0, 1, 1, 1)

        self.label_3 = QtWidgets.QLabel(self.groupBox_5)
        self.label_3.setAlignment(QtCore.Qt.AlignCenter)
        self.label_3.setObjectName("label_3")
        self.label_3.setText("Right")
        self.gridLayout_9.addWidget(self.label_3, 0, 2, 1, 1)

        # ----- Left Column (gridLayout_11) -----
        self.gridLayout_11 = QtWidgets.QGridLayout()
        self.gridLayout_11.setObjectName("gridLayout_11")

        # Left FK
        self.fk_label = QtWidgets.QLabel(self.groupBox_5)
        self.fk_label.setObjectName("fk_label")
        self.fk_label.setText("FK")
        self.gridLayout_11.addWidget(self.fk_label, 0, 0, 1, 1)

        self.L_color_fk_label = QtWidgets.QLabel(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.L_color_fk_label.sizePolicy().hasHeightForWidth())
        self.L_color_fk_label.setSizePolicy(sizePolicy)
        self.L_color_fk_label.setMinimumSize(QtCore.QSize(0, 0))
        self.L_color_fk_label.setText("")
        self.L_color_fk_label.setObjectName("L_color_fk_label")
        self.gridLayout_11.addWidget(self.L_color_fk_label, 0, 1, 1, 1)

        self.L_color_fk_spinBox = QtWidgets.QSpinBox(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.L_color_fk_spinBox.sizePolicy().hasHeightForWidth())
        self.L_color_fk_spinBox.setSizePolicy(sizePolicy)
        self.L_color_fk_spinBox.setMaximum(31)
        self.L_color_fk_spinBox.setObjectName("L_color_fk_spinBox")
        self.gridLayout_11.addWidget(self.L_color_fk_spinBox, 0, 2, 1, 1)

        self.L_RGB_fk_pushButton = QtWidgets.QPushButton(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.L_RGB_fk_pushButton.sizePolicy().hasHeightForWidth())
        self.L_RGB_fk_pushButton.setSizePolicy(sizePolicy)
        self.L_RGB_fk_pushButton.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.L_RGB_fk_pushButton.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.L_RGB_fk_pushButton.setStyleSheet("")
        self.L_RGB_fk_pushButton.setText("")
        self.L_RGB_fk_pushButton.setObjectName("L_RGB_fk_pushButton")
        self.gridLayout_11.addWidget(self.L_RGB_fk_pushButton, 0, 3, 1, 1)

        self.L_RGB_fk_slider = QtWidgets.QSlider(self.groupBox_5)
        self.L_RGB_fk_slider.setMaximum(255)
        self.L_RGB_fk_slider.setOrientation(QtCore.Qt.Horizontal)
        self.L_RGB_fk_slider.setObjectName("L_RGB_fk_slider")
        self.gridLayout_11.addWidget(self.L_RGB_fk_slider, 0, 4, 1, 1)

        # Left IK
        self.ik_label = QtWidgets.QLabel(self.groupBox_5)
        self.ik_label.setObjectName("ik_label")
        self.ik_label.setText("IK")
        self.gridLayout_11.addWidget(self.ik_label, 1, 0, 1, 1)

        self.L_color_ik_label = QtWidgets.QLabel(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.L_color_ik_label.sizePolicy().hasHeightForWidth())
        self.L_color_ik_label.setSizePolicy(sizePolicy)
        self.L_color_ik_label.setMinimumSize(QtCore.QSize(0, 0))
        self.L_color_ik_label.setText("")
        self.L_color_ik_label.setObjectName("L_color_ik_label")
        self.gridLayout_11.addWidget(self.L_color_ik_label, 1, 1, 1, 1)

        self.L_color_ik_spinBox = QtWidgets.QSpinBox(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.L_color_ik_spinBox.sizePolicy().hasHeightForWidth())
        self.L_color_ik_spinBox.setSizePolicy(sizePolicy)
        self.L_color_ik_spinBox.setMaximum(31)
        self.L_color_ik_spinBox.setObjectName("L_color_ik_spinBox")
        self.gridLayout_11.addWidget(self.L_color_ik_spinBox, 1, 2, 1, 1)

        self.L_RGB_ik_pushButton = QtWidgets.QPushButton(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.L_RGB_ik_pushButton.sizePolicy().hasHeightForWidth())
        self.L_RGB_ik_pushButton.setSizePolicy(sizePolicy)
        self.L_RGB_ik_pushButton.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.L_RGB_ik_pushButton.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.L_RGB_ik_pushButton.setStyleSheet("")
        self.L_RGB_ik_pushButton.setText("")
        self.L_RGB_ik_pushButton.setObjectName("L_RGB_ik_pushButton")
        self.gridLayout_11.addWidget(self.L_RGB_ik_pushButton, 1, 3, 1, 1)

        self.L_RGB_ik_slider = QtWidgets.QSlider(self.groupBox_5)
        self.L_RGB_ik_slider.setMaximum(255)
        self.L_RGB_ik_slider.setOrientation(QtCore.Qt.Horizontal)
        self.L_RGB_ik_slider.setObjectName("L_RGB_ik_slider")
        self.gridLayout_11.addWidget(self.L_RGB_ik_slider, 1, 4, 1, 1)

        self.gridLayout_9.addLayout(self.gridLayout_11, 1, 0, 1, 1)

        # ----- Center Column (gridLayout) -----
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")

        # Center FK
        self.fk_label_2 = QtWidgets.QLabel(self.groupBox_5)
        self.fk_label_2.setObjectName("fk_label_2")
        self.fk_label_2.setText("FK")
        self.gridLayout.addWidget(self.fk_label_2, 0, 0, 1, 1)

        self.C_color_fk_label = QtWidgets.QLabel(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.C_color_fk_label.sizePolicy().hasHeightForWidth())
        self.C_color_fk_label.setSizePolicy(sizePolicy)
        self.C_color_fk_label.setMinimumSize(QtCore.QSize(0, 0))
        self.C_color_fk_label.setText("")
        self.C_color_fk_label.setObjectName("C_color_fk_label")
        self.gridLayout.addWidget(self.C_color_fk_label, 0, 1, 1, 1)

        self.C_color_fk_spinBox = QtWidgets.QSpinBox(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.C_color_fk_spinBox.sizePolicy().hasHeightForWidth())
        self.C_color_fk_spinBox.setSizePolicy(sizePolicy)
        self.C_color_fk_spinBox.setMaximum(31)
        self.C_color_fk_spinBox.setObjectName("C_color_fk_spinBox")
        self.gridLayout.addWidget(self.C_color_fk_spinBox, 0, 2, 1, 1)

        self.C_RGB_fk_pushButton = QtWidgets.QPushButton(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.C_RGB_fk_pushButton.sizePolicy().hasHeightForWidth())
        self.C_RGB_fk_pushButton.setSizePolicy(sizePolicy)
        self.C_RGB_fk_pushButton.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.C_RGB_fk_pushButton.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.C_RGB_fk_pushButton.setStyleSheet("")
        self.C_RGB_fk_pushButton.setText("")
        self.C_RGB_fk_pushButton.setObjectName("C_RGB_fk_pushButton")
        self.gridLayout.addWidget(self.C_RGB_fk_pushButton, 0, 3, 1, 1)

        self.C_RGB_fk_slider = QtWidgets.QSlider(self.groupBox_5)
        self.C_RGB_fk_slider.setMaximum(255)
        self.C_RGB_fk_slider.setOrientation(QtCore.Qt.Horizontal)
        self.C_RGB_fk_slider.setObjectName("C_RGB_fk_slider")
        self.gridLayout.addWidget(self.C_RGB_fk_slider, 0, 4, 1, 1)

        # Center IK
        self.ik_label_2 = QtWidgets.QLabel(self.groupBox_5)
        self.ik_label_2.setObjectName("ik_label_2")
        self.ik_label_2.setText("IK")
        self.gridLayout.addWidget(self.ik_label_2, 1, 0, 1, 1)

        self.C_color_ik_label = QtWidgets.QLabel(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.C_color_ik_label.sizePolicy().hasHeightForWidth())
        self.C_color_ik_label.setSizePolicy(sizePolicy)
        self.C_color_ik_label.setMinimumSize(QtCore.QSize(0, 0))
        self.C_color_ik_label.setText("")
        self.C_color_ik_label.setObjectName("C_color_ik_label")
        self.gridLayout.addWidget(self.C_color_ik_label, 1, 1, 1, 1)

        self.C_color_ik_spinBox = QtWidgets.QSpinBox(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.C_color_ik_spinBox.sizePolicy().hasHeightForWidth())
        self.C_color_ik_spinBox.setSizePolicy(sizePolicy)
        self.C_color_ik_spinBox.setMaximum(31)
        self.C_color_ik_spinBox.setObjectName("C_color_ik_spinBox")
        self.gridLayout.addWidget(self.C_color_ik_spinBox, 1, 2, 1, 1)

        self.C_RGB_ik_pushButton = QtWidgets.QPushButton(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.C_RGB_ik_pushButton.sizePolicy().hasHeightForWidth())
        self.C_RGB_ik_pushButton.setSizePolicy(sizePolicy)
        self.C_RGB_ik_pushButton.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.C_RGB_ik_pushButton.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.C_RGB_ik_pushButton.setStyleSheet("")
        self.C_RGB_ik_pushButton.setText("")
        self.C_RGB_ik_pushButton.setObjectName("C_RGB_ik_pushButton")
        self.gridLayout.addWidget(self.C_RGB_ik_pushButton, 1, 3, 1, 1)

        self.C_RGB_ik_slider = QtWidgets.QSlider(self.groupBox_5)
        self.C_RGB_ik_slider.setMaximum(255)
        self.C_RGB_ik_slider.setOrientation(QtCore.Qt.Horizontal)
        self.C_RGB_ik_slider.setObjectName("C_RGB_ik_slider")
        self.gridLayout.addWidget(self.C_RGB_ik_slider, 1, 4, 1, 1)

        self.gridLayout_9.addLayout(self.gridLayout, 1, 1, 1, 1)

        # ----- Right Column (gridLayout_10) -----
        self.gridLayout_10 = QtWidgets.QGridLayout()
        self.gridLayout_10.setObjectName("gridLayout_10")

        # Right FK
        self.fk_label_3 = QtWidgets.QLabel(self.groupBox_5)
        self.fk_label_3.setObjectName("fk_label_3")
        self.fk_label_3.setText("FK")
        self.gridLayout_10.addWidget(self.fk_label_3, 0, 0, 1, 1)

        self.R_color_fk_label = QtWidgets.QLabel(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.R_color_fk_label.sizePolicy().hasHeightForWidth())
        self.R_color_fk_label.setSizePolicy(sizePolicy)
        self.R_color_fk_label.setMinimumSize(QtCore.QSize(0, 0))
        self.R_color_fk_label.setText("")
        self.R_color_fk_label.setObjectName("R_color_fk_label")
        self.gridLayout_10.addWidget(self.R_color_fk_label, 0, 1, 1, 1)

        self.R_color_fk_spinBox = QtWidgets.QSpinBox(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.R_color_fk_spinBox.sizePolicy().hasHeightForWidth())
        self.R_color_fk_spinBox.setSizePolicy(sizePolicy)
        self.R_color_fk_spinBox.setMaximum(31)
        self.R_color_fk_spinBox.setObjectName("R_color_fk_spinBox")
        self.gridLayout_10.addWidget(self.R_color_fk_spinBox, 0, 2, 1, 1)

        self.R_RGB_fk_pushButton = QtWidgets.QPushButton(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.R_RGB_fk_pushButton.sizePolicy().hasHeightForWidth())
        self.R_RGB_fk_pushButton.setSizePolicy(sizePolicy)
        self.R_RGB_fk_pushButton.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.R_RGB_fk_pushButton.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.R_RGB_fk_pushButton.setStyleSheet("")
        self.R_RGB_fk_pushButton.setText("")
        self.R_RGB_fk_pushButton.setObjectName("R_RGB_fk_pushButton")
        self.gridLayout_10.addWidget(self.R_RGB_fk_pushButton, 0, 3, 1, 1)

        self.R_RGB_fk_slider = QtWidgets.QSlider(self.groupBox_5)
        self.R_RGB_fk_slider.setMaximum(255)
        self.R_RGB_fk_slider.setOrientation(QtCore.Qt.Horizontal)
        self.R_RGB_fk_slider.setObjectName("R_RGB_fk_slider")
        self.gridLayout_10.addWidget(self.R_RGB_fk_slider, 0, 4, 1, 1)

        # Right IK
        self.ik_label_3 = QtWidgets.QLabel(self.groupBox_5)
        self.ik_label_3.setObjectName("ik_label_3")
        self.ik_label_3.setText("IK")
        self.gridLayout_10.addWidget(self.ik_label_3, 1, 0, 1, 1)

        self.R_color_ik_label = QtWidgets.QLabel(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.R_color_ik_label.sizePolicy().hasHeightForWidth())
        self.R_color_ik_label.setSizePolicy(sizePolicy)
        self.R_color_ik_label.setMinimumSize(QtCore.QSize(0, 0))
        self.R_color_ik_label.setText("")
        self.R_color_ik_label.setObjectName("R_color_ik_label")
        self.gridLayout_10.addWidget(self.R_color_ik_label, 1, 1, 1, 1)

        self.R_color_ik_spinBox = QtWidgets.QSpinBox(self.groupBox_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.R_color_ik_spinBox.sizePolicy().hasHeightForWidth())
        self.R_color_ik_spinBox.setSizePolicy(sizePolicy)
        self.R_color_ik_spinBox.setMaximum(31)
        self.R_color_ik_spinBox.setObjectName("R_color_ik_spinBox")
        self.gridLayout_10.addWidget(self.R_color_ik_spinBox, 1, 2, 1, 1)

        self.R_RGB_ik_pushButton = QtWidgets.QPushButton(self.groupBox_5)
        self.R_RGB_ik_pushButton.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.R_RGB_ik_pushButton.sizePolicy().hasHeightForWidth())
        self.R_RGB_ik_pushButton.setSizePolicy(sizePolicy)
        self.R_RGB_ik_pushButton.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.R_RGB_ik_pushButton.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.R_RGB_ik_pushButton.setStyleSheet("")
        self.R_RGB_ik_pushButton.setText("")
        self.R_RGB_ik_pushButton.setObjectName("R_RGB_ik_pushButton")
        self.gridLayout_10.addWidget(self.R_RGB_ik_pushButton, 1, 3, 1, 1)

        self.R_RGB_ik_slider = QtWidgets.QSlider(self.groupBox_5)
        self.R_RGB_ik_slider.setMaximum(255)
        self.R_RGB_ik_slider.setOrientation(QtCore.Qt.Horizontal)
        self.R_RGB_ik_slider.setObjectName("R_RGB_ik_slider")
        self.gridLayout_10.addWidget(self.R_RGB_ik_slider, 1, 4, 1, 1)

        self.gridLayout_9.addLayout(self.gridLayout_10, 1, 2, 1, 1)

        self.gridLayout_7.addLayout(self.gridLayout_9, 0, 0, 1, 1)

        # Use RGB Colors checkbox (below the color grid)
        self.useRGB_checkBox = QtWidgets.QCheckBox(self.groupBox_5)
        self.useRGB_checkBox.setObjectName("useRGB_checkBox")
        self.useRGB_checkBox.setText("Use RBG Colors")
        self.gridLayout_7.addWidget(self.useRGB_checkBox, 1, 0, 1, 1)

        self.gridLayout_2.addWidget(self.groupBox_5, 6, 0, 1, 1)

        # =====================================================================
        # Bottom Spacer (row 7)
        # =====================================================================
        spacerItem = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.gridLayout_2.addItem(spacerItem, 7, 0, 1, 1)

        # =====================================================================
        # Signal Connections
        # =====================================================================
        self.jointRig_checkBox.toggled.connect(self.jointWorldOri_checkBox.setEnabled)
        QtCore.QMetaObject.connectSlotsByName(Form)
