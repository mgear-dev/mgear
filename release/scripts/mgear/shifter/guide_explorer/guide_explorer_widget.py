from mgear.vendor.Qt import QtCore, QtWidgets
import logging

from typing import Optional

from mgear.shifter.guide_explorer import guide_tree_widget
from mgear.shifter.guide_explorer.models import ShifterComponent
from mgear.shifter.guide_explorer.utils import TempSelection
from mgear.shifter import guide as shifter_guide
from mgear.shifter import utils as shifter_utils

from mgear import shifter

from mgear.core import pyqt
import mgear.pymaya as pm

logger = logging.getLogger("Guide Explorer")

import importlib
importlib.reload(shifter_utils)


class GuideExplorerWidget(QtWidgets.QWidget):
    """
    Widget displaying an overview of the current mGear guide.

    Provides a split layout with:

    - Left panel: search bar and component tree view.
    - Right panel: displays one of the following:
      - Guide settings when the guide root is selected.
      - Component settings when a component is selected.
      - A placeholder when no selection is active.
    """
    TREE_MIN_WIDTH = 280
    RIGHT_MIN_WIDTH = 420

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """
        Initialize the guide explorer widget.

        :param parent: Optional parent widget.
        :return: None
        """
        super().__init__(parent)

        self.current_widget: Optional[QtWidgets.QWidget] = None
        self.current_key: Optional[str] = None
        self.previous_guide_tab_index: int = 0
        self.previous_comp_tab_index: int = 0
        self.last_split_sizes: List[int] = [340, 700]

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self) -> None:
        """
        Create and configure all child widgets for the guide explorer.

        :return: None
        """
        self.filter_components_line_edit = QtWidgets.QLineEdit(self)
        self.filter_components_line_edit.setClearButtonEnabled(True)
        self.filter_components_line_edit.setPlaceholderText("<Search components>")

        self.sync_checkbox = QtWidgets.QCheckBox("Sync Selection")

        self.guide_tree_widget = guide_tree_widget.GuideTreeWidget()

        self.left_widget = QtWidgets.QWidget(self)
        self.right_widget = QtWidgets.QWidget(self)

        self.right_scroll = QtWidgets.QScrollArea(self)
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.right_scroll.setWidget(self.right_widget)

        self.placeholder_label = QtWidgets.QLabel("Select a component")
        self.placeholder_label.setAlignment(QtCore.Qt.AlignCenter)

    def create_layout(self) -> None:
        """
        Create the main layout for the guide explorer.

        :return: None
        """
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(3, 3, 3, 3)
        main_layout.setSpacing(6)

        horizontal_layout = QtWidgets.QHBoxLayout()
        horizontal_layout.addWidget(self.filter_components_line_edit)
        horizontal_layout.addWidget(self.sync_checkbox)

        # -- Components tree widget layout
        left_layout = QtWidgets.QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addLayout(horizontal_layout)
        left_layout.addWidget(self.guide_tree_widget)

        self.left_widget.setMinimumWidth(self.TREE_MIN_WIDTH)
        self.left_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                       QtWidgets.QSizePolicy.Expanding)

        self.right_layout = QtWidgets.QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addWidget(self.placeholder_label)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(self.left_widget)
        self.splitter.addWidget(self.right_scroll)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes(self.last_split_sizes)

        main_layout.addWidget(self.splitter)

    def create_connections(self) -> None:
        """
        Connect widget signals to their corresponding slots.

        :return: None
        """
        self.filter_components_line_edit.textChanged.connect(self.apply_component_filter)

        self.guide_tree_widget.itemSelectionChanged.connect(self.on_selection_changed_clicked)
        self.guide_tree_widget.doubleClicked.connect(self.on_item_double_clicked)
        self.guide_tree_widget.labelsUpdated.connect(self.refresh_widget_titles)
        self.guide_tree_widget.selectionPayloadRenamed.connect(self.refresh_selected_widget)

        self.sync_checkbox.toggled.connect(self.on_sync_checkbox_toggled)

    def on_selection_changed_clicked(self) -> None:
        """
        Update the settings panel based on the current tree selection.

        Displays either the guide settings, component settings or
        a placeholder if nothing is selected.

        :return: None
        """
        items = self.guide_tree_widget.selectedItems()
        if not items:
            self.show_placeholder()
            return

        # -- Stored information when loading in the guide and components
        data = items[-1].data(0, guide_tree_widget.DATA_ROLE)

        # -- Shifter Component Instance
        if isinstance(data, ShifterComponent) and data.root_name:
            self.open_component_widget(data)

            # -- Safe select via the node uuid
            if self.sync_checkbox.isChecked():
                shifter_utils.select_by_uuid(uuid=data.uuid)

            return

        # -- Guide object
        if self._is_pymaya_node(data) or isinstance(data, str):
            self.open_guide_widget(data)

            if self.sync_checkbox.isChecked():
                shifter_utils.select_items(items=[data])
            return

        # -- Default to showing the placeholder if nothing is selected
        self.show_placeholder()

    def on_item_double_clicked(self) -> None:
        """
        Select the single node corresponding to the double-clicked item.

        If sync selection is enabled, this is skipped because selection is
        already driven by single-click.

        :return: None
        """
        # -- No need to do selection as the single click will have done it's job.
        if self.sync_checkbox.isChecked():
            return

        items = self.guide_tree_widget.selectedItems()
        data = items[-1].data(0, guide_tree_widget.DATA_ROLE)

        # -- Component
        if isinstance(data, ShifterComponent):
            shifter_utils.select_by_uuid(uuid=data.uuid)

        # -- Guide
        if self._is_pymaya_node(data) or isinstance(data, str):
            shifter_utils.select_items(items=[data])

    def remember_and_restore_split(self, restore=True) -> None:
        """
        Save or restore the splitter sizes.

        :param restore: If True, restore the last saved sizes.
                        If False, save the current sizes.
        :return: None
        """
        if restore:
            self.splitter.setSizes(self.last_split_sizes)
        else:
            self.last_split_sizes = self.splitter.sizes()

    def clear_right(self) -> None:
        """
        Remove the current panel from the right side and reset related data.

        :return: None
        """
        if self.current_widget:
            self.right_layout.removeWidget(self.current_widget)
            self.current_widget.deleteLater()
            self.current_widget = None
            self.current_key = None

    def set_right_min_width(self, width: int) -> None:
        """
        Set the minimum width for the right panel and its scroll area.

        :param width: Desired minimum width in pixels.
        :return: None
        """
        width = max(self.RIGHT_MIN_WIDTH, int(width))
        self.right_widget.setMinimumWidth(width)
        self.right_scroll.setMinimumWidth(width)

    def clear_right_min_width(self) -> None:
        """
        Reset the minimum width of the right panel to zero.

        :return: None
        """
        self.right_widget.setMinimumWidth(0)
        self.right_scroll.setMinimumWidth(0)

    def remove_placeholder(self) -> None:
        """
        Remove the placeholder label from the right panel if it exists.

        :return: None
        """
        if self.placeholder_label:
            self.placeholder_label.hide()

    def ensure_placeholder(self) -> None:
        """
        Ensure that the placeholder label exists and is attached to the right panel.

        :return: None
        """
        if self.placeholder_label.parent() is None:
            self.placeholder_label.setParent(self.right_widget)
            self.right_layout.addWidget(self.placeholder_label)

        self.placeholder_label.show()

    def show_placeholder(self) -> None:
        """
        Clear the right panel and display the placeholder label.

        :return: None
        """
        self.clear_right()
        self.clear_right_min_width()
        self.ensure_placeholder()

    def on_panel_close_button(self, panel: QtWidgets.QWidget) -> None:
        """
        Ensure that closing an embedded settings panel restores the placeholder.

        :param panel: Guide or component settings widget that has a close_button.
        """
        # -- Most mGear settings panels expose a 'close_button' attribute.
        close_button = getattr(panel, "close_button", None)
        if isinstance(close_button, QtWidgets.QPushButton):
            close_button.clicked.connect(self.show_placeholder)

    def open_guide_widget(self, data=None) -> None:
        """
        Build and display the guide settings panel on the right side.

        :param data: ShifterComponent describing the selected component.
        :return: None
        """
        self.remember_and_restore_split(restore=False)

        if self.current_key == "__GUIDE__" and self.current_widget:
            self.previous_guide_tab_index = self.current_widget.tabs.currentIndex()

        if data is None:
            item = self.guide_tree_widget.topLevelItem(0)
            data = item.data(0, guide_tree_widget.DATA_ROLE) if item else None

        # -- Temporarily select the guide root only while building the panel
        # -- If we do not select the item then the data is not loaded in.
        with TempSelection(data):
            panel = shifter_guide.GuideSettings(parent=self.right_widget)

        panel.setWindowFlags(QtCore.Qt.Widget)
        panel.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        panel.setObjectName("guide_settings_panel")

        self.on_panel_close_button(panel=panel)

        panel_min_width = max(panel.minimumSizeHint().width(), panel.sizeHint().width())
        self.set_right_min_width(panel_min_width)

        # -- Clean widgets and ensure the placeholder label is removed
        self.clear_right()
        self.remove_placeholder()
        self.current_widget = panel
        self.current_key = "__GUIDE__"
        self.right_layout.addWidget(panel)

        # -- Set the last known index for the guide
        panel.tabs.setCurrentIndex(self.previous_guide_tab_index)

        self.remember_and_restore_split(restore=True)

    def open_component_widget(self, comp: ShifterComponent) -> None:
        """
        Build and display the component settings panel on the right side.

        :param comp: ShifterComponent describing the selected component.
        :return: None
        """
        # -- If leaving the guide, remember current tab index
        if self.current_key == "__GUIDE__" and self.current_widget and hasattr(self.current_widget, "tabs"):
            self.previous_guide_tab_index = self.current_widget.tabs.currentIndex()

        # -- No need to rebuild if this component is already shown
        if self.current_key == comp.full_name and self.current_widget:
            return

        if self.current_widget and self.current_key != "__GUIDE__":
            self.previous_comp_tab_index = self.current_widget.tabs.currentIndex()

        self.remember_and_restore_split(restore=False)

        # -- Resolve the scene node from the UUID
        try:
            root_node = pm.ls(comp.uuid, uuid=True)[0]
        except Exception:
            logger.warning(f"Could not resolve component root from uuid '{comp.uuid}' for component '{comp.full_name}' "
                           f"The node may have been deleted or renamed.")
            self.show_placeholder()
            self.remember_and_restore_split(restore=True)
            return

        # -- Keep the dataclass in sync if the node has been renamed
        if root_node.name() != comp.root_name:
            comp = ShifterComponent(full_name=comp.full_name,
                                    comp_type=comp.comp_type,
                                    root_name=root_node.name(),
                                    side=comp.side,
                                    index=comp.index,
                                    uuid=comp.uuid)

        # -- Import the component guide module and try to get its UI class.
        component_instance = shifter.importComponentGuide(comp.comp_type)
        SettingsCls = getattr(component_instance, "componentSettings", None)
        if SettingsCls is None:
            self.show_placeholder()
            self.remember_and_restore_split(restore=True)
            return

        # -- Temporarily select the component root only while building the panel
        # -- If we do not select the item then the data is not loaded in.
        with TempSelection(comp.root_name):
            panel = SettingsCls(parent=self.right_widget)

        panel.setWindowFlags(QtCore.Qt.Widget)
        panel.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        panel.setObjectName(f"{comp.full_name}_settings")

        self.on_panel_close_button(panel=panel)

        panel_min_width = max(panel.minimumSizeHint().width(), panel.sizeHint().width())
        self.set_right_min_width(panel_min_width)

        self.clear_right()
        self.remove_placeholder()
        self.current_widget = panel
        self.current_key = comp.full_name
        self.right_layout.addWidget(panel)

        # -- Want to get the current tab count as the stored index could be
        # -- Higher than the new component tab count.
        tab_count = panel.tabs.count()
        if self.previous_comp_tab_index >= tab_count:
            self.previous_comp_tab_index = max(0, tab_count - 1)

        panel.tabs.setCurrentIndex(self.previous_comp_tab_index)

        self.remember_and_restore_split(restore=True)

    def apply_component_filter(self, text: str) -> None:
        """
        Filter tree items by name and type using the given search text.

        :param text: Space-separated terms; all must match for an item to stay visible.
        :return: None
        """
        # -- This should always be the guide
        root_item = self.guide_tree_widget.topLevelItem(0)

        if not root_item:
            return

        search_terms = [t.lower() for t in text.strip().split() if t]
        root_item.setHidden(False)
        root_item.setExpanded(True)
        # -- Search all child items in the tree widget
        for i in range(root_item.childCount()):
            item = root_item.child(i)
            comb = f"{item.text(0)} {item.text(1)}".lower()
            item.setHidden(not all(t in comb for t in search_terms))

    def component_exists(self, full_name: str) -> bool:
        """
        Check whether a component with the given full name exists in the tree.

        :param full_name: Full name of the component to look for.
        :return: True if the component is found, otherwise False.
        """
        # -- This is the mGear guide
        root = self.guide_tree_widget.topLevelItem(0)
        if not root:
            return False

        # -- Iterate over all the child items and ensure that the component full name exists
        for i in range(root.childCount()):
            data = root.child(i).data(0, guide_tree_widget.DATA_ROLE)
            if isinstance(data, ShifterComponent) and data.full_name == full_name:
                return True

        return False

    def refresh_selected_widget(self) -> None:
        """
        Reload the panel for the currently selected item.

        Reopens the appropriate settings panel when the selected guide or
        component has changed identity or attributes, ensuring the displayed
        content stays in sync with the scene.

        :return: None
        """
        items = self.guide_tree_widget.selectedItems()
        if not items:
            return

        data = items[-1].data(0, guide_tree_widget.DATA_ROLE)
        if isinstance(data, ShifterComponent):
            self.open_component_widget(data)
        else:
            self.open_guide_widget(data)

    def refresh_widget_titles(self) -> None:
        """
        Refresh the tree view and update the active widget title.

        Ensures renamed guides or components display correctly in both the
        tree and the right-hand panel by repainting the tree viewport and
        updating the current widget's window title if needed.

        :return: None
        """
        # -- Force tree repaint
        self.guide_tree_widget.viewport().update()

        # -- If the current widget is open for a component that got renamed,
        # -- refresh the title or label on that widget
        if self.current_widget and hasattr(self.current_widget, 'setWindowTitle'):
            items = self.guide_tree_widget.selectedItems()
            if items:
                data = items[-1].data(0, guide_tree_widget.DATA_ROLE)
                # -- if a component
                if isinstance(data, ShifterComponent):
                    self.current_widget.setWindowTitle(data.full_name)
                # -- if a guide
                else:
                    self.current_widget.setWindowTitle("Guide Settings")

    def on_sync_checkbox_toggled(self, state: bool) -> None:
        """
        Handle toggling of the 'Sync Selection' checkbox.

        Updates the internal flag on the tree widget that controls whether
        scene selection changes should update the tree selection. The actual
        setting is persisted during teardown, not on each toggle.

        :param state: True if sync selection is enabled, otherwise False.
        :return: None
        """
        self.guide_tree_widget._scene_sync_enabled = state

    def refresh(self) -> None:
        """
        Update the tree to reflect the current scene state.

        Reloads the guide data from the scene and resets the view if the
        previously selected component no longer exists.

        :return: None
        """
        self.guide_tree_widget.get_guide_from_scene()
        if self.current_key and not self.component_exists(self.current_key):
            self.show_placeholder()

    def _is_pymaya_node(self, obj) -> bool:
        """
        Check if the given object behaves like a PyMaya or PyNode instance.

        :param obj: Object to test.
        :return: True if the object has a callable ``name()`` method.
        """
        return hasattr(obj, "name") and callable(getattr(obj, "name", None))

    def _load_settings(self) -> None:
        """
        Load persistent settings for the guide overview widget.

        Restores sync selection state and the component filter text.

        :return: None
        """
        settings = QtCore.QSettings("mgear", "GuideExplorer")

        # -- Sync Selection checkbox
        sync_enabled = settings.value("sync_selection", False, type=bool)
        self.sync_checkbox.setChecked(sync_enabled)
        self.guide_tree_widget._scene_sync_enabled = sync_enabled

        # -- Component filter text
        saved_filter = settings.value("component_filter", "", type=str)
        self.filter_components_line_edit.setText(saved_filter)

        if saved_filter:
            # -- Setting the text will also trigger apply_component_filter
            self.apply_component_filter(saved_filter)

    def _save_settings(self) -> None:
        """
        Save persistent settings for the guide overview widget.

        Called on teardown so we only write once per session.

        :return: None
        """
        settings = QtCore.QSettings("mgear", "GuideExplorer")

        settings.setValue("sync_selection", self.sync_checkbox.isChecked())
        settings.setValue("component_filter", self.filter_components_line_edit.text() or "")

    def showEvent(self, event) -> None:
        """
        Refresh the widget when it becomes visible.

        :param event: Qt show event.
        :return: None
        """
        super(GuideExplorerWidget, self).showEvent(event)
        self.refresh()
        self._load_settings()

    def hideEvent(self, event) -> None:
        """
        Handle widget hide events.

        Persists settings when the widget is hidden.

        :param event: Qt hide event.
        :return: None
        """
        super().hideEvent(event)

        self._save_settings()

    def teardown(self) -> None:
        """
        Clean up callbacks and cached data before closing the widget.

        This removes all managed callbacks and clears the node maps to prevent
        stale references or memory leaks. This is called when we close the UI.

        :return: None
        """
        try:
            self.guide_tree_widget.teardown()
            self._save_settings()
        except Exception:
            pass
