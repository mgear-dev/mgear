"""
SDK Manager UI Widgets

Pure Python implementation of SDK Manager UI (replaces SDK_manager.ui)
"""

from mgear.vendor.Qt import QtCore, QtWidgets


class SDKManagerWidget(QtWidgets.QWidget):
    """Main SDK Manager widget - replaces SDK_manager.ui"""

    def __init__(self, parent=None):
        super(SDKManagerWidget, self).__init__(parent)
        self.setMinimumSize(300, 0)
        self.setWindowTitle("SDK_manager")
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI programmatically."""
        main_layout = QtWidgets.QGridLayout(self)
        main_layout.setContentsMargins(3, 3, 3, 3)
        main_layout.setSpacing(3)

        # Main tab widget
        self.main_tabWidget = QtWidgets.QTabWidget()
        self.main_tabWidget.setStyleSheet(
            "QTabBar::tab { height: 25px; width: 80px; }"
        )
        main_layout.addWidget(self.main_tabWidget, 0, 0)

        # Create tabs
        self._create_sdk_tab()
        self._create_controls_tab()
        self._create_mirror_tab()

    # =========================================================================
    # SDK Tab
    # =========================================================================
    def _create_sdk_tab(self):
        """Create the SDK tab."""
        self.setSDK_tab = QtWidgets.QWidget()
        self.main_tabWidget.addTab(self.setSDK_tab, "SDK")

        tab_layout = QtWidgets.QGridLayout(self.setSDK_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setHorizontalSpacing(0)
        tab_layout.setVerticalSpacing(6)

        # Driver group
        self._create_driver_group(tab_layout)

        # Separator
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        tab_layout.addWidget(line, 1, 0)

        # Driven group
        self._create_driven_group(tab_layout)

    def _create_driver_group(self, parent_layout):
        """Create the driver section."""
        self.driver_groupBox = QtWidgets.QGroupBox("")
        self.driver_groupBox.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        )
        parent_layout.addWidget(self.driver_groupBox, 0, 0)

        group_layout = QtWidgets.QGridLayout(self.driver_groupBox)
        group_layout.setContentsMargins(3, 3, 3, 3)
        group_layout.setSpacing(3)

        driver_layout = QtWidgets.QVBoxLayout()
        group_layout.addLayout(driver_layout, 0, 1)

        # Driver button
        self.Driver_pushButton = QtWidgets.QPushButton("Driver")
        self.Driver_pushButton.setMinimumHeight(35)
        driver_layout.addWidget(self.Driver_pushButton)

        # Driver attribute row
        attr_layout = QtWidgets.QHBoxLayout()
        driver_layout.addLayout(attr_layout)

        attr_label = QtWidgets.QLabel("Driver Attribute")
        attr_label.setMaximumWidth(80)
        attr_layout.addWidget(attr_label)

        self.DriverAttribute_comboBox = QtWidgets.QComboBox()
        attr_layout.addWidget(self.DriverAttribute_comboBox)

        # Show only connected checkbox
        self.ShowOnlyDriverAtt = QtWidgets.QCheckBox(
            "Show Only Connected Driver Attributes"
        )
        driver_layout.addWidget(self.ShowOnlyDriverAtt)

    def _create_driven_group(self, parent_layout):
        """Create the driven section."""
        self.driven_groupBox = QtWidgets.QGroupBox("")
        parent_layout.addWidget(self.driven_groupBox, 2, 0)

        group_layout = QtWidgets.QGridLayout(self.driven_groupBox)
        group_layout.setContentsMargins(3, 3, 3, 3)
        group_layout.setHorizontalSpacing(3)
        group_layout.setVerticalSpacing(6)

        # Key channels section (row 0)
        self._create_key_channels_section(group_layout)

        # Driven list section (row 1)
        self._create_driven_list_section(group_layout)

        # Separator (row 2)
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        group_layout.addWidget(line, 2, 0)

        # Driver value section (row 3)
        self._create_driver_value_section(group_layout)

        # Driver add buttons (row 4)
        self._create_driver_add_buttons(group_layout)

        # Separator (row 5)
        line2 = QtWidgets.QFrame()
        line2.setFrameShape(QtWidgets.QFrame.HLine)
        line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        group_layout.addWidget(line2, 5, 0)

        # Save slots (row 6)
        self._create_save_slots(group_layout)

    def _create_key_channels_section(self, parent_layout):
        """Create the key channels checkboxes with proper alignment."""
        key_layout = QtWidgets.QVBoxLayout()
        key_layout.setSpacing(2)
        parent_layout.addLayout(key_layout, 0, 0)

        # Key label
        key_label = QtWidgets.QLabel("Key:")
        key_layout.addWidget(key_label)

        # Channel checkbox width for alignment
        MAIN_CB_WIDTH = 70
        AXIS_CB_WIDTH = 28

        # Translate row
        translate_layout = QtWidgets.QHBoxLayout()
        translate_layout.setSpacing(3)
        key_layout.addLayout(translate_layout)

        self.translate_checkBox = QtWidgets.QCheckBox("Translate")
        self.translate_checkBox.setFixedWidth(MAIN_CB_WIDTH)
        self.translate_checkBox.setChecked(True)
        translate_layout.addWidget(self.translate_checkBox)

        self.translateX_checkBox = QtWidgets.QCheckBox("X")
        self.translateX_checkBox.setFixedWidth(AXIS_CB_WIDTH)
        self.translateX_checkBox.setChecked(True)
        translate_layout.addWidget(self.translateX_checkBox)

        self.translateY_checkBox = QtWidgets.QCheckBox("Y")
        self.translateY_checkBox.setFixedWidth(AXIS_CB_WIDTH)
        self.translateY_checkBox.setChecked(True)
        translate_layout.addWidget(self.translateY_checkBox)

        self.translateZ_checkBox = QtWidgets.QCheckBox("Z")
        self.translateZ_checkBox.setFixedWidth(AXIS_CB_WIDTH)
        self.translateZ_checkBox.setChecked(True)
        translate_layout.addWidget(self.translateZ_checkBox)

        translate_layout.addStretch()

        # Rotate row
        rotate_layout = QtWidgets.QHBoxLayout()
        rotate_layout.setSpacing(3)
        key_layout.addLayout(rotate_layout)

        self.rotate_checkBox = QtWidgets.QCheckBox("Rotate")
        self.rotate_checkBox.setFixedWidth(MAIN_CB_WIDTH)
        self.rotate_checkBox.setChecked(True)
        rotate_layout.addWidget(self.rotate_checkBox)

        self.rotateX_checkBox = QtWidgets.QCheckBox("X")
        self.rotateX_checkBox.setFixedWidth(AXIS_CB_WIDTH)
        self.rotateX_checkBox.setChecked(True)
        rotate_layout.addWidget(self.rotateX_checkBox)

        self.rotateY_checkBox = QtWidgets.QCheckBox("Y")
        self.rotateY_checkBox.setFixedWidth(AXIS_CB_WIDTH)
        self.rotateY_checkBox.setChecked(True)
        rotate_layout.addWidget(self.rotateY_checkBox)

        self.rotateZ_checkBox = QtWidgets.QCheckBox("Z")
        self.rotateZ_checkBox.setFixedWidth(AXIS_CB_WIDTH)
        self.rotateZ_checkBox.setChecked(True)
        rotate_layout.addWidget(self.rotateZ_checkBox)

        rotate_layout.addStretch()

        # Scale row
        scale_layout = QtWidgets.QHBoxLayout()
        scale_layout.setSpacing(3)
        key_layout.addLayout(scale_layout)

        self.scale_checkBox = QtWidgets.QCheckBox("Scale")
        self.scale_checkBox.setFixedWidth(MAIN_CB_WIDTH)
        self.scale_checkBox.setChecked(False)
        scale_layout.addWidget(self.scale_checkBox)

        self.scaleX_checkBox = QtWidgets.QCheckBox("X")
        self.scaleX_checkBox.setFixedWidth(AXIS_CB_WIDTH)
        self.scaleX_checkBox.setChecked(True)
        self.scaleX_checkBox.setEnabled(False)
        scale_layout.addWidget(self.scaleX_checkBox)

        self.scaleY_checkBox = QtWidgets.QCheckBox("Y")
        self.scaleY_checkBox.setFixedWidth(AXIS_CB_WIDTH)
        self.scaleY_checkBox.setChecked(True)
        self.scaleY_checkBox.setEnabled(False)
        scale_layout.addWidget(self.scaleY_checkBox)

        self.scaleZ_checkBox = QtWidgets.QCheckBox("Z")
        self.scaleZ_checkBox.setFixedWidth(AXIS_CB_WIDTH)
        self.scaleZ_checkBox.setChecked(True)
        self.scaleZ_checkBox.setEnabled(False)
        scale_layout.addWidget(self.scaleZ_checkBox)

        scale_layout.addStretch()

    def _create_driven_list_section(self, parent_layout):
        """Create the driven list section."""
        list_layout = QtWidgets.QVBoxLayout()
        parent_layout.addLayout(list_layout, 1, 0)

        # Add joints button
        self.AddJntsToDriven_pushButton = QtWidgets.QPushButton(
            "Add Selected Joints To Driven"
        )
        self.AddJntsToDriven_pushButton.setMinimumHeight(35)
        list_layout.addWidget(self.AddJntsToDriven_pushButton)

        # Driven list widget
        self.Driven_listWidget = QtWidgets.QListWidget()
        self.Driven_listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.Driven_listWidget.setAcceptDrops(False)
        self.Driven_listWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        list_layout.addWidget(self.Driven_listWidget)

        # Set driven key button
        self.SetDrivenKey_pushButton = QtWidgets.QPushButton("Set Driven Key")
        self.SetDrivenKey_pushButton.setMinimumHeight(35)
        list_layout.addWidget(self.SetDrivenKey_pushButton)

        # Key navigation buttons
        nav_layout = QtWidgets.QHBoxLayout()
        nav_layout.setSpacing(3)
        list_layout.addLayout(nav_layout)

        self.firstKey_pushButton = QtWidgets.QPushButton("<<")
        nav_layout.addWidget(self.firstKey_pushButton)

        self.prevKey_pushButton = QtWidgets.QPushButton("<")
        self.prevKey_pushButton.setMaximumHeight(40)
        nav_layout.addWidget(self.prevKey_pushButton)

        self.resetKey_pushButton = QtWidgets.QPushButton("|")
        nav_layout.addWidget(self.resetKey_pushButton)

        self.nextKey_pushButton = QtWidgets.QPushButton(">")
        nav_layout.addWidget(self.nextKey_pushButton)

        self.lastKey_pushButton = QtWidgets.QPushButton(">>")
        nav_layout.addWidget(self.lastKey_pushButton)

    def _create_driver_value_section(self, parent_layout):
        """Create the driver value slider section."""
        val_layout = QtWidgets.QHBoxLayout()
        val_layout.setSpacing(3)
        parent_layout.addLayout(val_layout, 3, 0)

        val_label = QtWidgets.QLabel("Driver Val")
        val_layout.addWidget(val_label)

        self.driverVal_SpinBox = QtWidgets.QDoubleSpinBox()
        self.driverVal_SpinBox.setSingleStep(0.1)
        val_layout.addWidget(self.driverVal_SpinBox)

        self.driverVal_Slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.driverVal_Slider.setMaximum(100)
        val_layout.addWidget(self.driverVal_Slider)

        self.driverReset_pushButton = QtWidgets.QPushButton("R")
        self.driverReset_pushButton.setMaximumWidth(35)
        val_layout.addWidget(self.driverReset_pushButton)

    def _create_driver_add_buttons(self, parent_layout):
        """Create the driver add/subtract buttons."""
        add_layout = QtWidgets.QHBoxLayout()
        add_layout.setSpacing(3)
        parent_layout.addLayout(add_layout, 4, 0)

        self.driverMinus_1_pushButton = QtWidgets.QPushButton("-1")
        add_layout.addWidget(self.driverMinus_1_pushButton)

        self.driverMinus_05_pushButton = QtWidgets.QPushButton("-0.5")
        add_layout.addWidget(self.driverMinus_05_pushButton)

        self.driverReset_0_pushButton = QtWidgets.QPushButton("0")
        add_layout.addWidget(self.driverReset_0_pushButton)

        self.driverAdd_05_pushButton = QtWidgets.QPushButton("+0.5")
        add_layout.addWidget(self.driverAdd_05_pushButton)

        self.driverAdd_1_pushButton = QtWidgets.QPushButton("+1")
        add_layout.addWidget(self.driverAdd_1_pushButton)

    def _create_save_slots(self, parent_layout):
        """Create the save slot buttons."""
        slots_layout = QtWidgets.QHBoxLayout()
        slots_layout.setSpacing(3)
        parent_layout.addLayout(slots_layout, 6, 0)

        self.Save_00_pushButton = QtWidgets.QPushButton("-----")
        slots_layout.addWidget(self.Save_00_pushButton)

        self.Save_01_pushButton = QtWidgets.QPushButton("-----")
        slots_layout.addWidget(self.Save_01_pushButton)

        self.Save_02_pushButton = QtWidgets.QPushButton("-----")
        slots_layout.addWidget(self.Save_02_pushButton)

        self.Save_03_pushButton = QtWidgets.QPushButton("-----")
        slots_layout.addWidget(self.Save_03_pushButton)

        self.Save_04_pushButton = QtWidgets.QPushButton("-----")
        slots_layout.addWidget(self.Save_04_pushButton)

    # =========================================================================
    # Controls Tab
    # =========================================================================
    def _create_controls_tab(self):
        """Create the Controls tab."""
        self.controls_tab = QtWidgets.QWidget()
        self.main_tabWidget.addTab(self.controls_tab, "Controls")

        tab_layout = QtWidgets.QGridLayout(self.controls_tab)
        tab_layout.setContentsMargins(3, 3, 3, 3)
        tab_layout.setSpacing(3)

        # Translate Limits group
        limits_group = QtWidgets.QGroupBox("Translate Limits")
        tab_layout.addWidget(limits_group, 3, 0)

        limits_layout = QtWidgets.QVBoxLayout(limits_group)
        limits_layout.setContentsMargins(3, 3, 3, 3)
        limits_layout.setSpacing(3)

        # Lock/Unlock row
        lock_layout = QtWidgets.QHBoxLayout()
        limits_layout.addLayout(lock_layout)

        lock_label = QtWidgets.QLabel("Lock/Unlock Limits")
        lock_label.setMinimumWidth(100)
        lock_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        lock_layout.addWidget(lock_label)

        self.lock_limits_X = QtWidgets.QPushButton("X")
        self.lock_limits_X.setMinimumHeight(25)
        lock_layout.addWidget(self.lock_limits_X)

        self.lock_limits_Y = QtWidgets.QPushButton("Y")
        self.lock_limits_Y.setMinimumHeight(25)
        lock_layout.addWidget(self.lock_limits_Y)

        self.lock_limits_Z = QtWidgets.QPushButton("Z")
        self.lock_limits_Z.setMinimumHeight(25)
        lock_layout.addWidget(self.lock_limits_Z)

        # Upper limits row
        upper_layout = QtWidgets.QHBoxLayout()
        limits_layout.addLayout(upper_layout)

        upper_label = QtWidgets.QLabel("Set Upper Limits")
        upper_label.setMinimumWidth(100)
        upper_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        upper_layout.addWidget(upper_label)

        self.upper_limits_X = QtWidgets.QPushButton("X")
        self.upper_limits_X.setMinimumHeight(25)
        upper_layout.addWidget(self.upper_limits_X)

        self.upper_limits_Y = QtWidgets.QPushButton("Y")
        self.upper_limits_Y.setMinimumHeight(25)
        upper_layout.addWidget(self.upper_limits_Y)

        self.upper_limits_Z = QtWidgets.QPushButton("Z")
        self.upper_limits_Z.setMinimumHeight(25)
        upper_layout.addWidget(self.upper_limits_Z)

        # Lower limits row
        lower_layout = QtWidgets.QHBoxLayout()
        limits_layout.addLayout(lower_layout)

        lower_label = QtWidgets.QLabel("Set Lower Limits")
        lower_label.setMinimumWidth(100)
        lower_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        lower_layout.addWidget(lower_label)

        self.lower_limits_X = QtWidgets.QPushButton("X")
        self.lower_limits_X.setMinimumHeight(25)
        lower_layout.addWidget(self.lower_limits_X)

        self.lower_limits_Y = QtWidgets.QPushButton("Y")
        self.lower_limits_Y.setMinimumHeight(25)
        lower_layout.addWidget(self.lower_limits_Y)

        self.lower_limits_Z = QtWidgets.QPushButton("Z")
        self.lower_limits_Z.setMinimumHeight(25)
        lower_layout.addWidget(self.lower_limits_Z)

        # Spacer
        tab_layout.addItem(
            QtWidgets.QSpacerItem(
                20, 40,
                QtWidgets.QSizePolicy.Minimum,
                QtWidgets.QSizePolicy.Expanding
            ),
            6, 0
        )

    # =========================================================================
    # Mirror Tab
    # =========================================================================
    def _create_mirror_tab(self):
        """Create the Mirror tab."""
        self.Mirror_tab = QtWidgets.QWidget()
        self.main_tabWidget.addTab(self.Mirror_tab, "Mirror")

        tab_layout = QtWidgets.QGridLayout(self.Mirror_tab)
        tab_layout.setContentsMargins(6, 6, 6, 6)

        self.Mirror_SDK_selected_ctls_pushButton = QtWidgets.QPushButton(
            "Mirror SDK's From Selected Ctls X+ To X-"
        )
        self.Mirror_SDK_selected_ctls_pushButton.setMinimumHeight(35)
        tab_layout.addWidget(
            self.Mirror_SDK_selected_ctls_pushButton, 0, 0
        )

        # Spacer
        tab_layout.addItem(
            QtWidgets.QSpacerItem(
                20, 40,
                QtWidgets.QSizePolicy.Minimum,
                QtWidgets.QSizePolicy.Expanding
            ),
            1, 0
        )
