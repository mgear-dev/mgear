from mgear.vendor.Qt import QtCore, QtWidgets, QtGui
from typing import Optional


class GuideTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """
    Tree widget item representing the root mGear guide.

    Displays the rig name with a character icon and bold font styling.
    """
    def __init__(self, parent: Optional[QtWidgets.QTreeWidgetItem], rig_name: str) -> None:
        """
        Initialize a guide tree item.

        :param parent: Parent tree item or None for a top-level item.
        :param rig_name: Name of the rig associated with the guide.
        :return: None
        """
        super(GuideTreeWidgetItem, self).__init__(parent, [f"guide ({rig_name})"])

        self.rig_name: str = rig_name

        self.setIcon(0, QtGui.QIcon(":character.svg"))
        self.setExpanded(True)

        name_font = QtGui.QFont()
        name_font.setBold(True)
        self.setFont(0, name_font)
        self.setToolTip(0, f"guide ({rig_name})")


class ComponentTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """
    Tree widget item representing a single mGear component.

    Shows the component name and type, with the type rendered in a
    monospace font for readability.
    """
    def __init__(self,
                 parent: Optional[QtWidgets.QTreeWidgetItem],
                 component: str,
                 comp_type: str) -> None:
        """
        Initialize a component tree item.

        :param parent: Parent tree item, typically the guide root item.
        :param component: Full component name, for example ``"arm_L0"``.
        :param comp_type: Component type name, for example ``"arm_2jnt"``.
        :return: None
        """
        super(ComponentTreeWidgetItem, self).__init__(parent, [component, comp_type])

        self.component_name: str = component
        self.component_type: str = comp_type

        self.setIcon(0, QtGui.QIcon(":advancedSettings.png"))

        self.setToolTip(0, component)

        mono = QtGui.QFont("Consolas")
        mono.setStyleHint(QtGui.QFont.Monospace)
        self.setFont(1, mono)
        self.setToolTip(1, comp_type)