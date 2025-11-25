import os

# from pprint import pprint

# Pyside -------------
from mgear.vendor.Qt import QtCompat
from functools import partial

# Maya ---------------
import mgear.pymaya as pm
import maya.OpenMaya as om
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# mGear QT -----------
from mgear.core import pyqt
from mgear.vendor.Qt import QtCore, QtWidgets

# mGear core ---------
import mgear.core.utils as utils
import mgear.core.attribute as attribute

# import mgear.core.pickWalk as pickWalk

# mGear rigbits ------
import mgear.rigbits.sdk_io as sdk_io
import mgear.rigbits.sdk_manager.core as sdk_m

__author__ = "Justin Pedersen"
__email__ = "Justin@tcgcape.co.za"
__version__ = [0, 0, 1]


class SDKManagerDialog(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    """
    Useage:
        from mgear.rigbits.SDK_manager import SDK_manager_ui
        SDK_manager_ui.show_SDK_manager()

    """

    def __init__(self, ui_path=None, parent=None):
        self.toolName = "SDK_manager [Beta]"
        super(SDKManagerDialog, self).__init__(parent)
        self.setWindowTitle(self.toolName)
        self.setWindowFlags(
            self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
        )
        self.setObjectName(self.toolName)

        # Vars ---------------------
        self.saved_attr_dict = {0: None, 1: None, 2: None, 3: None, 4: None}
        self.driver = None
        self.driver_range = None
        self.driver_att = None
        self.script_jobs = []

        # --------------------------
        self.init_ui(ui_path)
        self.create_menu_bar_actions()
        self.create_layout()
        self.create_contextMenu_01()
        self.create_connections()

    def __list_widget_selection(self):
        """
        Gets all the selected List Widget items and
        returns them as a list
        """
        return [x.text() for x in self.ui.Driven_listWidget.selectedItems()]

    # ============================================================== #
    # ========================= Q T _ U I ========================== #
    # ============================================================== #

    def init_ui(self, ui_path=None):
        if not ui_path:
            ui_path = "{0}/SDK_manager.ui".format(os.path.dirname(__file__))

        self.ui = QtCompat.loadUi(uifile=ui_path)

    def create_menu_bar_actions(self):
        """
        Actions for the menu bar
        self.<>_action = QtWidgets.QAction("<>", self)
        """
        # File
        self.export_SDKs_action = QtWidgets.QAction("Export SDK's", self)
        self.import_SDKs_action = QtWidgets.QAction("Import SDK's", self)

        # Select
        self.select_all_sdk_ctls = QtWidgets.QAction(
            "Select All SDK Ctls", self
        )
        self.select_all_anim_ctls = QtWidgets.QAction(
            "Select All Anim Ctls", self
        )
        self.select_all_sdk_jnts = QtWidgets.QAction(
            "Select All SDK Jnts", self
        )
        self.select_all_sdk_nodes = QtWidgets.QAction(
            "Select All SDK Nodes", self
        )

        # Tools
        self.tgl_pre_infinity_action = QtWidgets.QAction("Pre-infinity", self)
        self.tgl_pst_infinity_action = QtWidgets.QAction("Post-infinity", self)

        self.set_tgnt_in_auto_action = QtWidgets.QAction("Auto", self)
        self.set_tgnt_in_spline_action = QtWidgets.QAction("Spline", self)
        self.set_tgnt_in_flat_action = QtWidgets.QAction("Flat", self)
        self.set_tgnt_in_linear_action = QtWidgets.QAction("Linear", self)
        self.set_tgnt_in_plateau_action = QtWidgets.QAction("Plateau", self)
        self.set_tgnt_in_stepnext_action = QtWidgets.QAction("Stepped", self)
        self.set_tgnt_out_auto_action = QtWidgets.QAction("Auto", self)
        self.set_tgnt_out_spline_action = QtWidgets.QAction("Spline", self)
        self.set_tgnt_out_flat_action = QtWidgets.QAction("Flat", self)
        self.set_tgnt_out_linear_action = QtWidgets.QAction("Linear", self)
        self.set_tgnt_out_plateau_action = QtWidgets.QAction("Plateau", self)
        self.set_tgnt_out_stepnext_action = QtWidgets.QAction("Stepped", self)

        self.set_control_limits_action = QtWidgets.QAction(
            "Auto Set Limits On Selected Controls", self
        )
        self.remove_control_limits_action = QtWidgets.QAction(
            "Auto Remove Limits On Selected Controls", self
        )
        self.rescale_driver_driven_action = QtWidgets.QAction(
            "Rescale Driver range to fit Driven", self
        )
        self.lock_unlock_anim_ctls_action = QtWidgets.QAction(
            "Lock/Unlock Animation Ctls", self
        )
        self.lock_unlock_SDK_ctls_action = QtWidgets.QAction(
            "Lock/Unlock SDK Ctls", self
        )

        self.prune_SDK_nodes_action = QtWidgets.QAction(
            "Prune SDKs with no input/output", self
        )

        # Reset
        self.reset_all_ctls = QtWidgets.QAction("Reset All Ctls", self)
        self.reset_sdk_ctls = QtWidgets.QAction("Reset SDK Ctls", self)
        self.reset_anim_ctls = QtWidgets.QAction("Reset Anim Tweaks", self)

        # Help
        self.about_action = QtWidgets.QAction("About", self)

    def create_menu_bar(self, parent_layout):
        """
        Creating the Main Menu bar for the tool

        Arguments:
            parent_layout (QT layout): parent to add the menu bar or
        Returns:
            None
        """
        self.menu_bar = QtWidgets.QMenuBar()
        # all menu bar tabs ===============
        # File -------------------
        file_menu = self.menu_bar.addMenu("File")
        file_menu.setTearOffEnabled(1)

        # Select -------------------
        select_menu = self.menu_bar.addMenu("Select")
        select_menu.setTearOffEnabled(1)

        # Tools -------------------
        tools_menu = self.menu_bar.addMenu("Tools")
        tools_menu.setTearOffEnabled(1)

        # - infinity
        infinity_menu = tools_menu.addMenu("Toggle Infinity on SDK ctls")
        infinity_menu.setTearOffEnabled(1)

        # - tangent type
        tanget_type_menu = tools_menu.addMenu("Set Tangent Type")
        tanget_type_menu.setTearOffEnabled(1)
        tanget_in_menu = tanget_type_menu.addMenu("Tangent In")
        tanget_in_menu.setTearOffEnabled(1)
        tanget_out_menu = tanget_type_menu.addMenu("Tangent Out")
        tanget_out_menu.setTearOffEnabled(1)

        # Reset -------------------
        reset_menu = self.menu_bar.addMenu("Reset")
        reset_menu.setTearOffEnabled(1)

        # Help -------------------
        help_menu = self.menu_bar.addMenu("Help")
        help_menu.setTearOffEnabled(1)

        # Menu bar actions ===============
        # File
        file_menu.addAction(self.export_SDKs_action)
        file_menu.addAction(self.import_SDKs_action)

        # Select
        select_menu.addAction(self.select_all_sdk_ctls)
        select_menu.addAction(self.select_all_anim_ctls)
        select_menu.addAction(self.select_all_sdk_jnts)
        select_menu.addAction(self.select_all_sdk_nodes)

        # Tools
        infinity_menu.addAction(self.tgl_pre_infinity_action)
        infinity_menu.addAction(self.tgl_pst_infinity_action)

        tanget_in_menu.addAction(self.set_tgnt_in_auto_action)
        tanget_in_menu.addAction(self.set_tgnt_in_spline_action)
        tanget_in_menu.addAction(self.set_tgnt_in_flat_action)
        tanget_in_menu.addAction(self.set_tgnt_in_linear_action)
        tanget_in_menu.addAction(self.set_tgnt_in_plateau_action)
        tanget_in_menu.addAction(self.set_tgnt_in_stepnext_action)
        tanget_out_menu.addAction(self.set_tgnt_out_auto_action)
        tanget_out_menu.addAction(self.set_tgnt_out_spline_action)
        tanget_out_menu.addAction(self.set_tgnt_out_flat_action)
        tanget_out_menu.addAction(self.set_tgnt_out_linear_action)
        tanget_out_menu.addAction(self.set_tgnt_out_plateau_action)
        tanget_out_menu.addAction(self.set_tgnt_out_stepnext_action)

        tools_menu.addSeparator()
        tools_menu.addAction(self.set_control_limits_action)
        tools_menu.addAction(self.remove_control_limits_action)
        tools_menu.addSeparator()
        tools_menu.addAction(self.rescale_driver_driven_action)
        tools_menu.addSeparator()
        tools_menu.addAction(self.lock_unlock_anim_ctls_action)
        tools_menu.addAction(self.lock_unlock_SDK_ctls_action)
        tools_menu.addSeparator()
        tools_menu.addAction(self.prune_SDK_nodes_action)

        # Reset
        reset_menu.addAction(self.reset_all_ctls)
        reset_menu.addAction(self.reset_sdk_ctls)
        reset_menu.addAction(self.reset_anim_ctls)

        # Help
        help_menu.addAction(self.about_action)

        # Adding to the Layout ===============
        parent_layout.setMenuBar(self.menu_bar)

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.create_menu_bar(main_layout)
        main_layout.addWidget(self.ui)

    def create_contextMenu_01(self):
        # Driven Joints List Widget context menu
        self.pop_menu = QtWidgets.QMenu(self)

        # Popup menu items
        self.pm_selectSDKCtl = QtWidgets.QAction("Select SDK Ctl", self)
        self.pm_selectAnimCtl = QtWidgets.QAction("Select Anim Ctl", self)
        self.pm_selectJnt = QtWidgets.QAction("Select Joint", self)

        self.pm_selectSDK = QtWidgets.QAction("Select SDKs", self)
        self.pm_selectTx = QtWidgets.QAction("Select Tx Curves", self)
        self.pm_selectTy = QtWidgets.QAction("Select Ty Curves", self)
        self.pm_selectTz = QtWidgets.QAction("Select Tz Curves", self)
        self.pm_selectRx = QtWidgets.QAction("Select Rx Curves", self)
        self.pm_selectRy = QtWidgets.QAction("Select Ry Curves", self)
        self.pm_selectRz = QtWidgets.QAction("Select Rz Curves", self)

        self.pm_offset_selected = QtWidgets.QAction(
            "Apply Control Offset to Selected", self
        )

        self.pm_DeleteAtCurVal = QtWidgets.QAction(
            "Delete All Keys at current Value", self
        )
        self.pm_deleteSDK = QtWidgets.QAction("Delete All SDKs", self)
        self.pm_removeDriven = QtWidgets.QAction("Remove From Driven", self)

        # Adding the items to the menu
        self.pop_menu.addSeparator()
        self.pop_menu.addAction(self.pm_selectSDKCtl)
        self.pop_menu.addAction(self.pm_selectAnimCtl)
        self.pop_menu.addAction(self.pm_selectJnt)
        self.pop_menu.addSeparator()
        self.pop_menu.addAction(self.pm_selectSDK)
        self.pop_menu.addAction(self.pm_selectTx)
        self.pop_menu.addAction(self.pm_selectTy)
        self.pop_menu.addAction(self.pm_selectTz)
        self.pop_menu.addSeparator()
        self.pop_menu.addAction(self.pm_selectRx)
        self.pop_menu.addAction(self.pm_selectRy)
        self.pop_menu.addAction(self.pm_selectRz)
        self.pop_menu.addSeparator()
        self.pop_menu.addAction(self.pm_offset_selected)
        self.pop_menu.addSeparator()
        self.pop_menu.addAction(self.pm_DeleteAtCurVal)
        self.pop_menu.addAction(self.pm_deleteSDK)
        self.pop_menu.addSeparator()
        self.pop_menu.addAction(self.pm_removeDriven)

    def create_connections(self):
        # ================================================================#
        #                       -  M E N U - B A R -                      #
        # ================================================================#
        # File
        self.export_SDKs_action.triggered.connect(lambda: self.export_SDKs())
        self.import_SDKs_action.triggered.connect(lambda: self.import_SDKs())

        # Select
        self.select_all_sdk_ctls.triggered.connect(
            partial(sdk_m.select_all, "drv")
        )
        self.select_all_anim_ctls.triggered.connect(
            partial(sdk_m.select_all, "anim")
        )
        self.select_all_sdk_jnts.triggered.connect(
            partial(sdk_m.select_all, "jnts")
        )
        self.select_all_sdk_nodes.triggered.connect(
            partial(sdk_m.select_all, "nodes")
        )

        # Tools
        self.tgl_pre_infinity_action.triggered.connect(
            partial(self.toggle_infinty, 0)
        )
        self.tgl_pst_infinity_action.triggered.connect(
            partial(self.toggle_infinty, 1)
        )

        # - tangent in
        self.set_tgnt_in_auto_action.triggered.connect(
            partial(self.set_tangent_type, "in", "auto")
        )
        self.set_tgnt_in_spline_action.triggered.connect(
            partial(self.set_tangent_type, "in", "spline")
        )
        self.set_tgnt_in_flat_action.triggered.connect(
            partial(self.set_tangent_type, "in", "flat")
        )
        self.set_tgnt_in_linear_action.triggered.connect(
            partial(self.set_tangent_type, "in", "linear")
        )
        self.set_tgnt_in_plateau_action.triggered.connect(
            partial(self.set_tangent_type, "in", "plateau")
        )
        self.set_tgnt_in_stepnext_action.triggered.connect(
            partial(self.set_tangent_type, "in", "stepnext")
        )

        # - tangent out
        self.set_tgnt_out_auto_action.triggered.connect(
            partial(self.set_tangent_type, "out", "auto")
        )
        self.set_tgnt_out_spline_action.triggered.connect(
            partial(self.set_tangent_type, "out", "spline")
        )
        self.set_tgnt_out_flat_action.triggered.connect(
            partial(self.set_tangent_type, "out", "flat")
        )
        self.set_tgnt_out_linear_action.triggered.connect(
            partial(self.set_tangent_type, "out", "linear")
        )
        self.set_tgnt_out_plateau_action.triggered.connect(
            partial(self.set_tangent_type, "out", "plateau")
        )
        self.set_tgnt_out_stepnext_action.triggered.connect(
            partial(self.set_tangent_type, "out", "stepnext")
        )

        self.set_control_limits_action.triggered.connect(
            self.set_limits_on_selected
        )
        self.remove_control_limits_action.triggered.connect(self.dummy)
        self.rescale_driver_driven_action.triggered.connect(
            self.rescale_driver_driven
        )
        self.lock_unlock_anim_ctls_action.triggered.connect(
            partial(self.lock_unlock_ctls, 0)
        )
        self.lock_unlock_SDK_ctls_action.triggered.connect(
            partial(self.lock_unlock_ctls, 1)
        )

        self.prune_SDK_nodes_action.triggered.connect(sdk_m.prune_DK_nodes)

        # Reset
        self.reset_all_ctls.triggered.connect(
            partial(sdk_m.reset_to_default, "all")
        )
        self.reset_sdk_ctls.triggered.connect(
            partial(sdk_m.reset_to_default, "drv")
        )
        self.reset_anim_ctls.triggered.connect(
            partial(sdk_m.reset_to_default, "anim")
        )

        # About
        self.about_action.triggered.connect(self.dummy)

        # ================================================================#
        #                  - C O N T R O L S - M E N U -                  #
        # ================================================================#
        self.ui.lock_limits_X.clicked.connect(
            partial(sdk_m.toggle_limits, "x")
        )
        self.ui.lock_limits_Y.clicked.connect(
            partial(sdk_m.toggle_limits, "y")
        )
        self.ui.lock_limits_Z.clicked.connect(
            partial(sdk_m.toggle_limits, "z")
        )

        self.ui.upper_limits_X.clicked.connect(
            partial(sdk_m.set_limits_from_current, "x", None, True, False)
        )
        self.ui.upper_limits_Y.clicked.connect(
            partial(sdk_m.set_limits_from_current, "y", None, True, False)
        )
        self.ui.upper_limits_Z.clicked.connect(
            partial(sdk_m.set_limits_from_current, "z", None, True, False)
        )
        self.ui.lower_limits_X.clicked.connect(
            partial(sdk_m.set_limits_from_current, "x", None, False, True)
        )
        self.ui.lower_limits_Y.clicked.connect(
            partial(sdk_m.set_limits_from_current, "y", None, False, True)
        )
        self.ui.lower_limits_Z.clicked.connect(
            partial(sdk_m.set_limits_from_current, "z", None, False, True)
        )

        # ================================================================#
        #                       - S D K - M E N U -                       #
        # ================================================================#
        # Buttons =====================
        self.ui.Driver_pushButton.clicked.connect(self.load_driver)
        self.ui.AddJntsToDriven_pushButton.clicked.connect(
            self.add_selected_to_driven
        )
        self.ui.SetDrivenKey_pushButton.clicked.connect(self.set_driven_key)
        self.ui.driverReset_pushButton.clicked.connect(
            self.update_slider_range
        )
        self.ui.driverReset_pushButton.clicked.connect(
            self.update_spin_box_range
        )

        # Skip Key Buttons =====================
        self.ui.firstKey_pushButton.clicked.connect(
            partial(self.skip_key, firstKey=True)
        )
        self.ui.prevKey_pushButton.clicked.connect(
            partial(self.skip_key, prevKey=True)
        )
        self.ui.resetKey_pushButton.clicked.connect(
            partial(self.skip_key, reset=True)
        )
        self.ui.nextKey_pushButton.clicked.connect(
            partial(self.skip_key, nextKey=True)
        )
        self.ui.lastKey_pushButton.clicked.connect(
            partial(self.skip_key, lastKey=True)
        )

        # Sliders =====================
        self.ui.driverVal_Slider.valueChanged.connect(
            partial(self.update_spin_box)
        )
        self.ui.driverVal_Slider.valueChanged.connect(
            partial(self.update_driver_val)
        )
        self.ui.driverVal_SpinBox.valueChanged.connect(
            partial(self.update_slider)
        )

        # Spin Box Math buttons =====================
        self.ui.driverMinus_1_pushButton.clicked.connect(
            partial(self.spin_box_val, -1.0)
        )
        self.ui.driverMinus_05_pushButton.clicked.connect(
            partial(self.spin_box_val, -0.5)
        )
        self.ui.driverReset_0_pushButton.clicked.connect(
            partial(self.skip_key, reset=True)
        )
        self.ui.driverAdd_05_pushButton.clicked.connect(
            partial(self.spin_box_val, 0.5)
        )
        self.ui.driverAdd_1_pushButton.clicked.connect(
            partial(self.spin_box_val, 1.0)
        )

        # Save slots =====================
        self.ui.Save_00_pushButton.clicked.connect(
            partial(self.save_slot, 0, self.ui.Save_00_pushButton)
        )
        self.ui.Save_01_pushButton.clicked.connect(
            partial(self.save_slot, 1, self.ui.Save_01_pushButton)
        )
        self.ui.Save_02_pushButton.clicked.connect(
            partial(self.save_slot, 2, self.ui.Save_02_pushButton)
        )
        self.ui.Save_03_pushButton.clicked.connect(
            partial(self.save_slot, 3, self.ui.Save_03_pushButton)
        )
        self.ui.Save_04_pushButton.clicked.connect(
            partial(self.save_slot, 4, self.ui.Save_04_pushButton)
        )

        # Ui =====================
        self.ui.Driven_listWidget.itemDoubleClicked.connect(
            self.select_list_item
        )
        self.ui.DriverAttribute_comboBox.currentIndexChanged.connect(
            self.update_list_widget
        )
        self.ui.ShowOnlyDriverAtt.stateChanged.connect(
            self.driver_attr_drop_down
        )

        # Mirror  =====================
        self.ui.Mirror_SDK_selected_ctls_pushButton.clicked.connect(
            self.mirror_selected_SDK
        )

        # ================================================================#
        #                    - P O P - U P - M E N U -                    #
        # ================================================================#
        # set listWidget context menu policy
        self.ui.Driven_listWidget.customContextMenuRequested.connect(
            self.on_context_menu
        )
        # connecting popup menu items to defs
        # select components ------------------
        self.pm_selectSDKCtl.triggered.connect(
            partial(self.select_item, SDK=True)
        )
        self.pm_selectAnimCtl.triggered.connect(
            partial(self.select_item, anim=True)
        )
        self.pm_selectJnt.triggered.connect(
            partial(self.select_item, joint=True)
        )

        # select sdk ------------------------
        self.pm_selectSDK.triggered.connect(self.select_SDKS)

        # select transtaltes ----------------
        self.pm_selectTx.triggered.connect(
            partial(self.select_SDKS, ["translateX"])
        )
        self.pm_selectTy.triggered.connect(
            partial(self.select_SDKS, ["translateY"])
        )
        self.pm_selectTz.triggered.connect(
            partial(self.select_SDKS, ["translateZ"])
        )

        # select rotates --------------------
        self.pm_selectRx.triggered.connect(
            partial(self.select_SDKS, ["rotateX"])
        )
        self.pm_selectRy.triggered.connect(
            partial(self.select_SDKS, ["rotateY"])
        )
        self.pm_selectRz.triggered.connect(
            partial(self.select_SDKS, ["rotateZ"])
        )

        # offset ---------------------------
        self.pm_offset_selected.triggered.connect(self.apply_control_offset)

        # delete ---------------------------
        self.pm_DeleteAtCurVal.triggered.connect(self.delete_current_key)
        self.pm_deleteSDK.triggered.connect(self.delete_all_current_SDK)

        # remove ---------------------------
        self.pm_removeDriven.triggered.connect(
            self.remove_selected_from_driven
        )

    def on_context_menu(self, point):
        """show context menu if there are is something selected"""
        if self.ui.Driven_listWidget.currentItem():
            self.pop_menu.exec_(self.ui.Driven_listWidget.mapToGlobal(point))

    def showEvent(self, event):
        """
        Run when the UI is Opened
        """
        return

    def closeEvent(self, event=None):
        """
        Run when UI is closed.
        - delete any remaining script jobs created by the ui.
        - find workspace root and delete the ui.
        """
        self.delete_script_jobs()

    def hideEvent(self, *args):
        """
        Maya's docable window calls the hideEvent instdead of closeEvent.
        """
        self.closeEvent()
        return

    def get_QList_widget_items(self, listWidget):
        """
        returns a list of all the items in the QlistWidget
        """
        return [
            str(listWidget.item(i).text()) for i in range(listWidget.count())
        ]

    def select_list_item(self):
        """
        If a list Item is double clicked, will select the Item in maya.
        """
        selectedItems = self.__list_widget_selection()

        # Clearing the Users selection
        pm.select(cl=True)
        for selectedItem in selectedItems:
            try:
                # Selecting each item from the list
                node = pm.PyNode(selectedItem)
                pm.select(node, add=True)
            except:  # noqa: E722
                pm.warning("Could not select {}".format(selectedItem))

    def quick_mod_key_ask(self):
        """
        Used to get the key modifiers pressed.
        """
        modifiers = QtWidgets.QApplication.queryKeyboardModifiers()
        clickMode = 0  # basic mode
        if modifiers == QtCore.Qt.ControlModifier:
            clickMode = 1  # ctrl
        elif modifiers == QtCore.Qt.ShiftModifier:
            clickMode = 2  # shift
        elif modifiers == QtCore.Qt.AltModifier:
            clickMode = 3  # alt
        elif modifiers == (
            QtCore.Qt.ControlModifier
            | QtCore.Qt.ShiftModifier
            | QtCore.Qt.AltModifier
        ):
            clickMode = 4  # ctrl+shift+alt
        elif modifiers == QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier:
            clickMode = 5  # ctrl+alt
        elif modifiers == QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier:
            clickMode = 6  # ctrl+shift
        elif modifiers == QtCore.Qt.AltModifier | QtCore.Qt.ShiftModifier:
            clickMode = 7  # alt+shift
        return clickMode

    # ============================================================== #
    # ==================== U I _ U P D A T E S ===================== #
    # ============================================================== #

    def clear_ui(self):
        """
        Utility def to reset all elements of the Ui.
        """
        self.ui.Driver_pushButton.setText("Driver")
        self.driver = None
        self.ui.DriverAttribute_comboBox.clear()
        self.ui.Driven_listWidget.clear()
        self.delete_script_jobs()

    def create_script_jobs(self):
        """
        creates a script job and connects it to
        self.driver.attr(self.driver_att)
        """
        if self.driver:
            if self.driver_att:
                watched_attr = "{0}.{1}".format(self.driver, self.driver_att)
                new_script = pm.scriptJob(
                    attributeChange=(watched_attr, partial(self.update_slider))
                )
                self.script_jobs.append(new_script)

    def delete_script_jobs(self):
        """
        deletes all the script jobs inside self.script_jobs
        """
        for job_number in self.script_jobs:
            pm.scriptJob(kill=job_number)
        self.script_jobs = []

    def driver_attr_drop_down(self):
        """
        Adds all the keyable channels to the DriverAttribute_comboBox.
        Can filter out only connected drivers if
        self.ui.ShowOnlyDriverAtt isChecked
        """
        if self.driver:
            self.ui.DriverAttribute_comboBox.clear()
            driverAttrs = pm.listAttr(self.driver, keyable=True)
            if "visibility" in driverAttrs:
                driverAttrs.remove("visibility")

            # If only only connected is checked, will filter the dropdown.
            if self.ui.ShowOnlyDriverAtt.isChecked():
                connectedAttrs = []
                for attr in driverAttrs:
                    if sdk_m.get_driven_from_attr(
                        self.driver.attr(attr), is_SDK=False
                    ):
                        connectedAttrs.append(attr)
                driverAttrs = connectedAttrs

            driverAttrs = [x.attrName(longName=True) for x in driverAttrs]
            self.ui.DriverAttribute_comboBox.insertItems(0, driverAttrs)

    def update_list_widget(self):
        """
        Updates the ListWidget whenever the DriverAttribute_comboBox is
        changed to reflect
        all the connected SDK boxes.
        """
        self.ui.Driven_listWidget.clear()
        driverAtt = self.ui.DriverAttribute_comboBox.currentText()
        if driverAtt:
            connectedSDK_ctls = sdk_m.get_driven_from_attr(
                self.driver.attr(driverAtt), is_SDK=False
            )
            self.ui.Driven_listWidget.addItems(connectedSDK_ctls)

            # updating the Range
            self.driver_range = sdk_m.get_driver_keys(
                self.driver.attr(driverAtt)
            )
            self.driver_att = self.ui.DriverAttribute_comboBox.currentText()

            # Updating Driver Range Slider
            self.update_slider_range()
            self.update_spin_box_range()

            # Creating a script job to connect
            self.delete_script_jobs()
            self.create_script_jobs()

    def update_driver_val(self, val):
        """
        updates the driver value when the spider is moved.
        """
        if self.driver:
            self.driver.attr(self.driver_att).set(float(val) / 100)

    def update_slider(self, val=None):
        """
        updates the slider to a self.driver.attr(self.driver_att)
        """
        if not val:
            val = self.driver.attr(self.driver_att).get()
        self.ui.driverVal_Slider.setValue(float(val) * 100)

    def update_spin_box(self, val):
        """
        updates the spin box
        """
        try:
            self.ui.driverVal_SpinBox.setValue(float(val) / 100)
        except:  # noqa: E722
            pass

    # ============================================================== #
    # ================ P O P _ U P _ A C T I O N S ================= #
    # ============================================================== #

    def remove_selected_from_driven(self):
        """
        Remove the selected Item from the ListWidget
        """
        selectedItems = self.ui.Driven_listWidget.selectedItems()
        for selectedItem in selectedItems:
            index_to_del = self.ui.Driven_listWidget.row(selectedItem)
            self.ui.Driven_listWidget.takeItem(index_to_del)

    def select_item(self, SDK=False, anim=False, joint=False):
        """
        Utility to select SDK box, Anim Ctl or Joint
        If CTL is held when selecting an item, it will
        NOT clear the selection.

        Arguments:
            SDK (bool): if True will Select the SDK ctl
            anim (bool): if True will Select the Anim Ctl
            joint (bool): if True will Select the Join

        Returns:
            None
        """
        # Checking if CTL is being held. If so, dont clear selection.
        clear_sel = False if self.quick_mod_key_ask() == 1 else True

        if SDK:
            self.select_list_item()

        else:
            selectedItems = self.__list_widget_selection()

            if clear_sel:
                # Clearing selection
                pm.select(cl=True)

            for selectedItem in selectedItems:
                # Select the Anim Ctls
                if anim:
                    pm.select(
                        sdk_m.get_info(utils.as_pynode(selectedItem))[1],
                        add=True,
                    )
                # Select the Joints
                if joint:
                    SDKcompInfo = sdk_m.get_info(utils.as_pynode(selectedItem))
                    pm.select(
                        sdk_m.joint_from_driver_ctl(SDKcompInfo[1]), add=True
                    )

    def delete_all_current_SDK(self):
        """
        Popup menu command to delete currently selected SDK
        """
        selectedItems = self.__list_widget_selection()
        for selectedItem in selectedItems:
            sdk_io.removeSDKs(
                node=pm.PyNode(selectedItem), sourceDriverFilter=[self.driver]
            )

        om.MGlobal.displayInfo("Key Deletion Complete")

    @utils.one_undo
    def delete_current_key(self):
        """
        Deletes the keys on connected SDK's at the
        current Driver value.
        """
        selectedItems = self.__list_widget_selection()
        for selectedItem in selectedItems:
            dvr = self.driver.attr(self.driver_att).get()
            sdk_m.delete_current_value_keys(
                dvr,
                node=pm.PyNode(selectedItem),
                sourceDriverFilter=[self.driver],
            )

    def select_SDKS(self, drivenAttrFilter=[]):
        """
        selects all the SDK nodes associated with all the list
        items that are currently selected

        By default will clear user selection, then select the anim curves
        if SHIFT is held down when button is pressed, it will ADD to
        current selection without wiping it.

        Arguments:
            drivenAttrFilter (list / optional): Will filter the connections
                                                on the sdk nodes. defaults
                                                to all if nothing specified.

        Examples:
            drivenAttrFilter = ['translateX']
            drivenAttrFilter = ['translateX', 'rotateZ']

        """
        selectedItems = self.__list_widget_selection()

        # If Shift is pressed, Add to selection.
        if self.quick_mod_key_ask() != 2:
            pm.select(cl=True)

        for selectedItem in selectedItems:
            try:
                SDK_ctl = pm.PyNode(selectedItem)
                all_sdk = sdk_io.getAllSDKInfoFromNode(SDK_ctl).items()
                for sdk, sdkInfo in all_sdk:
                    # No filter, select everything
                    if len(drivenAttrFilter) == 0:
                        pm.select(sdk, add=True)
                    # Filter what nodes are selected.
                    else:
                        if sdkInfo["drivenAttr"] in drivenAttrFilter:
                            pm.select(sdk, add=True)
            except:  # noqa: E722
                pm.warning(
                    "Could not select SDK's for" " {}".format(selectedItem)
                )

    @utils.one_undo
    def apply_control_offset(self):
        """
        moves the selected list items to the same world space value
        as the current driver control in the Driver Attr axis
        """
        if self.driver:
            # Getting driver Values
            driverAtt = self.ui.DriverAttribute_comboBox.currentText()
            driver_value = pm.getAttr(self.driver.attr(driverAtt))

        # Iterating over selected items
        selectedItems = self.__list_widget_selection()
        for selectedItem in selectedItems:
            current_item = utils.as_pynode(selectedItem)
            # Setting the new value
            pm.setAttr(current_item.attr(driverAtt), driver_value)

    # ============================================================== #
    # ============== M E N U _ B A R _ A C T I O N S =============== #
    # ============================================================== #

    # TOOLS --------------------------------
    @utils.one_undo
    def toggle_infinty(self, mode):
        """
        Sets the post and Pre Infinity on either selected Ctls
        or on All if Nothing is selected
        Arguments:
            mode (int): 0 - pre infinity
                        1 - post infinity
                        2 - both

        """
        if mode == 0:
            pre = True
            post = False
        if mode == 1:
            pre = False
            post = True
        if mode == 2:
            pre = True
            post = True

        # getting all the SDK's
        SDKs_to_set = sdk_m.get_current_SDKs()

        # setting Infinity
        for SDK in SDKs_to_set:
            if pre:
                value = 4 if SDK.preInfinity.get() == 0 else 0
                SDK.preInfinity.set(value)
            if post:
                value = 4 if SDK.postInfinity.get() == 0 else 0
                SDK.postInfinity.set(value)

        om.MGlobal.displayInfo("infinity set")

    @utils.one_undo
    def set_tangent_type(self, tangent, tanType):
        """
        Sets the tangent type on SDK ctls in selection or
        all of them in the scene.

        Arguments:
            tangent(str): "in" or "out"
            tanType(str):   - "auto"
                            - "spline"
                            - "flat"
                            - "linear"
                            - "plateau"
                            - "stepnext"
        Returns:
            None
        """
        SDKs_to_set = sdk_m.get_current_SDKs()
        # Setting tangent types on the SDK nodes
        for animNode in SDKs_to_set:
            numberOfKeys = (
                len(pm.listAttr("{0}.ktv".format(animNode), multi=True)) / 3
            )
            for index in range(0, numberOfKeys):
                if tangent == "in":
                    pm.keyTangent(
                        animNode, index=[index, index], inTangentType=tanType
                    )
                if tangent == "out":
                    pm.keyTangent(
                        animNode, index=[index, index], outTangentType=tanType
                    )

        om.MGlobal.displayInfo(
            "{} tangents have been set to" " {}".format(tangent, tanType)
        )

    def rescale_driver_driven(self):
        """
        Used to create a more linear gradient from the driver
        and driven relationship.
        """
        pm.warning("WIP")

        selectedItems = self.__list_widget_selection()

        for selectedItem in selectedItems:

            SDK_ctl = pm.PyNode(selectedItem)
            for sdk, sdkInfo in sdk_io.getAllSDKInfoFromNode(SDK_ctl).items():
                print(sdk)
                print(sdkInfo)

    def lock_unlock_ctls(self, mode=0):
        """
        Locks / unlocks edits to all Attrs on either Tweak
        Or anim Ctls Anim ctls should be locked when rigging,
        and tweak ctls should be locked when rig goes to anim.

        Arguments:
            mode (int): 1 - will lock all Tweaks
                        2 - will lock all Anim ctls

        Returns:
            None
        """
        attributes = [
            "tx",
            "ty",
            "tz",
            "rx",
            "ry",
            "rz",
            "sx",
            "sy",
            "sz",
            "v",
        ]

        if mode == 0:
            AllCtls = [x.node() for x in pm.ls("*.is_tweak")]
        if mode == 1:
            AllCtls = [x.node() for x in pm.ls("*.is_SDK")]

        if AllCtls:
            for ctl in AllCtls:
                for attr in attributes:
                    lockStatus = pm.getAttr(ctl.attr(attr), lock=True)
                    #  Setting Lock status
                    if lockStatus is True:
                        newLockStatus = False
                    else:
                        newLockStatus = True

                    attribute._lockUnlockAttribute(
                        ctl,
                        attributes=[attr],
                        lock=newLockStatus,
                        keyable=True,
                    )

        # User Feedback
        ctlType = "SDK" if mode == 1 else "Anim"

        if lockStatus is False:
            lockMode = "locked"
        else:
            lockMode = "unlocked"

        om.MGlobal.displayInfo(
            "{} Ctl Channels have been {}".format(ctlType, lockMode)
        )

    def set_limits_on_selected(self):
        """ """
        # userSel = pm.ls(sl=True)
        print("TO DO: set_limits_on_selected")
        return

    # IMPORT / EXPORT ----------------------
    def export_SDKs(self, path=None):
        """
        Gets all the SDK nodes that have the is_SDK attr
        and exports them to the path
        """
        ctls = []
        for attr in pm.ls("*.is_SDK"):
            ctls.append(attr.node())

        # Getting a Path if one wasnt given
        if path is None:
            path = self.show_file_select_dialog()

        # Exporting the SDK's
        if path:
            sdk_io.exportSDKs(nodes=ctls, filePath=path)

            om.MGlobal.displayInfo("SDK's Have been Exported Successfully")
            pm.select(ctls, r=True)
        else:
            pm.warning("SDK Export Aborted.")

    def import_SDKs(self, path=None):
        """
        Imports SDK's from File
        TO DO:
            - Check if there are already SDK's in existence.
            - Delete them if they are.
        """
        if path is None:
            path = self.show_file_select_dialog(mode=1)

        if path:
            sdk_io.importSDKs(path)

            om.MGlobal.displayInfo("SDK's Have been Imported Successfully")
        else:
            pm.warning("SDK Import Aborted.")

    def show_file_select_dialog(self, mode=0, caption=""):
        """
        Opens the file dialoge for the user to select a place to save or import
        a file from

        Arguments:
            mode (int):
                0 - save
                1 - import
            caption (str): string for what item is being exported
        Returns:
            str - path as defined by user
        """
        fileFilter = "JSON (*.json);;All Files (*.*)"
        file_path = pm.fileDialog2(
            fileFilter=fileFilter, fm=mode, caption=caption + caption
        )
        if file_path:
            return file_path[0]
        else:
            return None

    # ============================================================== #
    # ================ B U T T O N _ A C T I O N S ================= #
    # ============================================================== #

    def load_driver(self):
        """
        Loads the selected Item as a driver to set Driven keys on.
        If nothing is selected, will Clear and reset the Ui.
        """
        sel = pm.ls(sl=True)

        if len(sel) == 1:
            if pm.nodeType(sel[0]) == "transform":
                # Checking the selection isnt an animTweak or SDK ctl
                selInfo = sdk_m.get_info(sel[0])
                if not selInfo[0] and not selInfo[1]:
                    self.ui.Driver_pushButton.setText(sel[0].name())
                    self.driver = sel[0]
                    # Adding keyable channels to Driver Attribute dropdown
                    self.driver_attr_drop_down()

                else:
                    pm.warning("Cannot use SDK Ctls or animTweaks as Drivers")
            else:
                pm.warning("Can only select transforms as driver objects")

        # Reseting the Ui
        if len(sel) == 0:
            self.clear_ui()

        elif len(sel) > 1:
            pm.warning("Can only select one driver object at a time")

    def add_selected_to_driven(self):
        """
        Add all the Connected SDK boxes from selection to the list
        """
        if self.driver:
            sel = pm.ls(sl=True)
            SDK_ctls = sdk_m.ctl_from_list(sel, SDK=True)
            SDK_labels = [x.name() for x in SDK_ctls]

            # Making sure not to add duplicate labels
            current_SDK_labels = self.get_QList_widget_items(
                self.ui.Driven_listWidget
            )
            newLabels = []
            for label in SDK_labels:
                if label not in current_SDK_labels:
                    newLabels.append(label)

            self.ui.Driven_listWidget.addItems(newLabels)
        else:
            pm.warning("Please set a driver before adding Driven objects")

    @utils.one_undo
    def set_driven_key(self, setZeroKey=False):
        """
        Collect all the relavant information from the UI and set a driven
        key on all of the Items in the driven list.

        Note that if the driver is in a "Non Zero" position it will have it's
        Zero key set automatically.

        TODO:
            - Def will need a re-work
            - Check if there are values on the other Drivers
                > All other drivers must be at Zero when setting the driven key
                > Might need to calculate deltas on sdk ctls, from
                  other drivers.
        """
        if self.driver:
            driverAtt = self.ui.DriverAttribute_comboBox.currentText()
            drivenCtls = self.get_QList_widget_items(self.ui.Driven_listWidget)

            # Working out what channels to key
            keyChannels = []
            if self.ui.translate_checkBox.isChecked():
                keyChannels.append("translate")
            if self.ui.rotate_checkBox.isChecked():
                keyChannels.append("rotate")
            if self.ui.scale_checkBox.isChecked():
                keyChannels.append("scale")

            # Checking at lest one channel to key has been selected
            if not keyChannels:
                pm.warning("At least one channel to key must be selected")

            else:
                # ------------------------------------------------------
                # Finding all the other driver controls attatched to
                # the driven ctls.
                # -------------------------------------------------------
                driver_ctls = []
                for drivenCtl in drivenCtls:
                    driverCtlList = sdk_m.get_driver_from_driven(drivenCtl)
                    for dvc in driverCtlList:
                        if dvc not in driver_ctls:
                            driver_ctls.append(dvc)

                # ----------------------------------------------------------
                # Setting the SDK
                # -----------------------------------------------------------
                """
                Everything is fine, until there is more than one driver,
                and the other drivers have values, or if the current driver has
                more than one driver channel with values

                sdk_mode - 0 : Only the current driver + current driver channel
                               have values.
                               SKD can be set in the normal fassion, A check
                               is also made to see if a Zero key needs to be
                               set for the pose.

                sdk_mode - 1 : Either the Current Driver has two driving axies
                               with values or there is another driver ctl that
                               has values currently active.

                """

                # if there is more than one driver ctl found, check what mode
                # to use.
                # else just assume mode 0.
                sdk_mode = 0
                crv_types = ("animCurveUA", "animCurveUL", "animCurveUU")
                if len(driver_ctls) >= 1:
                    for driver_ctl in driver_ctls:
                        driver_ctl_node = pm.PyNode(driver_ctl)
                        # Getting all the driver_ctl_attrs
                        driver_ctl_attrs = pm.listAttr(
                            driver_ctl_node, keyable=True
                        )
                        driver_ctl_attrs = [x.attrName(longName=True) for x in driver_ctl_attrs]
                        # If its the current driver, remove the current driver
                        # attr to avoid false positives
                        if driver_ctl_node.name() == self.driver.name():
                            driver_ctl_attrs.remove(driverAtt)

                        for driver_ctl_attr in driver_ctl_attrs:
                            # Checking if an attr on the Driver has values
                            # on it
                            driver_node_val = pm.getAttr(
                                driver_ctl_node.attr(driver_ctl_attr)
                            )
                            # If there are values, check if there are any
                            # connected SDK's
                            if driver_node_val != 0:
                                connected_nodes = pm.listConnections(
                                    driver_ctl_node.attr(driver_ctl_attr)
                                )
                                # If there is something connected, make check
                                # if its an SDK node
                                if connected_nodes:
                                    for conn_node in connected_nodes:
                                        if pm.nodeType(conn_node) in crv_types:
                                            # The connected Node is an SDK Type
                                            # + Driver Attr has values
                                            sdk_mode = 1
                                            break

                # ------------------------------------------------------------
                # SDK MODE : 0
                # ------------------------------------------------------------
                if sdk_mode == 0:
                    # check if a Zero key needs to be set.
                    driver_val = pm.getAttr(self.driver.attr(driverAtt))
                    set_zero_key = True if driver_val != 0 else False
                    # Set Driven Key
                    sdk_m.key_at_current_values(
                        drivenCtls=drivenCtls,
                        keyChannels=keyChannels,
                        driver=self.driver,
                        driverAtt=driverAtt,
                        zeroKey=set_zero_key,
                    )

                # ------------------------------------------------------------
                # SDK MODE : 1
                # ------------------------------------------------------------
                if sdk_mode == 1:
                    print("TO BE IMPLEMENTED")
                    print("More than one driver has values")

                # ------------------------------------------------------------
                # updating the Range and UI
                # ------------------------------------------------------------
                self.driver_range = sdk_m.get_driver_keys(
                    self.driver.attr(driverAtt)
                )
                self.update_slider_range()
                self.update_spin_box_range()

    def skip_key(
        self,
        firstKey=False,
        prevKey=False,
        nextKey=False,
        lastKey=False,
        reset=False,
    ):
        """
        Will skip the driver Value to the defined key frame.

        Arguments:
            firstKey (bool): If True will set Driver Val to firstKey
            prevKey (bool): If True will set Driver Val to prevKey
            nextKey (bool): If True will set Driver Val to nextKey
            lastKey (bool): If True will set Driver Val to lastKey
        """

        if self.driver:
            Attr = None
            driverAtt = self.ui.DriverAttribute_comboBox.currentText()

            if firstKey:
                Attr = sdk_m.get_driver_keys(
                    self.driver.attr(driverAtt), firstKey=True
                )
            if prevKey:
                Attr = sdk_m.get_driver_keys(
                    self.driver.attr(driverAtt), prevKey=True
                )
            if nextKey:
                Attr = sdk_m.get_driver_keys(
                    self.driver.attr(driverAtt), nextKey=True
                )
            if lastKey:
                Attr = sdk_m.get_driver_keys(
                    self.driver.attr(driverAtt), lastKey=True
                )
            if reset:
                Attr = 0.0

            if Attr is not None:
                self.driver.attr(driverAtt).set(Attr)

    def update_slider_range(self, reset=False):
        """
        updates the slider to the new SDK range

        Arguments:
            reset (bool): If True will reset the slider to default position
        """
        if self.driver_range:
            self.ui.driverVal_Slider.setMinimum(self.driver_range[0] * 100)
            self.ui.driverVal_Slider.setMaximum(self.driver_range[-1] * 100)
        else:
            self.ui.driverVal_Slider.setMinimum(-1000)
            self.ui.driverVal_Slider.setMaximum(1000)

        if reset:
            self.skip_key(reset=True)

    def update_spin_box_range(self):
        """
        updates the slider to the new SDK range
        """
        if self.driver_range:
            self.ui.driverVal_SpinBox.setMinimum(self.driver_range[0])
            self.ui.driverVal_SpinBox.setMaximum(self.driver_range[-1])
        else:
            self.ui.driverVal_SpinBox.setMinimum(-10.00)
            self.ui.driverVal_SpinBox.setMaximum(10.00)

    def spin_box_val(self, val):
        """
        Will add or subtract the val from the spin box.
        """
        currentVal = self.ui.driverVal_SpinBox.value()
        newVal = currentVal + val
        self.ui.driverVal_SpinBox.setValue(float(newVal))

    def save_slot(self, index, button):
        """
        Saves the attrs of current selection into a global dictionary,
        Edits the button's Text to relect that there is something stored in it.

        Buttons use keyboard modifiers. Click once with items selected to
        save thier positions, Click again to set all saved attrs onto the Ctls.
        CTL + Click to reset the button to default.

        TO DO:
            Allow user to select joints and find the SDK ctls from them.

        Arguments:
            index (int): Index of the save slot Dictionary to use
            button (QpushButton): The Q push button used to set the the dict
                                  or call it.

        Returns:
            None
        """
        # resetting the button and clearing the dict
        keymod = self.quick_mod_key_ask()

        if keymod == 1:
            button.setText("-----")
            self.saved_attr_dict[index] = None

        if keymod == 0:
            # If the Dict values exist, try set them on the controls
            if self.saved_attr_dict[index]:
                failedSets = []
                o_item = self.saved_attr_dict[index].items()
                for transform, attrsDict in o_item:
                    for attr, val in attrsDict.items():
                        try:
                            transform.attr(attr).set(val)
                        except:  # noqa: E722
                            failedSets.append(
                                "{}.{}".format(transform.name(), attr)
                            )

                if failedSets:
                    for item in failedSets:
                        pm.warning("Could not set " + item)

            # If they dont, set them and update the button.
            else:
                if len(pm.ls(sl=True)) > 0:
                    ctlList = pm.ls(sl=True)
                    ctlsToSave = []

                    for ctl in ctlList:
                        ctlInfo = sdk_m.get_info(ctl)
                        if ctlInfo[0]:
                            ctlsToSave.append(ctlInfo[0])

                    if ctlsToSave:
                        AttrDict = {}
                        for item in ctlsToSave:
                            AttrDict[item] = {}
                            keyableAtts = pm.listAttr(item, keyable=True)
                            for Att in keyableAtts:
                                AttrDict[item][Att] = item.attr(Att).get()
                        # Setting Dict and updating Button
                        self.saved_attr_dict[index] = AttrDict
                        button.setText("[ {} ]".format(index))
                    else:
                        pm.warning("Can only Save values of SDK Ctls")

    def mirror_selected_SDK(self):
        """
        Mirrors the SDK's on selected Driver Controls
        """
        userSel = pm.ls(sl=True)

        if len(userSel) > 0:
            # Mirroring All the SDK's on each item in selection
            for ctl in userSel:
                sdk_m.mirror_SDK(ctl)

            om.MGlobal.displayInfo("Mirroring Complete")

        else:
            pm.warning("Please Select a Driver Control To Mirror SDKs on")

    def dummy(self):
        """
        Dummy function
        """
        om.MGlobal.displayInfo("Feature Not Yet Implemented")


def show(*args):
    pyqt.showDialog(SDKManagerDialog, dockable=True)
