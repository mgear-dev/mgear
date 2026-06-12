import maya.cmds as cmds
import mgear.pymaya as pm
from mgear.core import pyqt
from mgear.core import attribute
from mgear.core import utils
from mgear.core import widgets as mwgt
from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
from mgear.core import callbackManager
import timeit
from functools import partial
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


from . import channel_master_utils as cmu
from . import channel_master_widgets as cmw
from . import channel_master_node as cmn
import importlib


class ChannelMaster(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    def __init__(self, parent=None):
        super(ChannelMaster, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.setWindowTitle("Channel Master")
        min_w = 155
        default_w = 250
        default_h = 600
        self.setMinimumWidth(min_w)
        self.resize(default_w, default_h)
        if cmds.about(ntOS=True):
            flags = self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
            self.setWindowFlags(flags)
        elif cmds.about(macOS=True):
            self.setWindowFlags(QtCore.Qt.Tool)

        self.values_buffer = []
        self.namespace = None

        self.doUpdateHighlightedSliders = True

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)

        self.create_actions()
        self.create_widgets()
        self.refresh_node_list()

        # Init Main Channels table
        chan_config, namespace = cmu.get_table_config_from_selection()
        self.main_table = cmw.ChannelTable(chan_config, namespace, self)

        self.create_layout()
        self.create_connections()

        # Init nodes
        self.update_channel_master_from_node()

        self.refresh_channels_values()

        self.cb_manager = callbackManager.CallbackManager()

        self.add_callback()

        # Usert settings to store
        # Create the user_settings dictionary with tuples containing the
        # UI elements and their default values.
        self.user_settings = {
            "channelMaster_use_node_namespace_action": (
                self.use_node_namespace_action,
                True,
            ),
            "channelMaster_use_only_local_data_action": (
                self.use_only_local_data_action,
                False,
            ),
            "channelMaster_display_sync_graph_action": (
                self.display_sync_graph_action,
                False,
            ),
            "channelMaster_display_fullname_action": (
                self.display_fullname_action,
                False,
            ),
            "channelMaster_scrubbing_update_action": (
                self.scrubbing_update_action,
                False,
            ),
            "channelMaster_key_all_tabs_action": (
                self.key_all_tabs_action,
                False,
            ),
            "channelMaster_copypaste_all_channels_action": (
                self.copypaste_all_channels_action,
                False,
            ),
            "channelMaster_key_only_behavior_action": (
                self.key_only_behavior_action,
                False,
            ),
            "channelMaster_key_delete_reset_only_selected_action": (
                self.key_delete_reset_only_selected_action,
                False,
            ),
            "channelMaster_display_sync_graph_action": (
                self.display_sync_graph_action,
                False,
            ),
        }
        self.load_settings()

    def add_callback(self):
        self.cb_manager.selectionChangedCB(
            "Channel_Master_selection_CB", self.selection_change
        )
        # self.cb_manager.userTimeChangedCB("Channel_Master_userTimeChange_CB",
        #                                   self.time_changed)

    def enterEvent(self, evnt):
        self.doUpdateHighlightedSliders = False
        self.refresh_channels_values()
        self.doUpdateHighlightedSliders = True

    def close(self):
        self.cb_manager.removeAllManagedCB()
        self.deleteLater()

    def closeEvent(self, evnt):
        self.close()

    def dockCloseEventTriggered(self):
        self.close()

    def create_actions(self):
        # file actions
        self.file_new_node_action = QtWidgets.QAction("New Node", self)
        self.file_new_node_action.setIcon(pyqt.get_icon("mgear_plus-square"))
        self.file_save_node_action = QtWidgets.QAction(
            "Save Current Node", self
        )
        self.file_save_node_action.setIcon(pyqt.get_icon("mgear_save"))
        self.set_external_config_action = QtWidgets.QAction(
            "Add External Config", self
        )
        self.set_external_config_action.setIcon(
            pyqt.get_icon("mgear_plus-circle")
        )
        self.remove_external_config_action = QtWidgets.QAction(
            "Remove External Config", self
        )
        self.remove_external_config_action.setIcon(
            pyqt.get_icon("mgear_minus-circle")
        )
        self.file_export_all_action = QtWidgets.QAction(
            "Export All Tabs", self
        )
        self.file_export_all_action.setIcon(pyqt.get_icon("mgear_log-out"))
        self.file_export_current_action = QtWidgets.QAction(
            "Export Current Tab", self
        )
        self.file_export_current_action.setIcon(pyqt.get_icon("mgear_log-out"))
        self.file_import_action = QtWidgets.QAction("Import", self)
        self.file_import_action.setIcon(pyqt.get_icon("mgear_log-in"))
        self.file_import_add_action = QtWidgets.QAction("Import Add", self)
        self.file_import_add_action.setIcon(pyqt.get_icon("mgear_log-in"))
        self.use_node_namespace_action = QtWidgets.QAction(
            "Use Namespace From ChannelMaster Node", self
        )
        self.use_node_namespace_action.setCheckable(True)
        self.use_node_namespace_action.setChecked(True)

        self.use_only_local_data_action = QtWidgets.QAction(
            "Use Only Data Embedded in Local Node", self
        )
        self.use_only_local_data_action.setCheckable(True)

        # Select actions
        self.select_all_hosts_action = QtWidgets.QAction(
            "Select All Ctl Hosts", self
        )
        self.select_all_hosts_action.setIcon(
            pyqt.get_icon("mgear_mouse-pointer")
        )

        self.select_current_tab_all_hosts_action = QtWidgets.QAction(
            "Select Current Tab All Ctl Hosts", self
        )
        self.select_current_tab_all_hosts_action.setIcon(
            pyqt.get_icon("mgear_mouse-pointer")
        )

        # Display actions
        self.display_fullname_action = QtWidgets.QAction(
            "Channel Full Name", self
        )
        self.display_fullname_action.setCheckable(True)
        self.display_fullname_action.setShortcut(QtGui.QKeySequence("Ctrl+F"))

        self.scrubbing_update_action = QtWidgets.QAction(
            "Update Value While Scrubbing", self
        )
        self.scrubbing_update_action.setCheckable(True)
        self.scrubbing_update_action.setShortcut(QtGui.QKeySequence("Ctrl+U"))

        self.display_edit_channel_order_action = QtWidgets.QAction(
            "Edit Channel Order", self
        )

        self.display_sync_graph_action = QtWidgets.QAction(
            "Sync with Graph Editor", self
        )
        self.display_sync_graph_action.setIcon(pyqt.get_icon("mgear_activity"))
        self.display_auto_sync_graph_action = QtWidgets.QAction(
            "Auto Sync with Graph Editor", self
        )
        self.display_auto_sync_graph_action.setCheckable(True)

        self.display_order_default_action = QtWidgets.QAction("Default", self)
        self.display_order_alphabetical_action = QtWidgets.QAction(
            "Alphabetical", self
        )

        # Key actions
        self.key_all_action = QtWidgets.QAction("Keyframe", self)
        self.key_all_action.setIcon(pyqt.get_icon("mgear_key"))
        self.key_all_action.setShortcut(QtGui.QKeySequence("S"))
        self.key_copy_action = QtWidgets.QAction("Copy Key", self)
        self.key_copy_action.setIcon(pyqt.get_icon("mgear_copy"))
        self.key_copy_action.setShortcut(QtGui.QKeySequence("Ctrl+C"))
        self.key_paste_action = QtWidgets.QAction("Paste Key", self)
        self.key_paste_action.setIcon(pyqt.get_icon("mgear_clipboard"))
        self.key_paste_action.setShortcut(QtGui.QKeySequence("Ctrl+V"))
        self.key_all_tabs_action = QtWidgets.QAction("Keyframe All Tabs", self)
        self.key_all_tabs_action.setCheckable(True)
        self.key_only_behavior_action = QtWidgets.QAction(
            "Key Only (Not Toggle Keyframe)", self
        )
        self.key_only_behavior_action.setCheckable(True)
        self.key_delete_reset_only_selected_action = QtWidgets.QAction(
            "Key/Delete/Reset Only on Selected", self
        )
        self.key_delete_reset_only_selected_action.setCheckable(True)
        self.copypaste_all_channels_action = QtWidgets.QAction(
            "Copy/Paste All Channels", self
        )
        self.copypaste_all_channels_action.setCheckable(True)

        self.key_del_frame_action = QtWidgets.QAction(
            "Delete Current Frame Keyframe", self
        )
        self.key_del_frame_action.setIcon(pyqt.get_icon("mgear_trash-2"))
        self.key_del_frame_action.setShortcut(QtGui.QKeySequence("Shift+S"))

        # Tabs Actions
        self.tab_new_action = QtWidgets.QAction("New Tab", self)
        self.tab_new_action.setIcon(pyqt.get_icon("mgear_menu"))
        self.tab_del_action = QtWidgets.QAction("Delete Current Tab", self)
        self.tab_del_action.setIcon(pyqt.get_icon("mgear_trash-2"))
        self.tab_dup_action = QtWidgets.QAction("Duplicate Tab", self)
        self.tab_dup_action.setIcon(pyqt.get_icon("mgear_copy"))
        self.tab_rename_action = QtWidgets.QAction("Rename Tab", self)
        # self.tab_rename_action.setIcon(pyqt.get_icon("mgear_copy"))

    def create_widgets(self):
        # Menu bar
        self.menu_bar = QtWidgets.QMenuBar()
        self.file_menu = self.menu_bar.addMenu("File")
        self.file_menu.addAction(self.file_new_node_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.file_save_node_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.set_external_config_action)
        self.file_menu.addAction(self.remove_external_config_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.file_export_all_action)
        self.file_menu.addAction(self.file_export_current_action)
        self.file_menu.addAction(self.file_import_action)
        self.file_menu.addAction(self.file_import_add_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.use_node_namespace_action)
        self.file_menu.addAction(self.use_only_local_data_action)

        self.select_menu = self.menu_bar.addMenu("Select")
        self.select_menu.addAction(self.select_all_hosts_action)
        self.select_menu.addAction(self.select_current_tab_all_hosts_action)

        self.display_menu = self.menu_bar.addMenu("Display")
        self.display_menu.addAction(self.display_sync_graph_action)
        self.display_menu.addAction(self.display_auto_sync_graph_action)
        self.display_menu.addSeparator()
        self.display_menu.addAction(self.display_fullname_action)
        self.display_menu.addAction(self.scrubbing_update_action)
        self.display_menu.addSeparator()
        self.display_menu.addAction(self.display_edit_channel_order_action)
        self.display_menu.addSeparator()
        self.order_menu = self.display_menu.addMenu("Order")
        self.order_menu.addAction(self.display_order_default_action)
        self.order_menu.addAction(self.display_order_alphabetical_action)

        self.key_menu = self.menu_bar.addMenu("Keyframe")
        self.key_menu.addAction(self.key_all_action)
        self.key_menu.addSeparator()
        self.key_menu.addAction(self.key_copy_action)
        self.key_menu.addAction(self.key_paste_action)
        self.key_menu.addSeparator()
        self.key_menu.addAction(self.key_del_frame_action)
        self.key_menu.addSeparator()
        self.key_menu.addAction(self.key_all_tabs_action)
        self.key_menu.addAction(self.copypaste_all_channels_action)
        self.key_menu.addAction(self.key_only_behavior_action)
        self.key_menu.addAction(self.key_delete_reset_only_selected_action)

        self.tab_menu = self.menu_bar.addMenu("Tab")
        self.tab_menu.addAction(self.tab_new_action)
        self.tab_menu.addAction(self.tab_dup_action)
        self.tab_menu.addAction(self.tab_rename_action)
        self.tab_menu.addSeparator()
        self.tab_menu.addAction(self.tab_del_action)

        # Keyframe widgets
        self.key_all_button = mwgt.create_button(
            size=34, icon="mgear_key", toolTip="Keyframe"
        )
        self.key_copy_button = mwgt.create_button(
            size=34, icon="mgear_copy", toolTip="Copy Keyframe"
        )
        self.key_paste_button = mwgt.create_button(
            size=34, icon="mgear_clipboard", toolTip="Paste Keyframe"
        )

        self.reset_all_button = mwgt.create_button(
            size=34, icon="mgear_rewind", toolTip="Reset to Creation Value"
        )

        self.sync_graph_editor_button = mwgt.create_button(
            size=34, icon="mgear_activity", toolTip="Sync with Graph Editor"
        )

        # channel listing widgets
        self.lock_button = mwgt.create_button(
            size=34,
            icon="mgear_unlock",
            toggle_icon="mgear_lock",
            toolTip="Lock Channel Auto Refresh",
        )
        self.refresh_button = mwgt.create_button(
            size=17, icon="mgear_refresh-cw", toolTip="Refresh Channel List"
        )
        self.add_channel_button = mwgt.create_button(
            size=34, icon="mgear_plus", toolTip="Add Selected Channels"
        )
        self.remove_channel_button = mwgt.create_button(
            size=34, icon="mgear_minus", toolTip="Remove Selected Channels"
        )

        # node list widgets
        self.node_list_combobox = QtWidgets.QComboBox()
        self.node_list_combobox.setMaximumHeight(17)
        self.refresh_node_list_button = mwgt.create_button(
            size=17, icon="mgear_refresh-cw", toolTip="Refresh Node List"
        )
        self.new_node_button = mwgt.create_button(
            size=17,
            icon="mgear_plus",
            toolTip="Create New Channel Master Node",
        )

        # search widgets
        self.search_label = QtWidgets.QLabel("Filter Channel: ")
        self.search_lineEdit = QtWidgets.QLineEdit()
        self.search_clear_button = mwgt.create_button(
            size=17, icon="mgear_delete", toolTip="Clear Search Field"
        )

        # tabs widget
        self.tab_widget = QtWidgets.QTabWidget()
        self.add_tab_button = mwgt.create_button(
            size=17, icon="mgear_plus", toolTip="Add New Tab"
        )
        self.add_tab_button.setFlat(True)
        self.add_tab_button.setMaximumWidth(34)

        self.tab_widget.setCornerWidget(
            self.add_tab_button, corner=QtCore.Qt.TopRightCorner
        )

    def create_layout(self):

        line_edit_style = """
        QLineEdit {
           border: 0 solid transparent;
           margin-right: 2px;
           margin-left: 2px;
        }
        """

        # main Layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)
        main_layout.setMenuBar(self.menu_bar)

        # keyframe buttons Layout
        key_buttons_layout = QtWidgets.QHBoxLayout()
        key_buttons_layout.addWidget(self.key_all_button)
        key_buttons_layout.addWidget(self.key_copy_button)
        key_buttons_layout.addWidget(self.key_paste_button)
        key_buttons_layout.addWidget(self.reset_all_button)
        key_buttons_layout.addWidget(self.sync_graph_editor_button)

        # channel listing buttons Layout
        channel_buttons_layout = QtWidgets.QVBoxLayout()
        channel_buttons_layout.addWidget(self.lock_button)
        channel_buttons_layout.addWidget(self.refresh_button)
        channel_add_remove_buttons_layout = QtWidgets.QHBoxLayout()
        channel_add_remove_buttons_layout.addWidget(self.add_channel_button)
        channel_add_remove_buttons_layout.addWidget(self.remove_channel_button)
        channel_add_remove_buttons_layout.addWidget(self.lock_button)

        # node list layout
        node_list_layout = QtWidgets.QHBoxLayout()
        node_list_layout.addWidget(self.node_list_combobox)
        node_list_layout.addWidget(self.refresh_node_list_button)
        node_list_layout.addWidget(self.new_node_button)

        # search line layout
        search_line_layout = QtWidgets.QHBoxLayout()
        self.search_lineEdit.setStyleSheet(line_edit_style)
        search_line_layout.addWidget(self.search_label)
        search_line_layout.addWidget(self.search_lineEdit)
        search_line_layout.addWidget(self.search_clear_button)

        # Buttons layout
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addLayout(key_buttons_layout)
        buttons_layout.addStretch()
        buttons_layout.addLayout(channel_add_remove_buttons_layout)

        main_layout.addLayout(node_list_layout)
        main_layout.addLayout(search_line_layout)
        main_layout.addLayout(buttons_layout)
        main_layout.addWidget(self.tab_widget)

        # main_table
        self.tab_widget.addTab(self.main_table, "Main")

    def create_connections(self):
        #  actions File
        self.file_new_node_action.triggered.connect(self.create_new_node)
        self.file_save_node_action.triggered.connect(self.save_node_data)
        self.set_external_config_action.triggered.connect(
            self.set_external_config
        )
        self.remove_external_config_action.triggered.connect(
            self.remove_external_config
        )
        self.file_export_all_action.triggered.connect(self.export_node_data)
        self.file_export_current_action.triggered.connect(self.export_tab_data)
        self.file_import_action.triggered.connect(self.import_node_data)
        self.file_import_add_action.triggered.connect(self.add_node_data)
        self.use_node_namespace_action.triggered.connect(
            self.use_node_namespace
        )
        self.use_only_local_data_action.triggered.connect(
            self.use_only_local_data
        )

        # actions select
        self.select_all_hosts_action.triggered.connect(self.select_all_hosts)

        self.select_current_tab_all_hosts_action.triggered.connect(
            self.select_current_table_all_hosts
        )

        # actions display
        self.display_fullname_action.triggered.connect(
            self.action_display_fullname
        )
        self.display_sync_graph_action.triggered.connect(
            self.action_sync_graph_editor
        )
        self.display_edit_channel_order_action.triggered.connect(
            self.action_edit_channel_order
        )
        self.scrubbing_update_action.triggered.connect(
            self.action_scrubbing_update
        )
        self.display_order_default_action.triggered.connect(
            self.action_default_order
        )
        self.display_order_alphabetical_action.triggered.connect(
            self.action_alphabetical_order
        )

        # actions keyframe
        self.key_all_action.triggered.connect(self.key_all)
        self.key_copy_action.triggered.connect(self.copy_channel_values)
        self.key_paste_action.triggered.connect(self.paste_channel_values)
        self.key_del_frame_action.triggered.connect(self.remove_key_all)

        # action tab
        self.tab_new_action.triggered.connect(self.add_tab)
        self.tab_del_action.triggered.connect(self.delete_tab)
        self.tab_dup_action.triggered.connect(self.duplicate_tab)
        self.tab_rename_action.triggered.connect(self.rename_tab)

        # Buttons
        self.search_lineEdit.textChanged.connect(self.search_channels)
        self.search_clear_button.clicked.connect(self.search_clear)

        self.refresh_button.clicked.connect(self.update_main_table)

        self.key_all_button.clicked.connect(self.key_all)
        self.key_copy_button.clicked.connect(self.copy_channel_values)
        self.key_paste_button.clicked.connect(self.paste_channel_values)
        self.reset_all_button.clicked.connect(self.reset_all)
        self.sync_graph_editor_button.clicked.connect(
            self.action_sync_graph_editor
        )

        self.refresh_node_list_button.clicked.connect(self.refresh_node_list)
        self.new_node_button.clicked.connect(self.create_new_node)

        self.add_tab_button.clicked.connect(self.add_tab)

        self.add_channel_button.clicked.connect(
            self.add_channels_to_current_tab
        )
        self.remove_channel_button.clicked.connect(
            self.remove_selected_channels
        )

        self.node_list_combobox.currentIndexChanged.connect(
            self.update_channel_master_from_node
        )
        # self.tab_widget.currentChanged.connect(self.save_node_data)
        self.tab_widget.currentChanged.connect(self.tab_change)

    def get_current_table(self):
        """get the active channel table for active tab

        Returns:
            QTableWidget: the channel table widget
        """
        tab = self.tab_widget.currentIndex()
        table = self.tab_widget.widget(tab)
        return table

    def get_all_tables(self):
        """Get all the table widget from each tab

        Returns:
            TYPE: Description
        """
        tables = []
        for i in range(self.tab_widget.count()):
            tables.append(self.tab_widget.widget(i))

        return tables

    def get_current_node(self):
        """Get the current node

        Returns:
            str: current node name
        """
        current_node = self.node_list_combobox.currentText()
        if not current_node:
            return
        if not pm.objExists(current_node):
            pm.displayWarning(
                "Channel Master Node: {}".format(current_node)
                + " Can't be found or doesn't exist"
            )
            return

        return current_node

    def get_channel_master_config(self):
        """Get the configuration from the current channel master

        Returns:
            TYPE: Description
        """
        cm_config_data = cmu.init_channel_master_config_data()
        tables = self.get_all_tables()
        for i, t in enumerate(tables):
            config = t.get_table_config()
            name = self.tab_widget.tabText(i)
            cm_config_data["tabs"].append(name)
            cm_config_data["tabs_data"][name] = config

        cm_config_data["current_tab"] = self.tab_widget.currentIndex()

        return cm_config_data

    def get_current_tab_name(self):
        """get the current taba name

        Returns:
            str: current tab name
        """
        return self.tab_widget.tabText(self.tab_widget.currentIndex())

    def save_node_data(self):
        """Save current node data"""
        current_node = self.get_current_node()
        if not current_node:
            pm.displayWarning(
                "Node data can't be saved." " Please check if node exist"
            )
            return

        cmn.set_node_data(current_node, self.get_channel_master_config())
        pm.displayInfo("Node: {}  data saved".format(current_node))

    def export_node_data(self):
        """Export the data configuration for the node. This include all
        the tabs
        """
        current_node = self.get_current_node()
        cmn.export_data(current_node)

    def export_tab_data(self):
        """Export the data configuration from the current tab"""
        current_node = self.get_current_node()
        current_tab = self.get_current_tab_name()
        cmn.export_data(current_node, current_tab)

    def get_data_from_current_node(self):
        """Get data configuration from the current node

        Returns:
            TYPE: Description
        """
        node = self.get_current_node()
        if not node:
            return
        # local data usage
        # first check if node has force_local_data attr if not create it
        if not cmds.attributeQuery("force_local_data", node=node, exists=True):
            cmds.addAttr(node, ln="force_local_data", at="bool", dv=False)
        # refresh configuration status in actions
        force_local_data = cmds.getAttr("{}.force_local_data".format(node))
        self.use_only_local_data_action.setChecked(force_local_data)

        # node namespace usage
        # first check if node has use_node_namespace attr if not create it
        if not cmds.attributeQuery(
            "use_node_namespace", node=node, exists=True
        ):
            cmds.addAttr(node, ln="use_node_namespace", at="bool", dv=False)
        # refresh configuration status in actions
        use_node_namespace = cmds.getAttr("{}.use_node_namespace".format(node))
        self.use_node_namespace_action.setChecked(use_node_namespace)

        self.set_namespace(node)

        return cmn.get_node_data(node)

    def import_node_data(self):
        """Create a new node and import the data from an exported data file"""
        sel = pm.selected()
        node = cmn.import_data()
        self.set_active_node(node)
        pm.select(sel)

    def add_node_data(self):
        """Add the imported data to the current node"""
        current_node = self.get_current_node()
        cmn.import_data(node=current_node, add_data=True)
        self.update_channel_master_from_node()

    def set_external_config(self):
        """set external config path"""
        current_node = self.get_current_node()
        cmn.set_external_config_path(current_node)
        self.update_channel_master_from_node()

    def remove_external_config(self):
        """remove external config path"""
        current_node = self.get_current_node()
        cmn.remove_external_config_path(current_node)
        self.update_channel_master_from_node()

    def update_channel_master_from_node(self):
        """Update the channel master content from the node configuration"""
        data = self.get_data_from_current_node()
        if not data:
            return
        self.clear_all_tabs()
        for t in data["tabs"]:
            if t != "Main":
                new_table = self.add_tab(name=t)
                new_table.set_table_config(
                    data["tabs_data"][t], self.namespace
                )
        self.tab_widget.setCurrentIndex(data["current_tab"])

    def update_main_table(self):
        """update main table content"""
        self.main_table.update_table_from_selection()
        # Clean values buffer
        # self.values_buffer = []

    def search_channels(self):
        """Filter the visible rows in the channel table.
        NOTE: ideally this should be implemented with a model/view pattern
        using QTableView
        """
        search_name = self.search_lineEdit.text()
        table = self.get_current_table()
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            if search_name.lower() in item.text().lower() or not search_name:
                table.setRowHidden(i, False)
            else:
                table.setRowHidden(i, True)

    def search_clear(self):
        """Clear search field"""
        self.search_lineEdit.setText("")

    def refresh_channels_values(self, current_time=False):
        """Refresh the channel values of the current table"""
        table = self.get_current_table()
        if table:
            self.doUpdateHighlightedSliders = False
            table.refresh_channels_values(current_time)
            self.doUpdateHighlightedSliders = True

    def tab_change(self):
        """Slot triggered when tab change"""
        self.refresh_channels_values()
        self.action_display_fullname()
        # self.values_buffer = []

    def set_namespace(self, current_node):
        if self.use_node_namespace_action.isChecked():
            self.namespace = pm.PyNode(current_node).namespace()
        else:
            self.namespace = None

    # actions
    def use_only_local_data(self):
        node = self.get_current_node()
        if not node:
            return
        use_local_data = self.use_only_local_data_action.isChecked()
        cmds.setAttr("{}.force_local_data".format(node), use_local_data)
        self.update_channel_master_from_node()

    def use_node_namespace(self):
        node = self.get_current_node()
        if not node:
            return
        use_node_ns = self.use_node_namespace_action.isChecked()
        cmds.setAttr("{}.use_node_namespace".format(node), use_node_ns)
        self.update_channel_master_from_node()

    def action_scrubbing_update(self):
        if self.scrubbing_update_action.isChecked():
            self.cb_manager.userTimeChangedCB(
                "Channel_Master_userTimeChange_CB", self.time_changed
            )
        else:
            self.cb_manager.removeManagedCB("Channel_Master_userTimeChange_CB")

    def action_edit_channel_order(self):
        """Show Edit channel order dialog"""
        try:
            self.channel_dialog.close()
            self.channel_dialog.deleteLater()
        except:
            pass
        table = self.get_current_table()

        self.channel_dialog = channelOrderDialog(self, table)
        self.channel_dialog.show()

    def action_display_fullname(self):
        """Toggle channel name  from nice name to full name"""
        table = self.get_current_table()
        for i in range(table.rowCount()):
            table.set_channel_fullname(
                i, self.display_fullname_action.isChecked()
            )

    def action_sync_graph_editor(self):
        table = self.get_current_table()
        attr_configs = []
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            ac = item.data(QtCore.Qt.UserRole)
            attr_configs.append(ac)

        cmu.sync_graph_editor(attr_configs, self.namespace)

    def action_default_order(self):
        """reset the channels to the default order"""
        current_tab = self.tab_widget.currentIndex()
        self.update_channel_master_from_node()
        self.tab_widget.setCurrentIndex(current_tab)

    def action_alphabetical_order(self):
        """order  the channels alphabetically"""
        # table = self.get_current_table()
        for i in range(self.tab_widget.count()):
            table = self.tab_widget.widget(i)
            table.sortItems(0, order=QtCore.Qt.AscendingOrder)

    # callback slots
    def selection_change(self, *args):
        """Callback triggered when selection change

        Args:
            *args: Description
        """
        if not self.lock_button.isChecked():
            self.update_main_table()

    def time_changed(self, *args):
        """Callback triger when time change

        Args:
            *args: Description
        """
        self.refresh_channels_values(current_time=pm.currentTime())

    # Keyframe

    def get_key_status(self, table):
        """Retunr 2 lists with the keyed and not keyed channels

        Args:
            table (TYPE): Description
        """
        not_keyed = []
        keyed = []
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            attr = table.namespace_sync(
                item.data(QtCore.Qt.UserRole)["fullName"]
            )
            if cmu.current_frame_has_key(attr) and cmu.value_equal_keyvalue(
                attr
            ):
                keyed.append(attr)
            else:
                not_keyed.append(attr)

        return keyed, not_keyed

    def key_all(self, *args):
        """Set a keyframe in all the channels

        Args:
            *args: Description
        """
        if self.key_all_tabs_action.isChecked():
            pm.displayInfo(
                "Keyframe all tabs." " Only add keys. Not toggle key behavior!"
            )
            tables = self.get_all_tables()
            key_only = True
        else:
            tables = [self.get_current_table()]
            key_only = self.key_only_behavior_action.isChecked()
        for table in tables:
            keyed, not_keyed = self.get_key_status(table)

            # filter if selected only
            if (
                not_keyed
                and self.key_delete_reset_only_selected_action.isChecked()
            ):
                not_keyed = (
                    table.get_fullname_from_selected_rows().intersection(
                        not_keyed
                    )
                )
            if (
                keyed
                and self.key_delete_reset_only_selected_action.isChecked()
            ):
                keyed = table.get_fullname_from_selected_rows().intersection(
                    keyed
                )

            # set / remove keys
            if not_keyed:
                cmu.set_key(not_keyed)

            elif not key_only and keyed:
                cmu.remove_key(keyed)

        self.refresh_channels_values()

    def remove_key_all(self, *args):
        """Remove keyframe from keyed channels

        Args:
            *args: Description
        """
        table = self.get_current_table()
        keyed, not_keyed = self.get_key_status(table)
        if keyed and self.key_delete_reset_only_selected_action.isChecked():
            keyed = table.get_fullname_from_selected_rows().intersection(keyed)
        if keyed:
            cmu.remove_key(keyed)
            self.refresh_channels_values()

    def copy_channel_values(self, *args):
        """Copy all attribute values from curretn channel table

        Args:
            *args: Description
        """
        table = self.get_current_table()
        self.values_buffer = []
        items = []

        if self.copypaste_all_channels_action.isChecked():
            for i in range(table.rowCount()):
                items.append(table.item(i, 0))
        else:
            items = table.selectedItems()

        for item in items:
            attr = table.namespace_sync(
                item.data(QtCore.Qt.UserRole)["fullName"]
            )
            self.values_buffer.append(cmds.getAttr(attr))

    def reset_all(self, *args):
        """reset all values from current table to the creation value.
        Note: creation value is the value that was set when the channel master
        tab channel was created. The default value is the Maya's attr defaults
        and can be different from the creation value

        Args:
            *args: Description
        """
        table = self.get_current_table()
        selected_rows = table.get_fullname_from_selected_rows()
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            attr_config = item.data(QtCore.Qt.UserRole)
            # is only in selected is active we skip the item if not selected
            if (
                selected_rows
                and self.key_delete_reset_only_selected_action.isChecked()
            ):
                if attr_config["fullName"] not in selected_rows:
                    continue
            cmu.reset_creation_value_attribute(attr_config, self.namespace)
        self.refresh_channels_values()

    @utils.one_undo
    def paste_channel_values(self, *args):
        """Paste and key values stored in buffer

        Args:
            *args: Description

        Returns:
            None: Return none if no values stored in buffer
        """
        if not self.values_buffer:
            return
        items = []
        table = self.get_current_table()
        if self.copypaste_all_channels_action.isChecked():
            for i in range(table.rowCount()):
                items.append(table.item(i, 0))

        else:
            items = table.selectedItems()
        if len(items) == len(self.values_buffer):
            for e, item in enumerate(items):
                attr = table.namespace_sync(
                    item.data(QtCore.Qt.UserRole)["fullName"]
                )
                cmds.setAttr(attr, self.values_buffer[e])
                cmu.set_key(attr)

            self.refresh_channels_values()
        else:
            pm.displayWarning(
                "Stored buffer has {0} values but selected "
                "channels number is: {1}. Can't paste "
                "values".format(str(len(self.values_buffer)), str(len(items)))
            )

    def refresh_node_list(self):
        """Refresh the channel master node list"""
        current_node = self.node_list_combobox.currentText()
        nodes = cmn.list_channel_master_nodes()
        self.node_list_combobox.clear()
        if not nodes:
            self.clear_all_tabs()
            return
        nodes.reverse()
        self.node_list_combobox.addItems(nodes)
        if current_node and pm.objExists(current_node):
            self._set_active_node(current_node)

    def create_new_node(self):
        """Create a new node

        Returns:
            bool: return false if the dialog is not accepted
        """
        sel = pm.selected()
        new_node_dialog = cmw.CreateChannelMasterNodeDialog(self)
        result = new_node_dialog.exec_()
        if result != QtWidgets.QDialog.Accepted:
            return
        name = new_node_dialog.get_name()
        if name:
            node = cmn.create_channel_master_node(name)
            self.set_active_node(node)
            pm.select(sel)

        else:
            pm.displayWarning("No valid node name!")

    def _set_active_node(self, name):
        """Set the active node

        Args:
            name (str): name of the node
        """
        for i in range(self.node_list_combobox.count()):
            if self.node_list_combobox.itemText(i) == name:
                self.node_list_combobox.setCurrentIndex(i)
                break

    def set_active_node(self, name):
        """Refresh list and Set the active node

        Args:
            name (str): name of the node
        """
        self.refresh_node_list()
        self._set_active_node(name)

    def add_tab(self, name=None):
        """Add new tab to the channel master

        Returns:
            QTableWidget: the   table in the newtab
        """

        if not self.get_current_node():
            pm.displayWarning("Custom tab need a node to be stored")
            return

        if not name:
            new_tab_dialog = cmw.CreateChannelMasterTabDialog(self)
            result = new_tab_dialog.exec_()
            if result != QtWidgets.QDialog.Accepted:
                return
            name = new_tab_dialog.get_name()

        if name:
            name = self.check_tab_name(name)
            new_table = cmw.ChannelTable(None, self)
            self.tab_widget.addTab(new_table, name)
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
            # self.save_node_data()
            return new_table
        else:
            pm.displayWarning("No valid tab name!")

    def duplicate_tab(self):
        """Duplicate the current tab"""
        table = self.get_current_table()
        cur_idx = self.tab_widget.currentIndex()
        name = self.tab_widget.tabText(cur_idx) + "_copy"
        name = self.check_tab_name(name)
        if table:
            config = table.get_table_config()
            new_table = self.add_tab(name)
            new_table.set_table_config(config, self.namespace)
            # self.save_node_data()

    def delete_tab(self):
        """Delete the current tab"""
        cur_idx = self.tab_widget.currentIndex()
        if cur_idx >= 1:
            button_pressed = QtWidgets.QMessageBox.question(
                self, "Delete Tab", "Confirm Delete Tab?"
            )
            if button_pressed == QtWidgets.QMessageBox.Yes:
                page = self.tab_widget.widget(cur_idx)
                self.tab_widget.removeTab(cur_idx)
                page.deleteLater()
                # self.save_node_data()
        else:
            pm.displayWarning("Main Tab Can't be deleted!")

    def clear_all_tabs(self):
        """clear all tabs but doesn't delete it from the node.
        Main tab is not cleared
        """
        count = self.tab_widget.count()
        for i in reversed(range(count)):
            if i >= 1:
                page = self.tab_widget.widget(i)
                self.tab_widget.removeTab(i)
                page.deleteLater()

    def check_tab_name(self, name):
        """Check if the tab name is unique and add an index if not

        Args:
            name (str): Name to check

        Returns:
            str: unique name after check
        """
        init_name = name
        names = []
        for i in range(self.tab_widget.count()):
            names.append(self.tab_widget.tabText(i))
        i = 1
        while name in names:
            name = init_name + str(i)
            i += 1

        return name

    def rename_tab(self):
        """Rename the tab text

        Returns:
            bool: False if name not accepted
        """
        cur_idx = self.tab_widget.currentIndex()
        if cur_idx >= 1:
            new_tab_dialog = cmw.CreateChannelMasterTabDialog(self)
            result = new_tab_dialog.exec_()
            if result != QtWidgets.QDialog.Accepted:
                return
            name = new_tab_dialog.get_name()
            if name:
                name = self.check_tab_name(name)
                self.tab_widget.setTabText(cur_idx, name)
                # self.save_node_data()

            else:
                pm.displayWarning("No valid tab name!")
        else:
            pm.displayWarning("Main Tab Can't be renamed!")

    def add_channels_to_current_tab(self):
        """Add selected channel from the channel box

        Returns:
            bool: None
        """
        # check that main tab is not edited
        cur_idx = self.tab_widget.currentIndex()
        if cur_idx >= 1:
            # selected_channels = attribute.getSelectedChannels()
            selected_channels = attribute.get_selected_channels_full_path()
            if not selected_channels:
                return

            # get table config
            table = self.get_current_table()
            config = table.get_table_config()

            for ch in selected_channels:
                # get channel data
                ch_parts = ch.split(".")
                ch_config = cmu.get_single_attribute_config(
                    ch_parts[0], ch_parts[1]
                )

                # check if channel is already in the table
                ch_name = ch_config["fullName"]
                if ch_name not in config["channels"]:
                    # add channel to config
                    config["channels"].append(ch_name)
                    config["channels_data"][ch_name] = ch_config
                else:
                    pm.displayWarning("{} already in table!".format(ch))

            # update table with new config
            table.set_table_config(config, self.namespace)
            # self.save_node_data()
        else:
            pm.displayWarning("Main Tab Can't be Edited!")

    def remove_selected_channels(self):
        """Remove selected channels from the current channel master table"""
        # check that main tab is not edited
        cur_idx = self.tab_widget.currentIndex()
        if cur_idx >= 1:
            # get table config
            table = self.get_current_table()
            config = table.get_table_config()

            # promp before remove the channel
            button_pressed = QtWidgets.QMessageBox.question(
                self, "Remove Channels", "Confirm Remove Selected Channels?"
            )
            if button_pressed == QtWidgets.QMessageBox.Yes:

                # get keys to remove
                for item in table.selectedItems():
                    fullName = item.data(QtCore.Qt.UserRole)["fullName"]
                    pm.displayInfo("Removed channel: {}".format(fullName))
                    config["channels"].remove(fullName)
                    config["channels_data"].pop(fullName, None)

                # update table with new config
                table.set_table_config(config)
                # self.save_node_data()
        else:
            pm.displayWarning("Main Tab Can't be Edited!")

    def get_table_all_hosts(self, table, *args):
        """Get the ctl host for a given table

        Args:
            table (obj): table
            *args: Description

        Returns:
            TYPE: Description
        """
        ctls = []
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            attr_config = item.data(QtCore.Qt.UserRole)
            ctls.append(attr_config["ctl"])
        return ctls

    def get_all_hosts(self, *args):
        """Get all ctl host from all the table in channel master

        Args:
            *args: Description

        Returns:
            TYPE: Description
        """
        all_ctls = []
        for t in self.get_all_tables():
            all_ctls += self.get_table_all_hosts(t)
        return all_ctls

    def get_current_table_all_hosts(self, *args):
        """Get current active table all ctl hosts

        Args:
            *args: Description

        Returns:
            TYPE: Description
        """
        table = self.get_current_table()
        return self.get_table_all_hosts(table)

    def select_current_table_all_hosts(self, *args):
        """Select current active table all ctl hosts

        Args:
            *args: Description
        """
        pm.select(self.get_current_table_all_hosts())

    def select_all_hosts(self, *args):
        """Select all ctl host from all tabs in Channel Master

        Args:
            *args: Description
        """
        pm.select(self.get_all_hosts())


def openChannelMaster(*args):
    return pyqt.showDialog(ChannelMaster, dockable=True)


class channelOrderDialog(QtWidgets.QDialog):

    """Dialog to edit table channel order"""

    def __init__(self, parent, table):
        super(channelOrderDialog, self).__init__(parent)

        self.setWindowTitle("Channel Order")
        self.setMinimumWidth(220)
        self.setWindowFlags(
            self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
        )
        self.table = table
        self.table_config = self.table.get_table_config()
        self.channels = self.table_config["channels"]

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.channel_list_qlist = QtWidgets.QListWidget()
        self.channel_list_qlist.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.channel_list_qlist.addItems(self.channels)
        self.channel_list_qlist.setDragDropOverwriteMode(True)
        self.channel_list_qlist.setDragDropMode(
            QtWidgets.QAbstractItemView.InternalMove
        )
        self.channel_list_qlist.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.channel_list_qlist.setAlternatingRowColors(True)

        self.apply_btn = QtWidgets.QPushButton("Apply")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")

    def apply_channel_order(self):
        qlist = self.channel_list_qlist
        items = [str(qlist.item(i).text()) for i in range(qlist.count())]
        self.table_config["channels"] = items
        self.table.set_table_config(self.table_config)
        self.close()
        self.deleteLater()

    def create_layout(self):
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.cancel_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)
        main_layout.addWidget(self.channel_list_qlist)
        main_layout.addLayout(button_layout)

    def create_connections(self):
        self.cancel_btn.clicked.connect(self.close)
        self.apply_btn.clicked.connect(self.apply_channel_order)


if __name__ == "__main__":

    from mgear.animbits import channel_master_utils
    from mgear.animbits import channel_master_widgets
    from mgear.animbits import channel_master

    import sys

    if sys.version_info[0] == 2:
        reload(channel_master_utils)
        reload(channel_master_widgets)
        reload(channel_master)
    else:
        importlib.reload(channel_master_utils)
        importlib.reload(channel_master_widgets)
        importlib.reload(channel_master)

    start = timeit.default_timer()

    ctl = pm.selected()[0].name()
    attrs = channel_master_utils.get_attributes_config(ctl)

    pyqt.showDialog(
        partial(channel_master.ChannelMaster, attrs), dockable=True
    )

    end = timeit.default_timer()
    timeConsumed = end - start
    print("{} time elapsed running".format(timeConsumed))
