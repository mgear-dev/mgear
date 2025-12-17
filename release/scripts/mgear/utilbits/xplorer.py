
import maya.cmds as cmds

VERSION = "1.0.0"


try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QStandardItemModel, QStandardItem
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import Qt
    from PySide2.QtGui import QStandardItemModel, QStandardItem

try:
    from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
except:
    class MayaQWidgetDockableMixin:
        pass


# Data roles
NODE_ROLE = Qt.UserRole + 1
VIS_ROLE = Qt.UserRole + 2
CONNECTED_NODES_ROLE = Qt.UserRole + 3
CHILDREN_LOADED_ROLE = Qt.UserRole + 4


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
    painter.drawText(pixmap.rect(), Qt.AlignCenter, text[:2].upper())

    painter.end()

    return QtGui.QIcon(pixmap)


# Cache for text icons
_text_icon_cache = {}


def get_text_icon(node_type):
    """Get or create a text-based icon for a node type"""
    if node_type not in _text_icon_cache:
        _text_icon_cache[node_type] = create_text_icon(node_type[:2])
    return _text_icon_cache[node_type]


def get_maya_icon(node_type):
    """Get Maya's built-in icon for a node type"""
    # First check manual fallback map
    lookup_type = ICON_FALLBACK_MAP.get(node_type, node_type)

    try:
        # Get the icon name from Maya
        icon_name = cmds.resourceManager(nameFilter=f"out_{lookup_type}.png")
        if icon_name:
            icon_path = f":/{icon_name[0]}"
            icon = QtGui.QIcon(icon_path)
            if not icon.isNull():
                return icon

        # Try without 'out_' prefix
        icon_name = cmds.resourceManager(nameFilter=f"{lookup_type}.png")
        if icon_name:
            icon_path = f":/{icon_name[0]}"
            icon = QtGui.QIcon(icon_path)
            if not icon.isNull():
                return icon

        # Fallback: use nodeIconFilePath
        icon_path = cmds.nodeIconFilePath(lookup_type)
        if icon_path:
            icon = QtGui.QIcon(icon_path)
            if not icon.isNull():
                return icon

    except:
        pass

    # Final fallback: create text icon with first 2 letters
    return get_text_icon(node_type)


def get_node_icon(node):
    """Get appropriate Maya icon for a node"""
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

        # Get icon for the node type
        icon = get_maya_icon(node_type)
        if icon and not icon.isNull():
            return icon

    except:
        pass

    # Return default transform icon or text icon
    return get_maya_icon('transform')


def create_dot_icon(color, size=18):
    """Create a colored dot icon for visibility"""
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setBrush(QtGui.QBrush(QtGui.QColor(color)))
    painter.setPen(Qt.NoPen)
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
            pen = QtGui.QPen(line_color, 1, Qt.SolidLine)
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

        # Set size based on number of icons
        width = max(20, len(self.connected_nodes) * (self.icon_size + 2))
        self.setFixedSize(width, self.icon_size + 2)
        self.setMouseTracking(True)

        # Cache icons
        self.icons = []
        for node_info in self.connected_nodes:
            node_type = node_info.get('type', 'transform')
            icon = get_maya_icon(node_type)
            self.icons.append(icon)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        self.icon_rects = []
        x = 2

        for i, icon in enumerate(self.icons):
            rect = QtCore.QRect(x, 1, self.icon_size, self.icon_size)
            self.icon_rects.append(rect)

            if icon and not icon.isNull():
                icon.paint(painter, rect)

            x += self.icon_size + 2

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            for i, rect in enumerate(self.icon_rects):
                if rect.contains(pos) and i < len(self.connected_nodes):
                    node_path = self.connected_nodes[i].get('path', '')
                    if node_path:
                        self.clicked.emit(node_path)
                    return
        super(ConnectedNodesWidget, self).mousePressEvent(event)

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
        self.setToolTip("")

    def enterEvent(self, event):
        self.setCursor(Qt.PointingHandCursor)

    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        self.setToolTip("")


class XPlorer(MayaQWidgetDockableMixin, QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(XPlorer, self).__init__(parent)
        self.setWindowTitle(f"xPlorer v{VERSION}")
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

        # Load persistent settings
        self.load_settings()

        layout.addWidget(menubar)

        # Toolbar
        toolbar = QtWidgets.QHBoxLayout()
        toolbar_widget = QtWidgets.QWidget()
        toolbar_widget.setLayout(toolbar)
        toolbar.setContentsMargins(5, 5, 5, 5)

        # Refresh button
        self.refresh_btn = QtWidgets.QPushButton("⟳")
        self.refresh_btn.setFixedSize(30, 25)
        self.refresh_btn.setToolTip("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        # Search field
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Search...")
        self.search_field.textChanged.connect(self.filter_tree)
        toolbar.addWidget(self.search_field)

        layout.addWidget(toolbar_widget)

        # Model - 3 columns: Node name, Connected nodes, Visibility
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Node", "Connected", "Vis"])

        # Tree
        self.tree = QtWidgets.QTreeView()
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.expanded.connect(self.on_expanded)
        self.tree.collapsed.connect(self.on_collapsed)
        self.tree.clicked.connect(self.on_clicked)

        # Enable right-click context menu on tree
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_tree_context_menu)

        # Install event filter for middle click
        self.tree.viewport().installEventFilter(self)

        # Enable horizontal scrollbar
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)

        # Disable auto-scroll to selection
        self.tree.setAutoScroll(False)

        # Enable keyboard focus
        self.tree.setFocusPolicy(Qt.StrongFocus)
        self.tree.installEventFilter(self)

        # Header context menu
        header = self.tree.header()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.on_header_context_menu)
        header.setStretchLastSection(False)

        # Smaller indentation for deep hierarchies
        self.tree.setIndentation(15)

        # Create bigger arrow branch icons
        self.setup_branch_icons()

        # Set custom delegate for indent lines
        self.indent_delegate = IndentLineDelegate(self.tree, self.tree)
        self.tree.setItemDelegateForColumn(0, self.indent_delegate)

        # Column widths
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 120)
        self.tree.setColumnWidth(2, 30)

        layout.addWidget(self.tree)

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
        if modifiers == Qt.ShiftModifier:
            self.expand_all_children(index)

    def on_show_shapes_changed(self, checked):
        """Handle show shapes toggle"""
        self.show_shapes = checked
        self.refresh()

    def setup_branch_icons(self):
        """Create bigger triangle arrow icons for branch indicators"""
        import tempfile
        import os

        size = 18

        # Arrow color
        color = QtGui.QColor(180, 180, 180)

        # Create right arrow (collapsed) ▶
        right_pixmap = QtGui.QPixmap(size, size)
        right_pixmap.fill(Qt.transparent)
        painter = QtGui.QPainter(right_pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
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
        down_pixmap.fill(Qt.transparent)
        painter = QtGui.QPainter(down_pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
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

    def save_settings(self):
        """Save persistent settings to Maya optionVar"""
        cmds.optionVar(iv=('xplorer_search_listed_only', int(self.search_listed_only)))
        cmds.optionVar(iv=('xplorer_list_selected_only', int(self.list_selected_only)))
        cmds.optionVar(iv=('xplorer_auto_adjust_column', int(self.auto_adjust_column)))

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
        if modifiers == Qt.ShiftModifier:
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

    def refresh(self):
        """Load hierarchy"""
        self.model.removeRows(0, self.model.rowCount())

        if self.list_selected_only:
            # List only selected nodes
            selection = cmds.ls(selection=True, long=True) or []
            for node in selection:
                self.add_node(node, self.model.invisibleRootItem())
        else:
            # Get root DAG nodes
            all_dag = cmds.ls(dag=True, long=True) or []
            roots = [n for n in all_dag if '|' not in n[1:]]

            for node in roots:
                self.add_node(node, self.model.invisibleRootItem())

        # Clear search
        self.search_field.clear()

    def add_node(self, node, parent, load_children=False):
        """Add node to tree. If load_children=False, only add placeholder."""
        name = node.split('|')[-1]

        # Check if this is a shape node
        is_shape = False
        try:
            is_shape = cmds.objectType(node, isAType='shape')
        except:
            pass

        # Skip shapes if not showing them
        if is_shape and not self.show_shapes:
            return None

        # Get visibility state
        vis_state = self.get_visibility_state(node)

        # Get node type for tooltip
        try:
            node_type = cmds.nodeType(node)
        except:
            node_type = "unknown"

        # Column 0: Node name with Maya icon
        name_item = QStandardItem(name)
        node_icon = get_node_icon(node)
        if node_icon:
            name_item.setIcon(node_icon)
        name_item.setData(node, NODE_ROLE)
        name_item.setData(False, CHILDREN_LOADED_ROLE)
        name_item.setEditable(False)

        # Tooltip with short name and type
        name_item.setToolTip(f"{name}\n({node_type})")

        # Column 1: Connected nodes (empty item, widget added later)
        connected_nodes = self.get_connected_nodes(node)
        connected_item = QStandardItem()
        connected_item.setData(connected_nodes, CONNECTED_NODES_ROLE)
        connected_item.setEditable(False)

        # Column 2: Visibility icon
        vis_item = QStandardItem()
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

        # Check if has children - add placeholder if yes
        children = cmds.listRelatives(node, children=True, fullPath=True) or []
        has_visible_children = False

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
                placeholder = QStandardItem("Loading...")
                placeholder.setEnabled(False)
                name_item.appendRow([placeholder, QStandardItem(), QStandardItem()])
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

        # Get and add children
        children = cmds.listRelatives(node, children=True, fullPath=True) or []
        for child in children:
            # Pre-check if child is shape to skip
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

    def eventFilter(self, obj, event):
        """Handle keyboard and mouse events"""
        # F key on tree
        if obj == self.tree and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == Qt.Key_F:
                self.frame_in_hierarchy()
                return True

        # Middle click on tree viewport - for connected column icons
        if obj == self.tree.viewport():
            if event.type() == QtCore.QEvent.MouseButtonPress:
                if event.button() == Qt.MiddleButton:
                    pos = event.pos()
                    index = self.tree.indexAt(pos)
                    if index.isValid() and index.column() == 1:
                        self.on_middle_click_connected(index, pos)
                        return True

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
                    import maya.mel as mel
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
            import maya.mel as mel
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
            # Get shapes first
            shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
            for shape in shapes:
                if shape in seen_paths:
                    continue
                seen_paths.add(shape)

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

                        mat_type = cmds.nodeType(mat)
                        connected.append({
                            'name': mat,
                            'type': mat_type,
                            'path': mat
                        })

            # Get other important connections (inputs)
            # Check for deformers, constraints, etc.
            history = cmds.listHistory(node, pruneDagObjects=True, interestLevel=1) or []

            for hist_node in history[:10]:  # Limit to avoid too many
                if hist_node == node:
                    continue
                if hist_node in seen_paths:
                    continue

                node_type = cmds.nodeType(hist_node)

                # Skip common uninteresting types
                skip_types = ['groupId', 'groupParts', 'tweak', 'objectSet',
                             'initialShadingGroup']
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

                const_type = cmds.nodeType(const)
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
        """Handle click - select node or toggle visibility"""
        column = index.column()

        # Column 0: Select node
        if column == 0:
            item = self.model.itemFromIndex(index)
            if item:
                node = item.data(NODE_ROLE)
                if node and cmds.objExists(node):
                    modifiers = QtWidgets.QApplication.keyboardModifiers()
                    if modifiers == Qt.ShiftModifier:
                        cmds.select(node, add=True)
                    elif modifiers == Qt.ControlModifier:
                        cmds.select(node, toggle=True)
                    else:
                        cmds.select(node, replace=True)

                    # Scroll horizontally to make sure item is visible
                    self.scroll_to_item_horizontal(index)

        # Column 1: Handled by ConnectedNodesWidget

        # Column 2: Toggle visibility
        elif column == 2:
            item = self.model.itemFromIndex(index)
            if not item:
                return

            node = item.data(NODE_ROLE)
            vis_state = item.data(VIS_ROLE)

            if node and vis_state in ['visible', 'hidden']:
                try:
                    current = cmds.getAttr(f"{node}.visibility")
                    cmds.setAttr(f"{node}.visibility", not current)

                    new_state = 'hidden' if current else 'visible'
                    item.setData(new_state, VIS_ROLE)
                    item.setIcon(VIS_ICONS.get(new_state, VIS_ICONS['locked']))
                except Exception as e:
                    print(f"Error toggling visibility: {e}")

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
        """Filter tree by search text"""
        text = text.lower()

        # If searching all nodes (not just listed), search Maya and reveal matches
        if text and not self.search_listed_only:
            self.search_all_nodes(text)
            return

        def filter_item(item, parent_visible=False):
            """Recursively filter items, returns True if item should be visible"""
            if not item or item.text() == "Loading...":
                return False

            name = item.text().lower()
            matches = text in name if text else True

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
            if child_visible and text:
                self.tree.expand(index)

            return visible

        # Filter from root
        root = self.model.invisibleRootItem()
        for row in range(root.rowCount()):
            item = root.child(row, 0)
            if item:
                filter_item(item)

    def search_all_nodes(self, text):
        """Search all Maya DAG nodes and reveal matches"""
        # Get all DAG nodes matching the search
        all_dag = cmds.ls(dag=True, long=True) or []
        matches = [n for n in all_dag if text in n.split('|')[-1].lower()]

        # Limit results to avoid performance issues
        matches = matches[:50]

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
        for match in matches:
            self.reveal_node_for_search(match)

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