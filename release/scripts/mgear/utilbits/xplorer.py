import tempfile
import os

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import maya.mel as mel

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui

VERSION = "1.0.0"

try:
    from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
except:
    class MayaQWidgetDockableMixin:
        pass


# =============================================================================
# OpenMaya 2.0 Helper Functions for Performance
# =============================================================================

def om_get_mobject(node_path):
    """Get MObject from node path using OpenMaya 2.0"""
    try:
        sel = om2.MSelectionList()
        sel.add(node_path)
        return sel.getDependNode(0)
    except:
        return None


def om_get_dag_path(node_path):
    """Get MDagPath from node path using OpenMaya 2.0"""
    try:
        sel = om2.MSelectionList()
        sel.add(node_path)
        return sel.getDagPath(0)
    except:
        return None


def om_get_node_type(mobj):
    """Get node type name from MObject"""
    try:
        return mobj.apiTypeStr.replace('kPluginShape', 'mesh').replace('k', '').lower()
    except:
        return None


def om_get_node_type_name(mobj):
    """Get the actual node type name from MObject"""
    try:
        fn = om2.MFnDependencyNode(mobj)
        return fn.typeName
    except:
        return 'unknown'


def om_is_shape(mobj):
    """Check if MObject is a shape node"""
    try:
        return mobj.hasFn(om2.MFn.kShape)
    except:
        return False


def om_get_shapes(dag_path):
    """Get shape MDagPaths under a transform"""
    shapes = []
    try:
        # Check if this is a transform
        if not dag_path.node().hasFn(om2.MFn.kTransform):
            return shapes

        # Get number of shapes
        num_shapes = dag_path.numberOfShapesDirectlyBelow()
        for i in range(num_shapes):
            shape_path = om2.MDagPath(dag_path)
            shape_path.extendToShapeDirectlyBelow(i)
            shapes.append(shape_path)
    except:
        pass
    return shapes


def om_get_children(dag_path):
    """Get child MDagPaths under a DAG node"""
    children = []
    try:
        for i in range(dag_path.childCount()):
            child_obj = dag_path.child(i)
            if child_obj.hasFn(om2.MFn.kDagNode):
                child_fn = om2.MFnDagNode(child_obj)
                child_path = child_fn.getPath()
                children.append(child_path)
    except:
        pass
    return children


def om_get_visibility(dag_path):
    """Get visibility state using OpenMaya - returns 'visible', 'hidden', or 'locked'"""
    try:
        fn = om2.MFnDagNode(dag_path)
        plug = fn.findPlug('visibility', False)

        # Check if locked
        if plug.isLocked:
            return 'locked'

        # Get value
        if plug.asBool():
            return 'visible'
        return 'hidden'
    except:
        return 'locked'


# Data roles
NODE_ROLE = QtCore.Qt.UserRole + 1
VIS_ROLE = QtCore.Qt.UserRole + 2
CONNECTED_NODES_ROLE = QtCore.Qt.UserRole + 3
CHILDREN_LOADED_ROLE = QtCore.Qt.UserRole + 4


# =============================================================================
# MANUAL ICON MAPPING
# Add entries here for node types that don't have Maya icons
# Format: 'nodeType': 'iconSourceType'
# =============================================================================
ICON_FALLBACK_MAP = {
    'ffd': 'lattice',
    'baseLattice': 'lattice',
    'softMod': 'cluster',
    'nonLinear': 'deformer',
    'tweak': 'mesh',
    'groupId': 'objectSet',
    'groupParts': 'objectSet',
    # Add more mappings as needed:
    # 'someNodeType': 'iconSourceType',
}


def create_text_icon(text, size=18, bg_color='#555555', text_color='#ffffff'):
    """Create an icon with text (first 2 letters)"""
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtGui.QColor(bg_color))

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)

    # Draw text
    painter.setPen(QtGui.QColor(text_color))
    font = painter.font()
    font.setPixelSize(int(size * 0.6))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, text[:2].upper())

    painter.end()

    return QtGui.QIcon(pixmap)


# Cache for text icons
_text_icon_cache = {}

# Cache for Maya icons (type -> QIcon)
_maya_icon_cache = {}


def get_text_icon(node_type):
    """Get or create a text-based icon for a node type"""
    if node_type not in _text_icon_cache:
        _text_icon_cache[node_type] = create_text_icon(node_type[:2])
    return _text_icon_cache[node_type]


def get_maya_icon(node_type):
    """Get Maya's built-in icon for a node type (cached)"""
    # Check cache first
    if node_type in _maya_icon_cache:
        return _maya_icon_cache[node_type]

    # First check manual fallback map
    lookup_type = ICON_FALLBACK_MAP.get(node_type, node_type)

    icon = None
    try:
        # Get the icon name from Maya
        icon_name = cmds.resourceManager(nameFilter=f"out_{lookup_type}.png")
        if icon_name:
            icon_path = f":/{icon_name[0]}"
            icon = QtGui.QIcon(icon_path)
            if icon.isNull():
                icon = None

        # Try without 'out_' prefix
        if not icon:
            icon_name = cmds.resourceManager(nameFilter=f"{lookup_type}.png")
            if icon_name:
                icon_path = f":/{icon_name[0]}"
                icon = QtGui.QIcon(icon_path)
                if icon.isNull():
                    icon = None

        # Fallback: use nodeIconFilePath
        if not icon:
            icon_path = cmds.nodeIconFilePath(lookup_type)
            if icon_path:
                icon = QtGui.QIcon(icon_path)
                if icon.isNull():
                    icon = None

    except:
        pass

    # Final fallback: create text icon with first 2 letters
    if not icon:
        icon = get_text_icon(node_type)

    # Cache and return
    _maya_icon_cache[node_type] = icon
    return icon


def get_node_icon_om(dag_path, node_path=None):
    """Get appropriate Maya icon for a node using OpenMaya (faster)"""
    try:
        mobj = dag_path.node()
        node_type = om_get_node_type_name(mobj)

        # For transforms, check if they have a shape
        if mobj.hasFn(om2.MFn.kTransform):
            shapes = om_get_shapes(dag_path)
            if shapes:
                shape_type = om_get_node_type_name(shapes[0].node())
                icon = get_maya_icon(shape_type)
                if icon and not icon.isNull():
                    return icon
            else:
                # No shapes from OpenMaya, try cmds as fallback for shapes
                if node_path:
                    try:
                        cmds_shapes = cmds.listRelatives(node_path, shapes=True, fullPath=True) or []
                        if cmds_shapes:
                            shape_type = cmds.nodeType(cmds_shapes[0])
                            icon = get_maya_icon(shape_type)
                            if icon and not icon.isNull():
                                return icon
                    except:
                        pass

        # Get icon for the node type
        icon = get_maya_icon(node_type)
        if icon and not icon.isNull():
            return icon

    except:
        pass

    # Return default transform icon or text icon
    return get_maya_icon('transform')


def get_node_icon(node):
    """Get appropriate Maya icon for a node (wrapper that uses OpenMaya)"""
    dag_path = om_get_dag_path(node)
    if dag_path:
        return get_node_icon_om(dag_path, node)

    # Fallback to cmds if OpenMaya fails
    try:
        node_type = cmds.nodeType(node)

        # For transforms, check if they have a shape
        if node_type == 'transform':
            shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
            if shapes:
                shape_type = cmds.nodeType(shapes[0])
                icon = get_maya_icon(shape_type)
                if icon and not icon.isNull():
                    return icon

        return get_maya_icon(node_type)
    except:
        return get_maya_icon('transform')


def create_dot_icon(color, size=18):
    """Create a colored dot icon for visibility"""
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setBrush(QtGui.QBrush(QtGui.QColor(color)))
    painter.setPen(QtCore.Qt.NoPen)
    painter.drawEllipse(2, 2, size - 4, size - 4)
    painter.end()

    return QtGui.QIcon(pixmap)


# Visibility icons
VIS_ICONS = {
    'visible': create_dot_icon('#4caf50'),
    'hidden': create_dot_icon('#f44336'),
    'locked': create_dot_icon('#9e9e9e'),
}


class IndentLineDelegate(QtWidgets.QStyledItemDelegate):
    """Custom delegate to draw vertical indent lines"""

    def __init__(self, tree, parent=None):
        super(IndentLineDelegate, self).__init__(parent)
        self.tree = tree

    def paint(self, painter, option, index):
        # Call default paint first (draws arrow, icon, text)
        super(IndentLineDelegate, self).paint(painter, option, index)

        # Only draw lines for column 0
        if index.column() == 0:
            painter.save()

            indent = self.tree.indentation()
            model = self.tree.model()

            # Check if this item has children (has expand/collapse arrow)
            has_children = model.rowCount(index) > 0

            # Build list of ancestors: check siblings and if ancestor has children (arrow)
            ancestors_info = []  # List of (has_siblings_below, ancestor_has_children)
            current_index = index
            while current_index.parent().isValid():
                parent_index = current_index.parent()
                row = current_index.row()
                parent_row_count = model.rowCount(parent_index)
                has_siblings_below = row < parent_row_count - 1

                # Check if the ancestor (parent) has children (it does, since current is its child)
                # But we need to check if the SIBLING at this level has children
                # Actually, we need to check if there's an arrow at this column position
                # The arrow appears for items with children - check if parent has arrow
                parent_has_children = model.rowCount(parent_index) > 0

                ancestors_info.insert(0, (has_siblings_below, parent_has_children))
                current_index = parent_index

            depth = len(ancestors_info)

            # Use same color as the arrow/branch indicator (no transparency)
            line_color = option.palette.color(QtGui.QPalette.Text)
            pen = QtGui.QPen(line_color, 1, QtCore.Qt.SolidLine)
            painter.setPen(pen)

            # Draw vertical lines only where there are more siblings
            # Skip drawing at the immediate parent level if THIS item has an arrow
            for i in range(depth):
                has_siblings_below, _ = ancestors_info[i]
                if has_siblings_below:
                    # Skip the line at immediate parent position if this item has children (arrow)
                    if i == depth - 1 and has_children:
                        continue
                    x = option.rect.x() - (depth - i) * indent + indent // 2
                    painter.drawLine(x, option.rect.top(), x, option.rect.bottom())

            # Draw connector lines for this item - only if NO arrow (no children)
            if depth > 0 and not has_children:
                x_line = option.rect.x() - indent + indent // 2
                y = option.rect.center().y()

                # Vertical stub
                row = index.row()
                parent_row_count = model.rowCount(index.parent())
                is_last = row >= parent_row_count - 1

                if is_last:
                    # Last item - draw from top to center only
                    painter.drawLine(x_line, option.rect.top(), x_line, y)
                else:
                    # Has siblings below - draw full vertical line
                    painter.drawLine(x_line, option.rect.top(), x_line, option.rect.bottom())

                # Horizontal connector
                x_end = option.rect.x() - 4
                painter.drawLine(x_line, y, x_end, y)

            painter.restore()


class ConnectedNodesWidget(QtWidgets.QWidget):
    """Widget to display multiple Maya icons for connected nodes"""

    clicked = QtCore.Signal(str)  # Emits node path when clicked

    def __init__(self, connected_nodes, parent=None):
        super(ConnectedNodesWidget, self).__init__(parent)
        self.connected_nodes = connected_nodes or []
        self.icon_size = 18
        self.icon_rects = []  # Store rects for click detection
        self.is_truncated = False
        self.visible_count = 0

        # Calculate natural width (all icons)
        self.natural_width = max(20, len(self.connected_nodes) * (self.icon_size + 2))
        # Set minimum size but allow expansion
        self.setMinimumSize(20, self.icon_size + 2)
        self.setMouseTracking(True)

        # Cache icons
        self.icons = []
        for node_info in self.connected_nodes:
            node_type = node_info.get('type', 'transform')
            icon = get_maya_icon(node_type)
            self.icons.append(icon)

    def sizeHint(self):
        """Return preferred size (all icons visible)"""
        return QtCore.QSize(self.natural_width, self.icon_size + 2)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        self.icon_rects = []
        x = 2
        available_width = self.width()
        ellipsis_width = 14  # Width reserved for "..." indicator

        self.is_truncated = False
        self.visible_count = 0

        for i, icon in enumerate(self.icons):
            icon_width = self.icon_size + 2
            is_last = (i == len(self.icons) - 1)

            # Check if this icon fits
            if is_last:
                # Last icon - just needs to fit
                if x + icon_width > available_width:
                    # Doesn't fit - show ellipsis
                    self.is_truncated = True
                    break
            else:
                # Not last - need space for icon + potential ellipsis
                if x + icon_width + ellipsis_width > available_width:
                    # Won't fit with ellipsis - show ellipsis and stop
                    self.is_truncated = True
                    break

            # Draw this icon
            rect = QtCore.QRect(x, 1, self.icon_size, self.icon_size)
            self.icon_rects.append(rect)
            self.visible_count = i + 1

            if icon and not icon.isNull():
                icon.paint(painter, rect)

            x += icon_width

        # Draw ellipsis if truncated
        if self.is_truncated and x + ellipsis_width <= available_width:
            painter.setPen(QtGui.QColor(150, 150, 150))
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(x, 1, ellipsis_width, self.icon_size,
                           QtCore.Qt.AlignCenter, "...")

        painter.end()

    def mousePressEvent(self, event):
        # Right click - show context menu with all connected nodes
        if event.button() == QtCore.Qt.RightButton:
            self.show_context_menu(event.globalPos())
            return
        # Left click - let the event propagate to parent (tree viewport) for handling
        event.ignore()

    def show_context_menu(self, global_pos):
        """Show context menu with all connected nodes"""
        if not self.connected_nodes:
            return

        menu = QtWidgets.QMenu(self)
        # Ensure icons are visible in multi-column layout
        menu.setStyleSheet("QMenu::item { padding-left: 24px; } QMenu::icon { left: 4px; }")

        for node_info in self.connected_nodes:
            node_name = node_info.get('name', 'Unknown')
            node_type = node_info.get('type', 'transform')
            node_path = node_info.get('path', '')

            # Get icon for this node type
            icon = get_maya_icon(node_type)

            # Create action with icon and name
            action = menu.addAction(icon, f"{node_name}  ({node_type})")
            action.setData(node_path)

        # Execute menu and handle selection
        action = menu.exec_(global_pos)
        if action:
            node_path = action.data()
            if node_path:
                self.clicked.emit(node_path)
                # Also select in Maya directly
                if cmds.objExists(node_path):
                    cmds.select(node_path, replace=True)

    def mouseMoveEvent(self, event):
        """Update tooltip based on hovered icon"""
        pos = event.pos()
        for i, rect in enumerate(self.icon_rects):
            if rect.contains(pos) and i < len(self.connected_nodes):
                node_info = self.connected_nodes[i]
                node_name = node_info.get('name', 'Unknown')
                node_type = node_info.get('type', 'Unknown')
                tooltip = f"{node_name}\n({node_type})"
                self.setToolTip(tooltip)
                return
        # Show hint about right-click if truncated
        if self.is_truncated:
            hidden_count = len(self.connected_nodes) - self.visible_count
            self.setToolTip(f"+{hidden_count} more (right-click to see all)")
        else:
            self.setToolTip("")

    def enterEvent(self, event):
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def leaveEvent(self, event):
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setToolTip("")


class XPlorer(MayaQWidgetDockableMixin, QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(XPlorer, self).__init__(parent)
        self.setWindowTitle(f"xPlorer v{VERSION}")

        # Flag to track when we're handling a connected icon click
        self._handling_connected_click = False
        self.setMinimumSize(300, 400)

        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Menu bar
        menubar = QtWidgets.QMenuBar()

        # View menu
        view_menu = menubar.addMenu("View")

        frame_action = view_menu.addAction("Frame Selected (F)")
        frame_action.setShortcut("F")
        frame_action.triggered.connect(self.frame_in_hierarchy)

        view_menu.addSeparator()

        self.show_shapes_action = view_menu.addAction("Show Shapes")
        self.show_shapes_action.setCheckable(True)
        self.show_shapes_action.setChecked(False)
        self.show_shapes_action.triggered.connect(self.on_show_shapes_changed)

        # Track show shapes state
        self.show_shapes = False

        view_menu.addSeparator()

        refresh_action = view_menu.addAction("Refresh")
        refresh_action.setShortcut("Ctrl+R")
        refresh_action.triggered.connect(self.refresh)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        self.search_listed_only_action = settings_menu.addAction("Search Listed Nodes Only")
        self.search_listed_only_action.setCheckable(True)
        self.search_listed_only_action.setChecked(True)
        self.search_listed_only = True
        self.search_listed_only_action.triggered.connect(self.on_search_listed_only_changed)

        self.list_selected_only_action = settings_menu.addAction("List Selected Only")
        self.list_selected_only_action.setCheckable(True)
        self.list_selected_only_action.triggered.connect(self.on_list_selected_only_changed)

        self.auto_adjust_column_action = settings_menu.addAction("Auto Adjust Node Column")
        self.auto_adjust_column_action.setCheckable(True)
        self.auto_adjust_column_action.setChecked(True)
        self.auto_adjust_column = True
        self.auto_adjust_column_action.triggered.connect(self.on_auto_adjust_column_changed)

        self.stretch_connected_action = settings_menu.addAction("Stretch Connected Column")
        self.stretch_connected_action.setCheckable(True)
        self.stretch_connected_action.setChecked(True)
        self.stretch_connected_column = True
        self.stretch_connected_action.triggered.connect(self.on_stretch_connected_changed)

        settings_menu.addSeparator()

        # Search limit submenu
        search_limit_menu = settings_menu.addMenu("Search All Nodes Limit")
        self.search_limit = 50  # Default limit
        self.search_limit_group = QtWidgets.QActionGroup(self)
        for limit in [25, 50, 100, 200, 500, 0]:  # 0 = unlimited
            label = "Unlimited" if limit == 0 else str(limit)
            action = search_limit_menu.addAction(label)
            action.setCheckable(True)
            action.setData(limit)
            action.setChecked(limit == self.search_limit)
            action.triggered.connect(self._make_limit_handler(limit))
            self.search_limit_group.addAction(action)

        # Store pending search matches for "Load More" functionality
        self._pending_matches = []
        self._current_match_index = 0

        # Search debounce timer (delays search until user stops typing)
        self.search_timer = QtCore.QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._do_filter_tree)
        self._pending_search_text = ""

        # Load persistent settings
        self.load_settings()

        layout.addWidget(menubar)

        # Search bar
        search_layout = QtWidgets.QHBoxLayout()
        search_widget = QtWidgets.QWidget()
        search_widget.setLayout(search_layout)
        search_layout.setContentsMargins(5, 5, 5, 2)

        # Search field
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Search... (space separates terms)")
        self.search_field.setClearButtonEnabled(True)
        self.search_field.textChanged.connect(self.filter_tree)
        search_layout.addWidget(self.search_field)

        layout.addWidget(search_widget)

        # Button bar
        button_layout = QtWidgets.QHBoxLayout()
        button_widget = QtWidgets.QWidget()
        button_widget.setLayout(button_layout)
        button_layout.setContentsMargins(5, 2, 5, 5)

        # Get icon path
        icons_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icons")

        # Refresh button
        self.refresh_btn = QtWidgets.QPushButton("⟳")
        self.refresh_btn.setFixedSize(25, 25)
        self.refresh_btn.setToolTip("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        button_layout.addWidget(self.refresh_btn)

        # Add selected button
        self.add_btn = QtWidgets.QPushButton()
        self.add_btn.setFixedSize(25, 25)
        self.add_btn.setToolTip("Add selected to list")
        add_icon_path = os.path.join(icons_path, "mgear_plus-square.svg")
        if os.path.exists(add_icon_path):
            self.add_btn.setIcon(QtGui.QIcon(add_icon_path))
        else:
            self.add_btn.setText("+")
        self.add_btn.clicked.connect(self.add_selected_to_list)
        button_layout.addWidget(self.add_btn)

        # Remove selected button
        self.remove_btn = QtWidgets.QPushButton()
        self.remove_btn.setFixedSize(25, 25)
        self.remove_btn.setToolTip("Remove selected from list")
        remove_icon_path = os.path.join(icons_path, "mgear_minus-square.svg")
        if os.path.exists(remove_icon_path):
            self.remove_btn.setIcon(QtGui.QIcon(remove_icon_path))
        else:
            self.remove_btn.setText("-")
        self.remove_btn.clicked.connect(self.remove_selected_from_list)
        button_layout.addWidget(self.remove_btn)

        button_layout.addStretch()

        layout.addWidget(button_widget)

        # Model - 3 columns: Node name, Connected nodes, Visibility
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Node", "Connected", ""])

        # Tree
        self.tree = QtWidgets.QTreeView()
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tree.expanded.connect(self.on_expanded)
        self.tree.collapsed.connect(self.on_collapsed)
        self.tree.clicked.connect(self.on_clicked)

        # Connect selection model to sync Maya selection with tree selection
        self.tree.selectionModel().selectionChanged.connect(self.on_selection_changed)

        # Install application-level event filter for keyboard handling
        QtWidgets.QApplication.instance().installEventFilter(self)

        # Enable right-click context menu on tree
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_tree_context_menu)

        # Install event filter for middle click
        self.tree.viewport().installEventFilter(self)

        # Enable horizontal scrollbar
        self.tree.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)

        # Disable auto-scroll to selection
        self.tree.setAutoScroll(False)

        # Enable keyboard focus
        self.tree.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.tree.installEventFilter(self)

        # Header context menu and compact styling
        header = self.tree.header()
        header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.on_header_context_menu)
        header.setStretchLastSection(False)
        # Apply stretch setting for Connected column (loaded from settings)
        if self.stretch_connected_column:
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        else:
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        # Make header compact
        header.setMinimumSectionSize(20)
        header.setDefaultSectionSize(50)

        # Smaller indentation for deep hierarchies
        self.tree.setIndentation(15)

        # Create bigger arrow branch icons
        self.setup_branch_icons()

        # Set custom delegate for indent lines
        self.indent_delegate = IndentLineDelegate(self.tree, self.tree)
        self.tree.setItemDelegateForColumn(0, self.indent_delegate)

        # Column widths - Vis column as narrow as possible (icon is ~18px)
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 120)
        self.tree.setColumnWidth(2, 22)

        layout.addWidget(self.tree)

        # "Load More" button (hidden by default)
        self.load_more_btn = QtWidgets.QPushButton("Load More Results...")
        self.load_more_btn.setVisible(False)
        self.load_more_btn.clicked.connect(self.load_more_search_results)
        layout.addWidget(self.load_more_btn)

        # Load data
        self.refresh()

    def on_expanded(self, index):
        """Handle expand - lazy load children if needed"""
        item = self.model.itemFromIndex(index)
        if not item:
            return

        # Check if children already loaded
        if not item.data(CHILDREN_LOADED_ROLE):
            self.load_children(item)

        # Shift+expand all
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            self.expand_all_children(index)

    def on_show_shapes_changed(self, checked):
        """Handle show shapes toggle"""
        self.show_shapes = checked
        self.refresh()

    def on_stretch_connected_changed(self, checked):
        """Handle stretch connected column toggle"""
        self.stretch_connected_column = checked
        header = self.tree.header()
        if checked:
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        else:
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        self.save_settings()

    def setup_branch_icons(self):
        """Create bigger triangle arrow icons for branch indicators"""

        size = 18

        # Arrow color
        color = QtGui.QColor(180, 180, 180)

        # Create right arrow (collapsed) ▶
        right_pixmap = QtGui.QPixmap(size, size)
        right_pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(right_pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)

        # Draw right triangle
        triangle = QtGui.QPolygon([
            QtCore.QPoint(3, 2),
            QtCore.QPoint(size - 3, size // 2),
            QtCore.QPoint(3, size - 2)
        ])
        painter.drawPolygon(triangle)
        painter.end()

        # Create down arrow (expanded) ▼
        down_pixmap = QtGui.QPixmap(size, size)
        down_pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(down_pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)

        # Draw down triangle
        triangle = QtGui.QPolygon([
            QtCore.QPoint(2, 3),
            QtCore.QPoint(size - 2, 3),
            QtCore.QPoint(size // 2, size - 3)
        ])
        painter.drawPolygon(triangle)
        painter.end()

        # Save to temp directory
        temp_dir = tempfile.gettempdir()
        right_path = os.path.join(temp_dir, 'xplorer_arrow_right.png').replace('\\', '/')
        down_path = os.path.join(temp_dir, 'xplorer_arrow_down.png').replace('\\', '/')

        right_pixmap.save(right_path, 'PNG')
        down_pixmap.save(down_path, 'PNG')

        # Apply stylesheet
        self.tree.setStyleSheet(f"""
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                image: url({right_path});
            }}
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                image: url({down_path});
            }}
        """)

    def on_search_listed_only_changed(self, checked):
        """Handle search listed only toggle"""
        self.search_listed_only = checked
        self.save_settings()

    def on_list_selected_only_changed(self, checked):
        """Handle list selected only toggle"""
        self.list_selected_only = checked
        self.save_settings()

    def on_auto_adjust_column_changed(self, checked):
        """Handle auto adjust column toggle"""
        self.auto_adjust_column = checked
        self.save_settings()

    def _make_limit_handler(self, limit):
        """Create a handler for search limit change (avoids lambda closure issues)"""
        def handler(checked=None):
            self.on_search_limit_changed(limit)
        return handler

    def on_search_limit_changed(self, limit):
        """Handle search limit change"""
        self.search_limit = limit
        self.save_settings()

    def load_settings(self):
        """Load persistent settings from Maya optionVar"""
        # Search listed only
        if cmds.optionVar(exists='xplorer_search_listed_only'):
            val = cmds.optionVar(q='xplorer_search_listed_only')
            self.search_listed_only = bool(val)
            self.search_listed_only_action.setChecked(self.search_listed_only)

        # List selected only
        if cmds.optionVar(exists='xplorer_list_selected_only'):
            val = cmds.optionVar(q='xplorer_list_selected_only')
            self.list_selected_only = bool(val)
            self.list_selected_only_action.setChecked(self.list_selected_only)
        else:
            self.list_selected_only = False

        # Auto adjust column
        if cmds.optionVar(exists='xplorer_auto_adjust_column'):
            val = cmds.optionVar(q='xplorer_auto_adjust_column')
            self.auto_adjust_column = bool(val)
            self.auto_adjust_column_action.setChecked(self.auto_adjust_column)
        else:
            self.auto_adjust_column = True

        # Search limit
        if cmds.optionVar(exists='xplorer_search_limit'):
            val = cmds.optionVar(q='xplorer_search_limit')
            self.search_limit = int(val)
            # Update the menu checkmark
            for action in self.search_limit_group.actions():
                if action.data() == self.search_limit:
                    action.setChecked(True)
                    break

        # Stretch connected column
        if cmds.optionVar(exists='xplorer_stretch_connected_column'):
            val = cmds.optionVar(q='xplorer_stretch_connected_column')
            self.stretch_connected_column = bool(val)
            self.stretch_connected_action.setChecked(self.stretch_connected_column)
        else:
            self.stretch_connected_column = True

    def save_settings(self):
        """Save persistent settings to Maya optionVar"""
        cmds.optionVar(iv=('xplorer_search_listed_only', int(self.search_listed_only)))
        cmds.optionVar(iv=('xplorer_list_selected_only', int(self.list_selected_only)))
        cmds.optionVar(iv=('xplorer_auto_adjust_column', int(self.auto_adjust_column)))
        cmds.optionVar(iv=('xplorer_search_limit', int(self.search_limit)))
        cmds.optionVar(iv=('xplorer_stretch_connected_column', int(self.stretch_connected_column)))

    def on_tree_context_menu(self, pos):
        """Show context menu on tree right-click"""
        index = self.tree.indexAt(pos)
        if not index.isValid():
            return

        # Only show menu for column 0 (Node column)
        if index.column() != 0:
            return

        item = self.model.itemFromIndex(index)
        if not item:
            return

        node = item.data(NODE_ROLE)
        if not node:
            return

        short_name = node.split('|')[-1]
        full_path = node if node.startswith('|') else '|' + node

        menu = QtWidgets.QMenu(self)

        # Copy short name
        copy_name_action = menu.addAction(f"Copy Name")
        copy_name_action.triggered.connect(lambda: self.copy_to_clipboard(short_name))

        # Copy full path
        copy_path_action = menu.addAction(f"Copy Full Path")
        copy_path_action.triggered.connect(lambda: self.copy_to_clipboard(full_path))

        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(text)

    def on_header_context_menu(self, pos):
        """Show context menu on header right-click"""
        header = self.tree.header()
        column = header.logicalIndexAt(pos)

        menu = QtWidgets.QMenu(self)

        # Adjust this column
        adjust_col_action = menu.addAction(f"Adjust Column to Content")
        adjust_col_action.triggered.connect(lambda: self.resize_column_to_contents(column))

        # Adjust all columns
        adjust_all_action = menu.addAction("Adjust All Columns to Content")
        adjust_all_action.triggered.connect(self.adjust_all_columns)

        menu.exec_(header.mapToGlobal(pos))

    def resize_column_to_contents(self, column):
        """Resize column to fit content, including widgets"""
        if column == 1:
            # Connected column - calculate based on widgets
            max_width = 80  # Minimum width

            def check_item_width(parent):
                nonlocal max_width
                for row in range(parent.rowCount()):
                    item = parent.child(row, 1)
                    if item:
                        # Check widget width
                        index = self.model.indexFromItem(item)
                        widget = self.tree.indexWidget(index)
                        if widget:
                            max_width = max(max_width, widget.width() + 10)

                        # Check children
                        name_item = parent.child(row, 0)
                        if name_item:
                            check_item_width(name_item)

            check_item_width(self.model.invisibleRootItem())
            self.tree.setColumnWidth(column, max_width)
        else:
            # Use default resize for other columns
            self.tree.resizeColumnToContents(column)

    def adjust_all_columns(self):
        """Resize all columns to fit content"""
        for col in range(self.model.columnCount()):
            self.resize_column_to_contents(col)

    def on_collapsed(self, index):
        """Handle collapse - if shift held, collapse all children"""
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            self.collapse_all_children(index)

    def expand_all_children(self, index):
        """Recursively expand all children of index"""
        item = self.model.itemFromIndex(index)
        if not item:
            return

        # Load children if not loaded
        if not item.data(CHILDREN_LOADED_ROLE):
            self.load_children(item)

        for row in range(item.rowCount()):
            child = item.child(row, 0)
            if child and child.text() != "Loading...":
                child_index = self.model.indexFromItem(child)

                # Load grandchildren
                if not child.data(CHILDREN_LOADED_ROLE):
                    self.load_children(child)

                self.tree.expand(child_index)
                self.expand_all_children(child_index)

    def collapse_all_children(self, index):
        """Recursively collapse all children of index"""
        item = self.model.itemFromIndex(index)
        if not item:
            return

        for row in range(item.rowCount()):
            child = item.child(row, 0)
            if child and child.text() != "Loading...":
                child_index = self.model.indexFromItem(child)
                self.collapse_all_children(child_index)
                self.tree.collapse(child_index)

    def add_selected_to_list(self):
        """Add Maya selected nodes to the current list"""
        selection = cmds.ls(selection=True, long=True) or []
        if not selection:
            return

        # Get currently listed nodes to avoid duplicates
        listed_nodes = set()

        def collect_nodes(parent):
            for row in range(parent.rowCount()):
                item = parent.child(row, 0)
                if item:
                    node = item.data(NODE_ROLE)
                    if node:
                        listed_nodes.add(node)
                    collect_nodes(item)

        collect_nodes(self.model.invisibleRootItem())

        # Add new nodes
        for node in selection:
            if node not in listed_nodes:
                self.add_node(node, self.model.invisibleRootItem())

    def remove_selected_from_list(self):
        """Remove Maya selected nodes from the current list"""
        selection = cmds.ls(selection=True, long=True) or []
        if not selection:
            return

        selection_set = set(selection)

        # Find and remove matching items
        def remove_matching(parent):
            rows_to_remove = []
            for row in range(parent.rowCount()):
                item = parent.child(row, 0)
                if item:
                    node = item.data(NODE_ROLE)
                    if node in selection_set:
                        rows_to_remove.append(row)
                    else:
                        # Check children recursively
                        remove_matching(item)

            # Remove rows in reverse order to maintain indices
            for row in reversed(rows_to_remove):
                parent.removeRow(row)

        remove_matching(self.model.invisibleRootItem())

    def refresh(self):
        """Load hierarchy"""
        self.model.removeRows(0, self.model.rowCount())

        # Reset search state
        self.load_more_btn.setVisible(False)
        self._pending_matches = []
        self._current_match_index = 0

        if self.list_selected_only:
            # List only selected nodes - use OpenMaya for selection
            sel = om2.MGlobal.getActiveSelectionList()
            for i in range(sel.length()):
                try:
                    dag_path = sel.getDagPath(i)
                    node = dag_path.fullPathName()
                    self.add_node(node, self.model.invisibleRootItem(), dag_path=dag_path)
                except:
                    # Not a DAG node, skip
                    pass
        else:
            # Get root DAG nodes using OpenMaya iterator
            dag_iter = om2.MItDag(om2.MItDag.kDepthFirst, om2.MFn.kTransform)
            while not dag_iter.isDone():
                # Only get root level transforms (depth 0 or 1 for world)
                if dag_iter.depth() <= 1:
                    try:
                        dag_path = dag_iter.getPath()
                        # Check if it's a root (parent is world)
                        if dag_path.length() == 1:
                            node = dag_path.fullPathName()
                            self.add_node(node, self.model.invisibleRootItem(), dag_path=dag_path)
                    except:
                        pass
                dag_iter.next()

        # Clear search
        self.search_field.clear()

    def add_node(self, node, parent, load_children=False, dag_path=None):
        """Add node to tree. If load_children=False, only add placeholder.

        Args:
            node: Full path string of the node
            parent: Parent QStandardItem
            load_children: Whether to load children immediately
            dag_path: Optional MDagPath for performance (avoids re-lookup)
        """
        name = node.split('|')[-1]

        # Get or create dag_path for OpenMaya operations
        if dag_path is None:
            dag_path = om_get_dag_path(node)

        # Use OpenMaya for fast checks when available
        if dag_path:
            mobj = dag_path.node()
            is_shape = om_is_shape(mobj)
            node_type = om_get_node_type_name(mobj)
            vis_state = om_get_visibility(dag_path)
            node_icon = get_node_icon_om(dag_path, node)
        else:
            # Fallback to cmds
            is_shape = False
            try:
                is_shape = cmds.objectType(node, isAType='shape')
            except:
                pass
            try:
                node_type = cmds.nodeType(node)
            except:
                node_type = "unknown"
            vis_state = self.get_visibility_state(node)
            node_icon = get_node_icon(node)

        # Skip shapes if not showing them
        if is_shape and not self.show_shapes:
            return None

        # Column 0: Node name with Maya icon
        name_item = QtGui.QStandardItem(name)
        if node_icon:
            name_item.setIcon(node_icon)
        name_item.setData(node, NODE_ROLE)
        name_item.setData(False, CHILDREN_LOADED_ROLE)
        name_item.setEditable(False)

        # Tooltip with short name and type
        name_item.setToolTip(f"{name}\n({node_type})")

        # Column 1: Connected nodes (empty item, widget added later)
        connected_nodes = self.get_connected_nodes(node)
        connected_item = QtGui.QStandardItem()
        connected_item.setData(connected_nodes, CONNECTED_NODES_ROLE)
        connected_item.setEditable(False)

        # Column 2: Visibility icon
        vis_item = QtGui.QStandardItem()
        vis_item.setIcon(VIS_ICONS.get(vis_state, VIS_ICONS['locked']))
        vis_item.setData(node, NODE_ROLE)
        vis_item.setData(vis_state, VIS_ROLE)
        vis_item.setEditable(False)

        # Add row to parent
        parent.appendRow([name_item, connected_item, vis_item])

        # Add connected nodes widget to column 1
        if connected_nodes:
            connected_widget = ConnectedNodesWidget(connected_nodes)
            connected_widget.clicked.connect(self.on_connected_node_clicked)
            index = self.model.indexFromItem(connected_item)
            self.tree.setIndexWidget(index, connected_widget)

        # Check if has children using OpenMaya when available
        has_visible_children = False
        if dag_path:
            children = om_get_children(dag_path)
            for child_path in children:
                child_is_shape = om_is_shape(child_path.node())
                if child_is_shape and not self.show_shapes:
                    continue
                has_visible_children = True
                break
        else:
            # Fallback to cmds
            children = cmds.listRelatives(node, children=True, fullPath=True) or []
            for child in children:
                try:
                    child_is_shape = cmds.objectType(child, isAType='shape')
                    if child_is_shape and not self.show_shapes:
                        continue
                    has_visible_children = True
                    break
                except:
                    has_visible_children = True
                    break

        if has_visible_children:
            if load_children:
                # Load children immediately
                self.load_children(name_item)
            else:
                # Add placeholder for lazy loading
                placeholder = QtGui.QStandardItem("Loading...")
                placeholder.setEnabled(False)
                name_item.appendRow([placeholder, QtGui.QStandardItem(), QtGui.QStandardItem()])
        else:
            # No children, mark as loaded
            name_item.setData(True, CHILDREN_LOADED_ROLE)

        return name_item

    def load_children(self, parent_item):
        """Load children for an item (lazy loading)"""
        if parent_item.data(CHILDREN_LOADED_ROLE):
            return

        node = parent_item.data(NODE_ROLE)
        if not node:
            return

        # Remove placeholder
        if parent_item.rowCount() > 0:
            first_child = parent_item.child(0, 0)
            if first_child and first_child.text() == "Loading...":
                parent_item.removeRow(0)

        # Try OpenMaya first for performance
        dag_path = om_get_dag_path(node)
        if dag_path:
            children = om_get_children(dag_path)
            for child_path in children:
                # Pre-check if child is shape to skip
                if om_is_shape(child_path.node()) and not self.show_shapes:
                    continue
                child_full_path = child_path.fullPathName()
                self.add_node(child_full_path, parent_item, load_children=False, dag_path=child_path)
        else:
            # Fallback to cmds
            children = cmds.listRelatives(node, children=True, fullPath=True) or []
            for child in children:
                try:
                    child_is_shape = cmds.objectType(child, isAType='shape')
                    if child_is_shape and not self.show_shapes:
                        continue
                except:
                    pass
                self.add_node(child, parent_item, load_children=False)

        # Mark as loaded
        parent_item.setData(True, CHILDREN_LOADED_ROLE)

    def on_connected_node_clicked(self, node_path):
        """Handle click on connected node icon"""
        if node_path and cmds.objExists(node_path):
            cmds.select(node_path, replace=True)
            print(f"Selected: {node_path}")

    def closeEvent(self, event):
        """Clean up application event filter on close"""
        QtWidgets.QApplication.instance().removeEventFilter(self)
        super(XPlorer, self).closeEvent(event)

    def _is_mouse_over_tree(self):
        """Check if mouse is over tree widget"""
        global_pos = QtGui.QCursor.pos()
        widget_at = QtWidgets.QApplication.widgetAt(global_pos)
        while widget_at is not None:
            if widget_at == self.tree:
                return True
            widget_at = widget_at.parent()
        return False

    def eventFilter(self, obj, event):
        """Handle keyboard and mouse events"""
        # Keyboard events - F key and arrow keys when mouse is over tree
        if event.type() == QtCore.QEvent.KeyPress and self._is_mouse_over_tree():
            key = event.key()
            if key == QtCore.Qt.Key_F:
                self.frame_in_hierarchy()
                return True
            if key in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down, QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
                self.tree.keyPressEvent(event)
                return True

        # Mouse events on tree viewport
        if obj == self.tree.viewport():
            if event.type() == QtCore.QEvent.MouseButtonPress:
                pos = event.pos()
                index = self.tree.indexAt(pos)

                # Middle click on connected column
                if event.button() == QtCore.Qt.MiddleButton:
                    if index.isValid() and index.column() == 1:
                        self.on_middle_click_connected(index, pos)
                        return True

                # Left click handling
                if event.button() == QtCore.Qt.LeftButton:
                    # Connected column - select the row and trigger connected node action
                    if index.isValid() and index.column() == 1:
                        widget = self.tree.indexWidget(index)
                        if widget and isinstance(widget, ConnectedNodesWidget):
                            widget_pos = widget.mapFromGlobal(self.tree.viewport().mapToGlobal(pos))
                            for i, rect in enumerate(widget.icon_rects):
                                if rect.contains(widget_pos) and i < len(widget.connected_nodes):
                                    # Set flag to prevent on_selection_changed from selecting transform
                                    self._handling_connected_click = True
                                    # Highlight the row containing the icon
                                    row_index = index.sibling(index.row(), 0)
                                    self.tree.setCurrentIndex(row_index)
                                    self._handling_connected_click = False
                                    # Select the connected node in Maya
                                    node_path = widget.connected_nodes[i].get('path', '')
                                    if node_path:
                                        self.on_connected_node_clicked(node_path)
                                    return True

                    # Visibility column - handle before selection changes
                    if index.isValid() and index.column() == 2:
                        self.toggle_visibility_for_selection(index)
                        return True  # Consume the event to prevent selection change

        return False

    def on_middle_click_connected(self, index, pos):
        """Handle middle click on connected column - select node and open AE copy tab"""
        # Get the widget at this index
        widget = self.tree.indexWidget(index)
        if not widget or not isinstance(widget, ConnectedNodesWidget):
            return

        # Find which icon was clicked
        widget_pos = widget.mapFromGlobal(self.tree.viewport().mapToGlobal(pos))

        for i, rect in enumerate(widget.icon_rects):
            if rect.contains(widget_pos) and i < len(widget.connected_nodes):
                node_info = widget.connected_nodes[i]
                node_path = node_info.get('path', '')

                if node_path and cmds.objExists(node_path):
                    # Select the node
                    cmds.select(node_path, replace=True)

                    # Open Attribute Editor copy window - deferred so AE updates first
                    try:
                        mel.eval('evalDeferred "copyAEWindow"')
                    except Exception as e:
                        print(f"Error opening AE copy: {e}")
                return

    def on_middle_click(self, index):
        """Handle middle click - select node and open Attribute Editor copy tab"""
        print("Middle click triggered!")

        item = self.model.itemFromIndex(index)
        if not item:
            print("No item found")
            return

        node = item.data(NODE_ROLE)
        print(f"Node: {node}")

        if node and cmds.objExists(node):
            # Select the node
            cmds.select(node, replace=True)
            print(f"Selected: {node}")

            # Open Attribute Editor with copy tab
            try:
                # Open/focus Attribute Editor
                mel.eval('openAEWindow')
                print("Opened AE window")
                # Create a copy tab for this node
                mel.eval('AEaddCopyTab')
                print("Added copy tab")
            except Exception as e:
                print(f"Error opening Attribute Editor: {e}")

    def frame_in_hierarchy(self):
        """Expand tree to show selected Maya node"""
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            return

        node_path = selection[0]

        # Find and reveal the node in tree
        self.reveal_node(node_path)

    def reveal_node(self, node_path):
        """Find node in tree, expand parents, and select it"""

        # Build path hierarchy
        parts = node_path.split('|')
        if parts[0] == '':
            parts = parts[1:]  # Remove empty first part from |root|child

        # Navigate and expand from root
        current_parent = self.model.invisibleRootItem()
        found_item = None

        current_path = ""
        for part in parts:
            current_path = current_path + "|" + part

            # Find this part in current parent's children
            found = False
            for row in range(current_parent.rowCount()):
                item = current_parent.child(row, 0)
                if item and item.text() == part:
                    # Load children if not loaded
                    if not item.data(CHILDREN_LOADED_ROLE):
                        self.load_children(item)

                    # Expand this item
                    index = self.model.indexFromItem(item)
                    self.tree.expand(index)

                    current_parent = item
                    found_item = item
                    found = True
                    break

            if not found:
                print(f"Node not found in tree: {node_path}")
                return

        if found_item:
            # Adjust Node column to fit content
            self.resize_column_to_contents(0)

            # Select and scroll to item
            index = self.model.indexFromItem(found_item)
            self.tree.setCurrentIndex(index)

            # Scroll vertically to center
            self.tree.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)

            # Scroll horizontally to make sure item is visible
            self.scroll_to_item_horizontal(index)

            print(f"Framed: {node_path}")

    def get_connected_nodes(self, node):
        """Get connected nodes like Attribute Editor shows"""
        connected = []
        seen_paths = set()  # Track by path to avoid duplicates

        try:
            # Get shapes - always use cmds for reliability, it's only called once per node
            shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
            for shape in shapes:
                if shape in seen_paths:
                    continue
                seen_paths.add(shape)

                # Use OpenMaya for node type if possible
                shape_dag = om_get_dag_path(shape)
                if shape_dag:
                    shape_type = om_get_node_type_name(shape_dag.node())
                else:
                    shape_type = cmds.nodeType(shape)

                short_name = shape.split('|')[-1]
                connected.append({
                    'name': short_name,
                    'type': shape_type,
                    'path': shape
                })

                # Get shaders connected to this shape
                shading_engines = cmds.listConnections(shape, type='shadingEngine') or []
                for sg in shading_engines:
                    if sg in seen_paths:
                        continue

                    # Get the material connected to the shading engine
                    materials = cmds.listConnections(sg + '.surfaceShader') or []
                    for mat in materials:
                        if mat in seen_paths:
                            continue
                        seen_paths.add(mat)

                        # Use OpenMaya for node type
                        mat_obj = om_get_mobject(mat)
                        mat_type = om_get_node_type_name(mat_obj) if mat_obj else cmds.nodeType(mat)
                        connected.append({
                            'name': mat,
                            'type': mat_type,
                            'path': mat
                        })

            # Get other important connections (inputs)
            # Check for deformers, constraints, etc.
            history = cmds.listHistory(node, pruneDagObjects=True, interestLevel=1) or []

            # Skip types set for fast lookup
            skip_types = {'groupId', 'groupParts', 'tweak', 'objectSet', 'initialShadingGroup'}

            for hist_node in history[:10]:  # Limit to avoid too many
                if hist_node == node:
                    continue
                if hist_node in seen_paths:
                    continue

                # Use OpenMaya for node type lookup
                hist_obj = om_get_mobject(hist_node)
                node_type = om_get_node_type_name(hist_obj) if hist_obj else cmds.nodeType(hist_node)

                # Skip common uninteresting types
                if node_type in skip_types or hist_node in skip_types:
                    continue

                seen_paths.add(hist_node)
                connected.append({
                    'name': hist_node,
                    'type': node_type,
                    'path': hist_node
                })

            # Check for constraints
            constraints = cmds.listRelatives(node, type='constraint') or []
            for const in constraints:
                if const in seen_paths:
                    continue
                seen_paths.add(const)

                # Use OpenMaya for node type if possible
                const_obj = om_get_mobject(const)
                const_type = om_get_node_type_name(const_obj) if const_obj else cmds.nodeType(const)
                connected.append({
                    'name': const,
                    'type': const_type,
                    'path': const
                })

            # Check for controller tags
            # Show only if this node's .message connects to controller.controllerObject
            # Exclude if controller.message connects to this node (mGear rigCtlTags case)
            all_ctrl_connections = cmds.listConnections(node, type='controller', connections=True, plugs=True) or []

            # Process connections in pairs (source, destination)
            i = 0
            while i < len(all_ctrl_connections) - 1:
                plug1 = all_ctrl_connections[i]
                plug2 = all_ctrl_connections[i + 1]
                i += 2

                # Determine which is our node's plug and which is the controller's plug
                if node in plug1 or node.split('|')[-1] in plug1:
                    our_plug = plug1
                    ctrl_plug = plug2
                else:
                    our_plug = plug2
                    ctrl_plug = plug1

                # Get controller node name
                ctrl_node = ctrl_plug.split('.')[0]
                if ctrl_node in seen_paths:
                    continue

                # Only show if OUR .message connects to controller (we are the controllerObject)
                # Skip if controller.message connects to us (mGear rigCtlTags)
                if '.message' in ctrl_plug:
                    # controller.message -> our node = SKIP
                    continue

                if '.message' in our_plug:
                    # our.message -> controller = SHOW
                    seen_paths.add(ctrl_node)
                    connected.append({
                        'name': ctrl_node,
                        'type': 'controller',
                        'path': ctrl_node
                    })

        except Exception as e:
            pass

        return connected

    def get_visibility_state(self, node):
        """Get visibility state: visible, hidden, or locked"""
        # Try OpenMaya first for performance
        dag_path = om_get_dag_path(node)
        if dag_path:
            return om_get_visibility(dag_path)

        # Fallback to cmds
        try:
            if not cmds.objExists(node):
                return 'locked'
            if cmds.getAttr(f"{node}.visibility", lock=True):
                return 'locked'
            if cmds.getAttr(f"{node}.visibility"):
                return 'visible'
            return 'hidden'
        except:
            return 'locked'

    def on_clicked(self, index):
        """Handle click - scroll to item and update AE"""
        column = index.column()

        # Column 0: Scroll to item and ensure node is selected
        if column == 0:
            self.scroll_to_item_horizontal(index)
            # Handle re-clicking same row (on_selection_changed won't fire)
            item = self.model.itemFromIndex(index)
            if item:
                node = item.data(NODE_ROLE)
                if node and cmds.objExists(node):
                    # Check if this is the only selected item
                    selected_indexes = self.tree.selectionModel().selectedRows(0)
                    if len(selected_indexes) == 1:
                        cmds.select(node, replace=True)
                        self.update_attribute_editor(node)

        # Column 1: Handled by eventFilter
        # Column 2: Handled by eventFilter -> toggle_visibility_for_selection

    def toggle_visibility_for_selection(self, clicked_index):
        """Toggle visibility for all selected items, syncing to clicked item's new state"""
        # Get the clicked visibility item
        clicked_vis_item = self.model.itemFromIndex(clicked_index)
        if not clicked_vis_item:
            return

        clicked_node = clicked_vis_item.data(NODE_ROLE)
        clicked_vis_state = clicked_vis_item.data(VIS_ROLE)

        # Determine target visibility from clicked item
        if clicked_node and clicked_vis_state in ['visible', 'hidden']:
            try:
                current = cmds.getAttr(f"{clicked_node}.visibility")
                target_visible = not current
            except:
                return
        else:
            return

        # Get all selected rows
        selected_indexes = self.tree.selectionModel().selectedRows(0)

        # Collect all visibility items from selected rows
        vis_items_to_update = []
        for sel_index in selected_indexes:
            # Get the visibility item (column 2) for this row
            vis_index = sel_index.sibling(sel_index.row(), 2)
            vis_item = self.model.itemFromIndex(vis_index)
            if vis_item:
                vis_items_to_update.append(vis_item)

        # Check if clicked item's row is in selection
        clicked_row_index = clicked_index.sibling(clicked_index.row(), 0)
        clicked_in_selection = any(
            sel_index.row() == clicked_row_index.row() and
            sel_index.parent() == clicked_row_index.parent()
            for sel_index in selected_indexes
        )

        # If clicked item is not in selection, only toggle that one
        if not vis_items_to_update or not clicked_in_selection:
            vis_items_to_update = [clicked_vis_item]

        # Toggle visibility for all items
        for vis_item in vis_items_to_update:
            node = vis_item.data(NODE_ROLE)
            vis_state = vis_item.data(VIS_ROLE)

            # Skip locked attributes
            if vis_state == 'locked':
                continue

            if node and cmds.objExists(node):
                try:
                    cmds.setAttr(f"{node}.visibility", target_visible)
                    new_state = 'visible' if target_visible else 'hidden'
                    vis_item.setData(new_state, VIS_ROLE)
                    vis_item.setIcon(VIS_ICONS.get(new_state, VIS_ICONS['locked']))
                except Exception as e:
                    print(f"Error toggling visibility for {node}: {e}")

    def update_attribute_editor(self, node):
        """Update Attribute Editor to show the node's main tab (only if AE is the active/raised tab)"""
        try:
            # Check if Attribute Editor is the currently raised/active tab
            # workspaceControl -q -r returns True only if it's the raised tab in its tab group
            ae_is_raised = False
            try:
                ae_is_raised = cmds.workspaceControl('AttributeEditor', q=True, r=True)
            except:
                pass

            if not ae_is_raised:
                return

            # Get short name for AE commands
            short_name = node.split('|')[-1]
            # Update AE content and switch to the transform's tab
            mel.eval('updateAE "%s"' % short_name)
            # Switch to the node's tab in the AE (shows transform, not shape)
            mel.eval('showEditorExact "%s"' % short_name)
        except:
            pass

    def on_selection_changed(self, selected, deselected):
        """Sync Maya selection with tree selection"""
        # Skip if we're handling a connected icon click
        if self._handling_connected_click:
            return

        # Get all currently selected rows in the tree
        selected_indexes = self.tree.selectionModel().selectedRows(0)

        # Collect all nodes from selected rows
        nodes_to_select = []
        for sel_index in selected_indexes:
            item = self.model.itemFromIndex(sel_index)
            if item:
                node = item.data(NODE_ROLE)
                if node and cmds.objExists(node):
                    nodes_to_select.append(node)

        # Update Maya selection
        if nodes_to_select:
            cmds.select(nodes_to_select, replace=True)
            self.update_attribute_editor(nodes_to_select[0])
        else:
            cmds.select(clear=True)

    def scroll_to_item_horizontal(self, index):
        """Resize Node column to fit selected row and scroll to show item"""
        # Only resize if auto adjust is enabled
        if self.auto_adjust_column:
            # Resize column 0 to fit selected row content
            self.resize_column_to_row_contents(0, index)

            # Force update to recalculate scrollbar range
            self.tree.updateGeometry()
            QtWidgets.QApplication.processEvents()

            # Scroll horizontal all the way to the right
            h_scroll = self.tree.horizontalScrollBar()
            h_scroll.setValue(h_scroll.maximum())

    def resize_column_to_row_contents(self, column, index):
        """Resize column to fit the content of a specific row"""
        item = self.model.itemFromIndex(index)
        if not item:
            return

        # Calculate depth for indentation
        depth = 0
        parent = item.parent()
        while parent:
            depth += 1
            parent = parent.parent()

        indent = self.tree.indentation()
        indent_width = depth * indent

        # Get icon width
        icon = item.icon()
        icon_width = 0
        if not icon.isNull():
            sizes = icon.availableSizes()
            if sizes:
                icon_width = sizes[0].width() + 4
            else:
                icon_width = 20

        # Get text width
        font_metrics = QtGui.QFontMetrics(self.tree.font())
        text_rect = font_metrics.boundingRect(item.text())
        text_width = text_rect.width()

        # Total width: arrow(20) + indentation + icon + text + padding(20)
        total_width = 20 + indent_width + icon_width + text_width + 20

        # Set column width
        self.tree.setColumnWidth(column, int(total_width))

    def filter_tree(self, text):
        """Filter tree by search text - debounced for performance."""
        self._pending_search_text = text

        # For "search all nodes" mode, debounce to avoid searching on every keystroke
        if not self.search_listed_only and text.strip():
            self.search_timer.start(300)  # 300ms delay
        else:
            # For listed-only search, execute immediately (fast)
            self.search_timer.stop()
            self._do_filter_tree()

    def _do_filter_tree(self):
        """Actually perform the tree filtering."""
        text = self._pending_search_text.lower().strip()

        # Split by spaces to get multiple search terms
        search_terms = [t for t in text.split() if t] if text else []

        # Hide "Load More" button when not in search-all mode or search is cleared
        if not search_terms or self.search_listed_only:
            self.load_more_btn.setVisible(False)
            self._pending_matches = []
            self._current_match_index = 0

        # If searching all nodes (not just listed), search Maya and reveal matches
        if search_terms and not self.search_listed_only:
            self.search_all_nodes(search_terms)
            return

        def matches_search(name):
            """Check if name matches any search term"""
            if not search_terms:
                return True
            name_lower = name.lower()
            return any(term in name_lower for term in search_terms)

        def filter_item(item, parent_visible=False):
            """Recursively filter items, returns True if item should be visible"""
            if not item or item.text() == "Loading...":
                return False

            name = item.text()
            matches = matches_search(name)

            # Check children (children are on column 0 item)
            child_visible = False
            for row in range(item.rowCount()):
                child = item.child(row, 0)
                if child and filter_item(child, matches or parent_visible):
                    child_visible = True

            # Show if matches, parent matches, or any child matches
            visible = matches or parent_visible or child_visible

            # Get index and set row hidden
            index = self.model.indexFromItem(item)
            self.tree.setRowHidden(index.row(), index.parent(), not visible)

            # Expand if has matching children
            if child_visible and search_terms:
                self.tree.expand(index)

            return visible

        # Filter from root
        root = self.model.invisibleRootItem()
        for row in range(root.rowCount()):
            item = root.child(row, 0)
            if item:
                filter_item(item)

    def search_all_nodes(self, search_terms):
        """Search all Maya DAG nodes and reveal matches"""
        # Get all DAG nodes matching any search term
        all_dag = cmds.ls(dag=True, long=True) or []

        def matches_any_term(node_path):
            name = node_path.split('|')[-1].lower()
            return any(term in name for term in search_terms)

        all_matches = [n for n in all_dag if matches_any_term(n)]
        total_matches = len(all_matches)

        # Store all matches for "Load More" functionality
        self._pending_matches = all_matches
        self._current_match_index = 0

        # Determine how many to show initially
        if self.search_limit > 0:
            matches_to_show = all_matches[:self.search_limit]
            self._current_match_index = len(matches_to_show)
            has_more = total_matches > self.search_limit
        else:
            matches_to_show = all_matches
            self._current_match_index = total_matches
            has_more = False

        # First, hide all items
        root = self.model.invisibleRootItem()

        def hide_all(parent):
            for row in range(parent.rowCount()):
                item = parent.child(row, 0)
                if item:
                    index = self.model.indexFromItem(item)
                    self.tree.setRowHidden(index.row(), index.parent(), True)
                    hide_all(item)

        hide_all(root)

        # Reveal each match
        for match in matches_to_show:
            self.reveal_node_for_search(match)

        # Update "Load More" button
        if has_more:
            remaining = total_matches - self._current_match_index
            self.load_more_btn.setText(f"Load More Results... ({remaining} remaining)")
            self.load_more_btn.setVisible(True)
        else:
            self.load_more_btn.setVisible(False)

    def load_more_search_results(self):
        """Load more search results when 'Load More' button is clicked"""
        if not self._pending_matches:
            self.load_more_btn.setVisible(False)
            return

        total_matches = len(self._pending_matches)
        start_index = self._current_match_index

        # Determine batch size (use search_limit or default to 50)
        batch_size = self.search_limit if self.search_limit > 0 else 50
        end_index = min(start_index + batch_size, total_matches)

        # Get next batch of matches
        next_batch = self._pending_matches[start_index:end_index]
        self._current_match_index = end_index

        # Reveal each match in the batch
        for match in next_batch:
            self.reveal_node_for_search(match)

        # Update button or hide if no more results
        if self._current_match_index >= total_matches:
            self.load_more_btn.setVisible(False)
        else:
            remaining = total_matches - self._current_match_index
            self.load_more_btn.setText(f"Load More Results... ({remaining} remaining)")

    def reveal_node_for_search(self, node_path):
        """Reveal a node in the tree for search results"""
        parts = node_path.split('|')
        if parts[0] == '':
            parts = parts[1:]

        current_parent = self.model.invisibleRootItem()

        for i, part in enumerate(parts):
            found = False
            for row in range(current_parent.rowCount()):
                item = current_parent.child(row, 0)
                if item and item.text() == part:
                    # Load children if not loaded
                    if not item.data(CHILDREN_LOADED_ROLE):
                        self.load_children(item)

                    # Show this item
                    index = self.model.indexFromItem(item)
                    self.tree.setRowHidden(index.row(), index.parent(), False)

                    # Expand parent
                    if i < len(parts) - 1:
                        self.tree.expand(index)

                    current_parent = item
                    found = True
                    break

            if not found:
                break


# Global
xplorer_win = None

def show():
    global xplorer_win

    if cmds.workspaceControl("XPlorerWorkspaceControl", exists=True):
        cmds.deleteUI("XPlorerWorkspaceControl")

    xplorer_win = XPlorer()
    xplorer_win.show(dockable=True)
    return xplorer_win


if __name__ == "__main__":
    show()