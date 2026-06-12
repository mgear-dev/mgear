"""
mGear Component Type Browser
A tool to list and select mGear components by type

"""

import re
from collections import defaultdict

from maya import cmds

from mgear.vendor.Qt import QtCore, QtWidgets
from mgear.core import pyqt


class MGearComponentTypeBrowser(QtWidgets.QDialog):
    """Browser for mGear component types"""

    def __init__(self, parent=None):
        if parent is None:
            parent = pyqt.maya_main_window()

        super(MGearComponentTypeBrowser, self).__init__(parent)

        self.setWindowTitle("mGear Component Type Browser")
        self.setMinimumWidth(450)
        self.setMinimumHeight(500)

        self.component_types = {}  # {type_name: [component_list]}

        self.create_widgets()
        self.create_layout()
        self.create_connections()

        self.refresh_types()

    def create_widgets(self):
        """Create UI widgets"""
        # Filter section
        self.filter_label = QtWidgets.QLabel("Filter (regex):")
        self.filter_line = QtWidgets.QLineEdit()
        self.filter_line.setPlaceholderText("Enter regex pattern...")

        # Type list
        self.type_list = QtWidgets.QListWidget()
        self.type_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        # Buttons
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.select_btn = QtWidgets.QPushButton("Select All of Type")
        self.close_btn = QtWidgets.QPushButton("Close")

        # Status label
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")

    def create_layout(self):
        """Create UI layout"""
        # Filter layout
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(self.filter_label)
        filter_layout.addWidget(self.filter_line)

        # Button layout
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.select_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.type_list)
        main_layout.addWidget(self.status_label)
        main_layout.addLayout(button_layout)

    def create_connections(self):
        """Create signal connections"""
        self.filter_line.textChanged.connect(self.apply_filter)
        self.type_list.itemClicked.connect(self.select_components_of_type)
        self.type_list.itemDoubleClicked.connect(self.select_components_of_type)
        self.refresh_btn.clicked.connect(self.refresh_types)
        self.select_btn.clicked.connect(self.select_current_type)
        self.close_btn.clicked.connect(self.close)

    def find_mgear_component_types(self):
        """Find all mGear components and group them by type"""
        type_dict = defaultdict(list)

        # Get all transforms in the scene
        all_transforms = cmds.ls(type='transform', long=True)

        for obj in all_transforms:
            # Check if object name ends with _root
            if not obj.split('|')[-1].endswith('_root'):
                continue

            # Check if it has the isGearGuide attribute
            if not cmds.attributeQuery('isGearGuide', node=obj, exists=True):
                continue

            # Check if it has comp_type attribute
            if not cmds.attributeQuery('comp_type', node=obj, exists=True):
                continue

            # Get the component type
            comp_type = cmds.getAttr(f"{obj}.comp_type")
            if comp_type:
                type_dict[comp_type].append(obj)

        return dict(type_dict)

    def refresh_types(self):
        """Refresh the component type list"""
        self.component_types = self.find_mgear_component_types()
        self.apply_filter()

        type_count = len(self.component_types)
        total_components = sum(len(comps) for comps in self.component_types.values())
        self.status_label.setText(
            f"Found {type_count} type{'s' if type_count != 1 else ''}, "
            f"{total_components} component{'s' if total_components != 1 else ''} total"
        )

    def apply_filter(self):
        """Apply regex filter to type list"""
        self.type_list.clear()

        filter_text = self.filter_line.text()

        # Sort types alphabetically
        sorted_types = sorted(self.component_types.keys())

        # If no filter, show all types
        if not filter_text:
            for comp_type in sorted_types:
                components = self.component_types[comp_type]
                count = len(components)
                display_text = f"{comp_type} ({count})"

                item = QtWidgets.QListWidgetItem(display_text)
                item.setData(QtCore.Qt.UserRole, comp_type)
                item.setData(QtCore.Qt.UserRole + 1, components)

                # Create tooltip with component list
                tooltip_lines = [f"Type: {comp_type}", f"Count: {count}", "", "Components:"]
                tooltip_lines.extend([comp.split('|')[-1] for comp in components[:10]])
                if count > 10:
                    tooltip_lines.append(f"... and {count - 10} more")
                item.setToolTip('\n'.join(tooltip_lines))

                self.type_list.addItem(item)
            return

        # Apply regex filter
        try:
            pattern = re.compile(filter_text, re.IGNORECASE)
            filtered_types = [t for t in sorted_types if pattern.search(t)]

            for comp_type in filtered_types:
                components = self.component_types[comp_type]
                count = len(components)
                display_text = f"{comp_type} ({count})"

                item = QtWidgets.QListWidgetItem(display_text)
                item.setData(QtCore.Qt.UserRole, comp_type)
                item.setData(QtCore.Qt.UserRole + 1, components)

                # Create tooltip with component list
                tooltip_lines = [f"Type: {comp_type}", f"Count: {count}", "", "Components:"]
                tooltip_lines.extend([comp.split('|')[-1] for comp in components[:10]])
                if count > 10:
                    tooltip_lines.append(f"... and {count - 10} more")
                item.setToolTip('\n'.join(tooltip_lines))

                self.type_list.addItem(item)

            # Update status with filter info
            type_count = len(filtered_types)
            total_types = len(self.component_types)
            filtered_comp_count = sum(len(self.component_types[t]) for t in filtered_types)
            self.status_label.setText(
                f"Showing {type_count} of {total_types} type{'s' if total_types != 1 else ''}, "
                f"{filtered_comp_count} component{'s' if filtered_comp_count != 1 else ''}"
            )

        except re.error as e:
            self.status_label.setText(f"Invalid regex: {str(e)}")

    def select_components_of_type(self, item):
        """Select all components of the clicked type"""
        components = item.data(QtCore.Qt.UserRole + 1)
        existing = [c for c in components if cmds.objExists(c)]

        if existing:
            cmds.select(existing, replace=True)
            comp_type = item.data(QtCore.Qt.UserRole)
            print(f"Selected {len(existing)} component(s) of type: {comp_type}")

    def select_current_type(self):
        """Select all components of the currently selected type"""
        current_item = self.type_list.currentItem()
        if current_item:
            self.select_components_of_type(current_item)


def show():
    """Show the mGear Component Type Browser"""
    return pyqt.showDialog(MGearComponentTypeBrowser)


if __name__ == "__main__":
    show()
