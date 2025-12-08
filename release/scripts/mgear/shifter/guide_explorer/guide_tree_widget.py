from mgear.vendor.Qt import QtCore, QtWidgets, QtGui

import importlib
import logging
from dataclasses import dataclass
from functools import partial
from typing import Any, List, Optional

from maya.api import OpenMaya as om

from mgear import shifter
from mgear.core import callbackManager as cb

from mgear.shifter import guide_manager
from mgear.shifter import utils as shifter_utils
from mgear.shifter.guide_explorer import guide_tree_widget_items
from mgear.shifter.guide_explorer.models import ShifterComponent

from mgear.compatible import compatible_comp_dagmenu

importlib.reload(shifter_utils)
importlib.reload(guide_tree_widget_items)

logger = logging.getLogger("Guide Explorer - Tree Widget")

DATA_ROLE = QtCore.Qt.UserRole + 1

ATTRS_GUIDE = ["rig_name"]
ATTRS_COMP  = ["comp_name", "comp_side", "comp_index"]


class GuideTreeWidget(QtWidgets.QTreeWidget):
    """
    Tree widget displaying the active mGear guide and its components.

    Supports building, unbuilding, duplicating, mirroring, deleting,
    and adding components through a context menu or keyboard shortcuts.
    Also integrates with a Component Manager dialog for creating new components.

    :ivar _guide: Cached guide root or query result from the scene.
    :ivar component_manager: Dialog used for selecting and creating components.
    """
    labelsUpdated = QtCore.Signal()
    selectionPayloadRenamed = QtCore.Signal()

    def __init__(self, guide=None):
        """
        Initialize the tree widget and connect actions and signals.

        :param guide: Optional initial guide reference to populate the tree.
        :return: None
        """
        super(GuideTreeWidget, self).__init__()

        self._attr_cb_manager = cb.CallbackManager()
        self._selection_cb_manager = cb.CallbackManager()
        self._node_to_item = {}
        self._uuid_to_item = {}
        self._guide = guide
        self.component_manager = None

        self._block_scene_selection_sync = False
        self._scene_sync_enabled = False
        self._scene_callbacks_active = False

        self._node_added_cb_id = None
        self._node_removed_cb_id = None

        # -- This part is critical for the callbacks slowing down
        # -- when building and importing
        self._pending_scene_refresh = False
        self._node_added_timer = QtCore.QTimer(self)
        self._node_added_timer.setSingleShot(True)
        self._node_added_timer.timeout.connect(self._process_pending_scene_refresh)

        self.add_actions()
        self.create_widgets()
        self.create_connections()

    def add_actions(self) -> None:
        """
        Create QAction instances and register them on the widget.

        Actions are also added to the widget so that their shortcuts remain
        active even when the context menu is closed.

        :return: None
        """
        self.refresh_action = QtWidgets.QAction("Refresh", self)
        self.refresh_action.setShortcut(QtGui.QKeySequence("R"))
        self.refresh_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        self.mirror_component_action = QtWidgets.QAction("Mirror", self)

        self.build_action = QtWidgets.QAction("Build", self)
        self.build_action.setShortcut(QtGui.QKeySequence("Ctrl+B"))
        self.build_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        self.unbuild_action = QtWidgets.QAction("Unbuild", self)
        self.unbuild_action.setShortcut(QtGui.QKeySequence("Ctrl+U"))
        self.unbuild_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        self.delete_action = QtWidgets.QAction("Delete", self)
        self.delete_action.setShortcut(QtGui.QKeySequence("Del"))
        self.delete_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        self.guide_visibility_action = QtWidgets.QAction("Guide Visibility", self)
        self.guide_visibility_action.setShortcut(QtGui.QKeySequence("H"))
        self.guide_visibility_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        self.ctrl_visibility_action = QtWidgets.QAction("Control Visibility", self)
        self.ctrl_visibility_action.setShortcut(QtGui.QKeySequence("C"))
        self.ctrl_visibility_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        self.joint_visibility_action = QtWidgets.QAction("Joint Visibility", self)
        self.joint_visibility_action.setShortcut(QtGui.QKeySequence("J"))
        self.joint_visibility_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        self.select_component_action = QtWidgets.QAction("Select Component", self)
        self.select_component_action.setShortcut(QtGui.QKeySequence("F"))
        self.select_component_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        self.update_component_type_action = QtWidgets.QAction("Update Component Type", self)
        self.update_component_type_action.setShortcut(QtGui.QKeySequence("Ctrl+U"))
        self.update_component_type_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        # -- Register actions on the dialog so their shortcuts stay active.
        # -- Without this, actions only exist in the context menu and
        # -- their shortcuts will not trigger unless the menu is open.
        self.addAction(self.refresh_action)
        self.addAction(self.build_action)
        self.addAction(self.unbuild_action)
        self.addAction(self.delete_action)
        self.addAction(self.guide_visibility_action)
        self.addAction(self.ctrl_visibility_action)
        self.addAction(self.joint_visibility_action)
        self.addAction(self.select_component_action)
        self.addAction(self.update_component_type_action)

    def create_widgets(self) -> None:
        """
        Create and configure the tree columns, header, and context menu policy.

        The tree uses two columns: component name and component type.
        The header is hidden for a cleaner look but retains stretch behavior.

        :return: None
        """
        self.setColumnCount(2)
        self.setIndentation(10)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        header = self.header()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(60)

        # -- Make columns follow the widget width:
        # -- Component name stretches
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        # -- Type hugs content
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)

        # -- Hide the header after setting modes
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.viewport().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def create_connections(self) -> None:
        """
        Connect UI signals to their handlers and wire actions to slots.

        Includes double-click selection, context menu handling, and all
        action triggers such as build, unbuild, mirror, delete and selection.

        :return: None
        """
        self.customContextMenuRequested.connect(self.show_context_menu)

        self.build_action.triggered.connect(self.on_build_action_clicked)
        self.unbuild_action.triggered.connect(self.on_unbuild_action_clicked)
        self.refresh_action.triggered.connect(self.on_refresh_action_clicked)
        self.mirror_component_action.triggered.connect(self.on_mirror_action_clicked)
        self.delete_action.triggered.connect(self.on_delete_action_clicked)

        self.guide_visibility_action.triggered.connect(self.on_guide_visibility_action_clicked)
        self.ctrl_visibility_action.triggered.connect(self.on_control_visibility_action_clicked)
        self.joint_visibility_action.triggered.connect(self.on_joint_visibility_action_clicked)

        self.select_component_action.triggered.connect(self.on_select_component_action_clicked)

        self.update_component_type_action.triggered.connect(self.on_update_component_type_action_clicked)

    def on_build_action_clicked(self) -> None:
        """
        Build the rig from the current selection context.

        If the root item named "guide" is selected, the entire guide is built.
        If component items are selected, their corresponding roots are selected
        and provided to mGear Shifter for ``buildFromSelection``.

        :return: None
        """
        selection: List[str] = []

        # -- Get the UI selection
        items = self.selectedItems()
        for item in items:
            comp_data = item.data(0, DATA_ROLE)

            if hasattr(comp_data, "root_name"):
                node = comp_data.root_name
            else:
                node = comp_data

            node_name = node.name() if hasattr(node, "name") else str(node)
            selection.append(node_name)

        # -- Select all our items
        shifter_utils.select_items(selection)

        # -- Do the rig build
        rig = shifter.Rig()
        rig.buildFromSelection()

    def on_unbuild_action_clicked(self) -> None:
        """
        Unbuild the current rig, if present.

        The function finds any node with the attribute ``*.is_rig`` and deletes
        the owning rig transform. Logs an error if no rig is found.

        :return: None
        """
        # -- Get the rig in the scene
        rig = shifter_utils.get_rig()

        if not rig:
            logger.error("No valid rig has been found in the scene to unbuild.")
            return

        # -- Delete the rig
        rig_name = rig[0].node().name()
        shifter_utils.delete_nodes([rig_name])

    def on_refresh_action_clicked(self) -> None:
        """
        Refresh the tree from the current scene.

        :return: None
        """
        self.get_guide_from_scene()

    def on_mirror_action_clicked(self) -> None:
        """
        Mirror the selected component guide.

        Only the last selected item is considered. The guide root is resolved
        and duplicated with mirroring enabled. The tree is refreshed afterward
        via callbacks.

        :return: None
        """
        items = self.selectedItems()

        if not items:
            return

        # -- Only consider the last selected item for now
        item = items[-1]
        comp_data = item.data(0, DATA_ROLE)

        if not isinstance(comp_data, ShifterComponent):
            logger.warning("Mirror is only supported for component items.")
            return

        # -- Resolve the component root as a PyNode
        try:
            root_node = shifter_utils.node_from_uuid(uuid=comp_data.uuid)
        except Exception:
            try:
                root_node = shifter_utils.node_from_name(name=comp_data.root_name)
            except Exception:
                logger.warning(f"Could not resolve component root for mirroring: {comp_data.full_name}")
                return

        # -- Mirror the guide
        guide = shifter.guide.Rig()
        guide.duplicate(root_node, True)

    def on_delete_action_clicked(self) -> None:
        """
        Delete selected guide or component roots from the scene.

        The function resolves node names from the selection, converts component
        items to their root nodes, and passes the list to a delete helper.
        The tree is refreshed afterward.

        :return: None
        """
        selection: List[str] = []

        # -- Get the UI selection
        items = self.selectedItems()
        if not items:
            logger.warning("No item in the UI has been selected for deletion.")
            return

        for item in items:
            comp_data = item.data(0, DATA_ROLE)

            # -- Component roots
            if hasattr(comp_data, "root_name"):
                node = comp_data.root_name
            else:
                # -- Root guide node
                node = comp_data

            selection.append(node)

        # -- Do the deletion of the node
        shifter_utils.delete_nodes(selection)

        self.get_guide_from_scene()

    def on_guide_visibility_action_clicked(self) -> None:
        """
        Toggle the visibility of the selected guide or component roots.

        For each selected tree item, resolves the stored DATA_ROLE data:
        - If it is a ShifterComponent, uses its root node.
        - Otherwise treats the data as a node-like object.

        :return: None
        """
        items = self.selectedItems()
        # -- Fail/exit early
        if not items:
            return

        for item in items:
            comp_data = item.data(0, DATA_ROLE)

            if isinstance(comp_data, ShifterComponent):
                node = shifter_utils.node_from_uuid(uuid=comp_data.uuid)
            else:
                node = shifter_utils.node_from_name(name=comp_data)

            visibility = node.visibility.get()
            node.visibility.set(not visibility)

    def on_control_visibility_action_clicked(self) -> None:
        """
        Toggle the rig control visibility.

        Resolves the active rig via 'shifter_utils.get_rig()', then flips the
        'ctl_vis' attribute on the rig root if present.

        :return: None
        """
        rig_list = shifter_utils.get_rig()
        rig = rig_list[0].node() if rig_list and hasattr(rig_list[0], "node") else None

        if not rig:
            return

        ctrl_visibility = rig.ctl_vis.get()
        rig.ctl_vis.set(not ctrl_visibility)

    def on_joint_visibility_action_clicked(self) -> None:
        """
        Toggle the rig joint visibility.

        Resolves the active rig via 'shifter_utils.get_rig()', then flips the
        'jnt_vis' attribute on the rig root if present.

        :return: None
        """
        rig_list = shifter_utils.get_rig()
        rig = rig_list[0].node() if rig_list and hasattr(rig_list[0], "node") else None

        if not rig:
            return

        jnt_visibility = rig.jnt_vis.get()
        rig.jnt_vis.set(not jnt_visibility)

    def on_select_component_action_clicked(self) -> None:
        """
        Select the scene nodes that correspond to the selected tree items.

        Builds a list of node names by reading DATA_ROLE:
        - If a ShifterComponent is stored, resolves it via UUID.
        - Otherwise treats the payload as a node-like object.

        :return: None
        """
        items = self.selectedItems()
        selection_list: List[str] = []

        for item in items:
            comp_data = item.data(0, DATA_ROLE)

            if hasattr(comp_data, "root_name"):
                node = shifter_utils.node_from_uuid(uuid=comp_data.uuid)
            else:
                node = comp_data

            selection_list.append(node)

        shifter_utils.select_items(selection_list, replace=True)

    def get_guide_from_scene(self) -> None:
        """
        Query the scene for the active mGear guide and populate the tree.

        Clears the tree, resolves the guide, rig name and component metadata,
        then creates a root item followed by child items for each component.
        The root item is selected by default.

        :return: None
        """
        self._attr_cb_manager.removeAllManagedCB()
        self.clear()
        self._node_to_item.clear()
        self._uuid_to_item.clear()

        self._guide = shifter_utils.get_guide()
        if not self._guide:
            logger.warning("No Guide has been found in the scene.")
            return

        guide_name = self._guide[0].node()
        rig_name = shifter_utils.get_rig_name(guide_name)
        components = shifter_utils.get_components(guide_name)

        root_item = guide_tree_widget_items.GuideTreeWidgetItem(parent=self,
                                                                rig_name=rig_name)

        root_item.setText(0, f"guide ({rig_name})")
        root_item.setData(0, QtCore.Qt.UserRole, "guide")
        root_item.setData(0, DATA_ROLE, guide_name)
        self._node_to_item[str(guide_name)] = root_item

        self._create_attr_callbacks(str(guide_name), ATTRS_GUIDE)

        for comp in components:

            root_node = comp.node().name()
            comp_type = comp.comp_type.get()
            comp_name = comp.comp_name.get()
            comp_side = comp.comp_side.get()
            comp_index = comp.comp_index.get()
            root_uuid = shifter_utils.uuid_from_node(node=root_node)

            full_name = f"{comp_name}_{comp_side}{comp_index}"

            comp_item = guide_tree_widget_items.ComponentTreeWidgetItem(root_item,
                                                                        full_name,
                                                                        comp_type)
            comp_item.setData(0, QtCore.Qt.UserRole, root_node)
            comp_item.setData(0, DATA_ROLE, ShifterComponent(full_name=full_name,
                                                             comp_type=comp_type,
                                                             root_name=root_node,
                                                             side=comp_side,
                                                             index=comp_index,
                                                             uuid=root_uuid))

            self._node_to_item[root_node] = comp_item
            self._uuid_to_item[root_uuid] = comp_item
            # -- watch naming attrs on this component root
            self._create_attr_callbacks(root_node, ATTRS_COMP)

        # -- Select root so settings show on first open
        self.setCurrentItem(root_item)

    def _create_attr_callbacks(self, node_name: str, short_attrs: list[str]) -> None:
        """
        Register attribute change callbacks for the given node and attributes.

        :param node_name: Name of the node to watch.
        :param short_attrs: List of attribute names to track.
        :return: None
        """
        # -- Create a unique name so this manager can cleanly remove them later
        callback_namespace = f"GuideOverview.{node_name}"
        for attr in short_attrs:
            fn = partial(self._on_attr_changed, node_name, attr)
            self._attr_cb_manager.attributeChangedCB(f"{callback_namespace}.{attr}",
                                                     fn,
                                                     node_name,
                                                     [attr])

    def _register_node_added_callback(self) -> None:
        """
        Register DG node-added and node-removed callbacks.

        Used so the tree can refresh when new guide or component nodes
        are created or deleted.

        :return: None
        """
        if self._node_added_cb_id is None:
            self._node_added_cb_id = om.MDGMessage.addNodeAddedCallback(self._on_node_added,
                                                                        "transform")

        if self._node_removed_cb_id is None:
            self._node_removed_cb_id = om.MDGMessage.addNodeRemovedCallback(self._on_node_removed,
                                                                            "transform")

    def _on_attr_changed(self, node_name: str, attr: str) -> None:
        """
        Handle guide or component attribute changes and refresh the tree item.

        :param node_name: Name of the node whose attribute changed.
        :param attr: Short attribute name that triggered the callback.
        :return: None
        """
        item = self._node_to_item.get(node_name)
        if not item:
            return

        data = item.data(0, DATA_ROLE)

        if isinstance(data, ShifterComponent):

            node = shifter_utils.node_from_uuid(uuid=data.uuid)

            comp_name = node.attr("comp_name").get()
            comp_side = node.attr("comp_side").get()
            comp_index = node.attr("comp_index").get()
            comp_type = node.attr("comp_type").get()

            new_full_name = f"{comp_name}_{comp_side}{comp_index}"
            new_node_name = node.name()

            self.blockSignals(True)

            item.setText(0, new_full_name)
            item.setData(0, DATA_ROLE, ShifterComponent(full_name=new_full_name,
                                                        comp_type=comp_type,
                                                        root_name=new_node_name,
                                                        side=comp_side,
                                                        index=comp_index,
                                                        uuid=data.uuid))

            # -- Update the node name mapping if the transform was renamed
            if new_node_name != node_name:
                self._node_to_item[new_node_name] = item

            self.blockSignals(False)

            self.labelsUpdated.emit()
            if self.currentItem() is item:
                self.selectionPayloadRenamed.emit()

        # -- Either guide or component
        else:

            node = shifter_utils.node_from_name(name=data)

            rig_name = node.attr("rig_name").get()

            self.blockSignals(True)
            item.setText(0, f"guide ({rig_name})")
            self.blockSignals(False)

            self.labelsUpdated.emit()
            if self.currentItem() is item:
                self.selectionPayloadRenamed.emit()

    def _on_scene_selection_changed(self, *args: Any) -> None:
        """
        Sync the tree selection from the current Maya selection.

        Called whenever the Maya selection changes.

        :return: None
        """
        if not self._scene_sync_enabled or self._block_scene_selection_sync:
            return

        selection = shifter_utils.get_selection()
        if not selection:
            return

        # -- Take the last selected object
        last_item = selection[-1]

        # -- Try to find the component root for this object
        comp_root = shifter_utils.find_component_root(last_item)
        if not comp_root:
            # Might be the guide root itself
            try:
                node_name = last_item.name()
            except Exception:
                node_name = str(last_item)

            item = self._node_to_item.get(node_name)
            if not item:
                return
        else:
            # -- Use uuid mapping if possible, more robust and less prone to name clashes.
            root_node_name = comp_root.node().name()
            try:
                root_uuid = shifter_utils.uuid_from_node(node=root_node_name)
                item = self._uuid_to_item.get(root_uuid)
            except Exception:
                item = self._node_to_item.get(root_node_name)

            if not item:
                return

        # -- Update tree selection without causing extra noise
        self._block_scene_selection_sync = True
        try:
            self.clearSelection()
            self.setCurrentItem(item)
            self.scrollToItem(item)
            parent = item.parent()
            if parent:
                self.expandItem(parent)
        finally:
            self._block_scene_selection_sync = False

    def _on_node_added(self, mobj: om.MObject, clientData: Any = None) -> None:
        """
        DG callback when a transform node is created.

        This does not inspect custom attributes because the callback fires
        before mGear has finished adding them. Instead, it schedules a
        debounced tree refresh if the widget is visible and a guide is
        currently loaded.

        :param mobj: Maya object that was added.
        :param clientData: Arbitrary client data passed by Maya.
        :return: None
        """
        # -- Only care while the widget is actually visible
        if not self.isVisible():
            return

        self._pending_scene_refresh = True

        # -- Restart the debounce timer. If more nodes are added before the timeout,
        # -- this will be called again and the timer will be restarted.
        self._node_added_timer.start(50)

    def _on_node_removed(self, mobj: om.MObject, clientData: Any = None) -> None:
        """
        DG callback when a transform node is deleted.

        Schedules a debounced tree refresh if the widget is visible.

        :param mobj: Maya object that was removed.
        :param clientData: Arbitrary client data passed by Maya.
        :return: None
        """
        if not self.isVisible():
            return

        self._pending_scene_refresh = True
        self._node_added_timer.start(100)

    def _process_pending_scene_refresh(self) -> None:
        """
        Handle any pending scene refresh requested by the node-added callback.

        Called by the debounce timer once there have been no new nodes added
        for the timer interval.

        :return: None
        """
        if not self._pending_scene_refresh:
            return

        # -- Clear the flag first to avoid accidental loops
        self._pending_scene_refresh = False

        # -- If the widget is no longer visible, skip the refresh
        if not self.isVisible():
            return

        # -- Rebuild the tree from the scene
        self.get_guide_from_scene()

    def on_update_component_type_action_clicked(self) -> None:
        """
        Update the component type for the selected component using the DAG menu.

        Ensures a single ShifterComponent is selected, selects the component
        in the scene if needed, calls the compatibility helper, then rebuilds
        the tree and attempts to reselect the updated component.

        :return: None
        """
        items = self.selectedItems()
        # -- If nothing is selected, do nothing.
        if not items:
            return

        # -- Currently on considering single item selection
        # -- Get the last selected item
        data = items[-1].data(0, DATA_ROLE)

        # -- Ensure it is a shifter component object
        if not isinstance(data, ShifterComponent):
            return

        selected_uuid = data.uuid

        # -- Ensure that we have something selected in order for something to be
        # -- picked up by the command
        if not self._scene_sync_enabled:
            try:
                node = shifter_utils.node_from_uuid(uuid=selected_uuid)
            except Exception:
                logger.warning(f"Could not resolve node from uuid: {selected_uuid}")
                return

            shifter_utils.select_items(items=[node])

        # -- Update the component type
        compatible_comp_dagmenu.update_component_type_and_update_guide_with_dagmenu()

        # -- Rebuild the tree so UI/model and callbacks are correct
        self.get_guide_from_scene()

        self._block_scene_selection_sync = True
        try:
            self.clearSelection()
            new_item = self._node_to_item.get(data.root_name)
            print(new_item)
            if not new_item:
                return

            self.setCurrentItem(new_item)
            new_item.setSelected(True)
        finally:
            self._block_scene_selection_sync = False

    def _enable_scene_callbacks(self) -> None:
        """
        Ensure scene callbacks are registered.

        Only called when the widget becomes visible.

        :return: None
        """
        if self._scene_callbacks_active:
            return

        # -- Selection changed
        self._selection_cb_manager.selectionChangedCB("GuideOverview.Selection",
                                                      self._on_scene_selection_changed)

        # -- Node added, node removed
        self._register_node_added_callback()
        self._scene_callbacks_active = True

    def _disable_scene_callbacks(self) -> None:
        """
        Remove scene callbacks.

        Called when the widget is hidden or closed.

        :return: None
        """
        if not self._scene_callbacks_active:
            return

        # -- Stop any pending node-added refresh
        self._node_added_timer.stop()
        self._pending_scene_refresh = False

        # -- Remove selection callbacks
        self._selection_cb_manager.removeAllManagedCB()

        # -- Remove node-added callback
        if self._node_added_cb_id is not None:
            try:
                om.MMessage.removeCallback(self._node_added_cb_id)
            except Exception:
                pass
            self._node_added_cb_id = None

        if self._node_removed_cb_id is not None:
            try:
                om.MMessage.removeCallback(self._node_removed_cb_id)
            except Exception:
                pass
            self._node_removed_cb_id = None

        self._scene_callbacks_active = False

    def show_context_menu(self, point: QtCore.QPoint) -> None:
        """
        Show the context menu for the tree.

        Builds the right-click menu with guide and component actions, then opens it
        at the cursor position. The incoming point is in the viewport coordinate
        system and is mapped to global screen space.

        :param point: Position of the click in viewport coordinates.
        :return: None
        """
        has_guide = bool(self._guide) and hasattr(self._guide[0], "node") and self._guide[0].node()
        rig_list = shifter_utils.get_rig()
        has_rig = bool(rig_list) and hasattr(rig_list[0], "node") and rig_list[0].node()

        menu = QtWidgets.QMenu(self)

        menu.addAction(self.build_action)
        menu.addAction(self.unbuild_action)
        menu.addSeparator()

        # -- Visibility actions
        visibility_actions: List[QtWidgets.QAction] = []

        if has_guide:
            visibility_actions.append(self.guide_visibility_action)

        if has_rig:
            visibility_actions.append(self.ctrl_visibility_action)
            visibility_actions.append(self.joint_visibility_action)

        for action in visibility_actions:
            menu.addAction(action)

        # -- Add separator only if at least one visibility action exists
        if visibility_actions:
            menu.addSeparator()

        menu.addAction(self.mirror_component_action)
        menu.addSeparator()
        menu.addAction(self.delete_action)
        menu.addSeparator()
        menu.addAction(self.select_component_action)
        menu.addSeparator()
        menu.addAction(self.refresh_action)
        menu.addSeparator()
        menu.addAction(self.update_component_type_action)

        menu.exec_(self.viewport().mapToGlobal(point))

    def clear_items(self) -> None:
        """
        Clear all items and associated callbacks from the tree.

        Removes all managed callbacks and resets the internal node-to-item maps.

        :return: None
        """
        # -- Attribute callbacks on guide and components
        self._attr_cb_manager.removeAllManagedCB()

        # -- Clear tree items and maps
        self.clear()
        self._node_to_item.clear()
        self._uuid_to_item.clear()
        self._guide = None

    def teardown(self) -> None:
        """
        Fully tear down the tree widget before the parent UI is closed.

        This disables all scene callbacks and clears all items, mappings
        and attribute callbacks.

        :return: None
        """
        # -- Stop reacting to scene
        self._disable_scene_callbacks()

        # -- Clear tree model and attribute callbacks
        self.clear_items()

    def showEvent(self, event: QtCore.QEvent) -> None:
        """
        Qt show event handler.

        When the tree becomes visible, enable scene callbacks.

        :param event: Qt show event.
        :return: None
        """
        super().showEvent(event)
        self._enable_scene_callbacks()

    def hideEvent(self, event: QtCore.QEvent) -> None:
        """
        Qt hide event handler.

        When the tree is hidden, disable scene callbacks.

        :param event: Qt hide event.
        :return: None
        """
        self._disable_scene_callbacks()
        super().hideEvent(event)
