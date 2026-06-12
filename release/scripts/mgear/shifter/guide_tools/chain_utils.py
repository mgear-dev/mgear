"""Chain utilities for mGear Shifter guide tools.

"""

from __future__ import print_function

from maya import cmds

from mgear.vendor.Qt import QtWidgets
from mgear.core import pyqt

import mgear.pymaya as pm
from mgear.core import icon


# =============================================================================
# Core Utility Functions
# =============================================================================


def get_name_index(name):
    """Get the last underscore-separated numeric token value from a name.

    Args:
        name (str): Node name to parse.

    Returns:
        tuple: (index_value, token_position, token_width) or (None, None, None)
            if no numeric token found.
    """
    parts = name.split("_")
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].isdigit():
            return int(parts[i]), i, len(parts[i])
    return None, None, None


def set_name_index(name, new_index):
    """Set the last underscore-separated numeric token to a new value.

    Args:
        name (str): Original node name.
        new_index (int): New index value to set.

    Returns:
        str: Name with updated index, or name + "_0" if no index found.
    """
    parts = name.split("_")
    idx = None
    width = 1

    for i in range(len(parts) - 1, -1, -1):
        if parts[i].isdigit():
            idx = i
            width = len(parts[i])
            break

    if idx is None:
        return name + "_" + str(new_index)

    parts[idx] = str(new_index).zfill(width)
    return "_".join(parts)


def find_chain_end(node):
    """Find the last locator in a chain starting from any node in the chain.

    Traverses down the hierarchy to find the deepest child that follows
    the same naming pattern.

    Args:
        node (str): Any node in the chain.

    Returns:
        tuple: (chain_end, parent_of_end) - The last node in the chain and its
            parent. Parent may be None if chain_end has no parent in the chain.
    """
    if not cmds.objExists(node):
        return node, None

    current = node
    parent = None

    while True:
        children = cmds.listRelatives(current, children=True,
                                       type="transform") or []
        if not children:
            break

        # Find child that continues the chain pattern
        next_node = None
        for child in children:
            child_short = child.split("|")[-1]
            child_index, _, _ = get_name_index(child_short)

            # Check if child follows the naming pattern (has numeric index)
            if child_index is not None:
                next_node = child
                break

        if next_node is None:
            break

        parent = current
        current = next_node

    # If we didn't traverse (parent is None), check the hierarchy parent
    # This handles the case where the selected node is already at the chain end
    if parent is None:
        hierarchy_parent = cmds.listRelatives(current, parent=True,
                                               type="transform")
        if hierarchy_parent:
            parent_short = hierarchy_parent[0].split("|")[-1]
            parent_index, _, _ = get_name_index(parent_short)
            # Only use as parent if it follows the naming pattern
            if parent_index is not None:
                parent = hierarchy_parent[0]

    return current, parent


def get_world_position(node):
    """Get the world space position of a node.

    Args:
        node (str): Node name.

    Returns:
        list: [x, y, z] world position.
    """
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def calculate_chain_offset(chain_end, chain_end_parent):
    """Calculate the offset for a new locator based on chain direction.

    Uses the vector from the parent to the chain end to determine
    the direction and distance for the new locator.

    Args:
        chain_end (str): The last node in the chain.
        chain_end_parent (str or None): The parent of the chain end.

    Returns:
        list: [x, y, z] offset to apply to the new locator, or [0, 0, 0]
            if no parent exists.
    """
    if chain_end_parent is None:
        return [0.0, 0.0, 0.0]

    # Get world positions
    end_pos = get_world_position(chain_end)
    parent_pos = get_world_position(chain_end_parent)

    # Calculate direction vector (parent -> end)
    offset = [
        end_pos[0] - parent_pos[0],
        end_pos[1] - parent_pos[1],
        end_pos[2] - parent_pos[2]
    ]

    return offset


# =============================================================================
# Display Curve Functions
# =============================================================================


def find_component_root(node):
    """Find the component root from any node in the component hierarchy.

    Traverses up the hierarchy to find the node ending with '_root' that
    has the 'isGearGuide' attribute.

    Args:
        node (str): Any node in the component.

    Returns:
        str or None: The component root node name, or None if not found.
    """
    current = node

    while current:
        short_name = current.split("|")[-1]

        # Check if this is a component root
        if short_name.endswith("_root"):
            if cmds.attributeQuery("isGearGuide", node=current, exists=True):
                return current

        # Move up the hierarchy
        parent = cmds.listRelatives(current, parent=True, type="transform")
        if not parent:
            break
        current = parent[0]

    return None


def find_display_curve(component_root):
    """Find the display curve for a component.

    Looks for a curve named *_crv under the component root.

    Args:
        component_root (str): The component root node.

    Returns:
        str or None: The display curve transform name, or None if not found.
    """
    if not component_root:
        return None

    # Get all descendants under the component root
    children = cmds.listRelatives(component_root, allDescendents=True,
                                   type="transform") or []

    for child in children:
        short_name = child.split("|")[-1]
        if short_name.endswith("_crv"):
            # Verify it has a curve shape
            shapes = cmds.listRelatives(child, shapes=True,
                                         type="nurbsCurve") or []
            if shapes:
                return child

    return None


def find_curve_cns_node(curve_transform):
    """Find the mgear_curveCns node driving a display curve.

    Args:
        curve_transform (str): Display curve transform name.

    Returns:
        str or None: The mgear_curveCns node name, or None if not found.
    """
    shapes = cmds.listRelatives(curve_transform, shapes=True,
                                 type="nurbsCurve") or []
    if not shapes:
        return None

    # Get history of the shape
    history = cmds.listHistory(shapes[0], pruneDagObjects=True) or []

    for node in history:
        if cmds.nodeType(node) == "mgear_curveCns":
            return node

    return None


def get_curve_cns_inputs(curve_cns_node):
    """Get the input transforms connected to a mgear_curveCns node.

    Args:
        curve_cns_node (str): The mgear_curveCns node name.

    Returns:
        list[str]: List of connected transform names in order.
    """
    inputs = []
    index = 0

    while True:
        attr = "{}.inputs[{}]".format(curve_cns_node, index)
        if not cmds.objExists(attr):
            break

        connections = cmds.listConnections(attr, source=True,
                                            destination=False) or []
        if connections:
            inputs.append(connections[0])

        index += 1

    return inputs


def collect_chain_locators(node):
    """Collect all locators in a chain from root to tip.

    Args:
        node (str): Any node in the chain.

    Returns:
        list[str]: List of locator names from root to tip.
    """
    # First, find the root of the chain by going up
    current = node
    while True:
        parent = cmds.listRelatives(current, parent=True,
                                     type="transform") or []
        if not parent:
            break

        parent_short = parent[0].split("|")[-1]
        parent_index, _, _ = get_name_index(parent_short)

        # If parent doesn't have a numeric index, we've reached the chain root
        if parent_index is None:
            break

        current = parent[0]

    chain_root = current

    # Now collect all locators from root to tip
    locators = [chain_root]

    current = chain_root
    while True:
        children = cmds.listRelatives(current, children=True,
                                       type="transform") or []
        if not children:
            break

        # Find child that continues the chain
        next_node = None
        for child in children:
            child_short = child.split("|")[-1]
            child_index, _, _ = get_name_index(child_short)

            if child_index is not None:
                next_node = child
                break

        if next_node is None:
            break

        locators.append(next_node)
        current = next_node

    return locators


def find_guide_model(node):
    """Find the guide model root from any node in the guide hierarchy.

    Traverses up the hierarchy to find the node with the 'ismodel' attribute.

    Args:
        node (str): Any node in the guide.

    Returns:
        str or None: The guide model root node name, or None if not found.
    """
    current = node

    while current:
        # Check if this is the guide model root
        if cmds.attributeQuery("ismodel", node=current, exists=True):
            return current

        # Move up the hierarchy
        parent = cmds.listRelatives(current, parent=True, type="transform")
        if not parent:
            break
        current = parent[0]

    return None


def connect_x_ray(curve_node, guide_model):
    """Connect the guide_x_ray attribute to the curve shapes.

    This replicates the behavior of guide.connect_x_ray method.

    Args:
        curve_node: The curve transform (PyNode or str).
        guide_model (str): The guide model root node name.
    """
    from mgear.pymaya import versions

    # Only for Maya 2022+
    if versions.current() < 20220000:
        return

    # Check if guide model has guide_x_ray attribute
    if not cmds.attributeQuery("guide_x_ray", node=guide_model, exists=True):
        return

    # Get curve as PyNode if it's a string
    if isinstance(curve_node, str):
        curve_node = pm.PyNode(curve_node)

    # Connect to each shape
    for shape in curve_node.getShapes():
        # Check if alwaysDrawOnTop is already connected
        if not shape.attr("alwaysDrawOnTop").listConnections():
            pm.connectAttr(
                "{}.guide_x_ray".format(guide_model),
                shape.attr("alwaysDrawOnTop")
            )


def regenerate_display_curve(node):
    """Regenerate the display curve for the chain containing the given node.

    Finds the component root, locates the display curve, and rebuilds it
    with all current chain locators.

    Args:
        node (str): Any node in the chain.

    Returns:
        str or None: The regenerated curve name, or None if failed.
    """
    # Find component root
    component_root = find_component_root(node)
    if not component_root:
        print("Warning: Could not find component root for: %s" % node)
        return None

    # Find existing display curve
    disp_curve = find_display_curve(component_root)
    if not disp_curve:
        print("Warning: No display curve found under: %s" % component_root)
        return None

    # Get the curve cns node
    curve_cns = find_curve_cns_node(disp_curve)
    if not curve_cns:
        print("Warning: No mgear_curveCns found for: %s" % disp_curve)
        return None

    # Collect all chain locators
    locators = collect_chain_locators(node)
    if len(locators) < 2:
        print("Warning: Need at least 2 locators for display curve")
        return None

    # Store curve properties before deleting
    try:
        line_width = cmds.getAttr("{}.lineWidth".format(disp_curve))
    except Exception:
        line_width = -1

    # Get curve degree from existing curve
    shapes = cmds.listRelatives(disp_curve, shapes=True,
                                 type="nurbsCurve") or []
    if shapes:
        degree = cmds.getAttr("{}.degree".format(shapes[0]))
    else:
        degree = 1

    # Store the curve name
    curve_name = disp_curve.split("|")[-1]

    # Delete the old curve
    cmds.delete(disp_curve)

    # Create new curve with updated locators using pymaya/icon
    pm_locators = [pm.PyNode(loc) for loc in locators]
    new_curve = icon.connection_display_curve(curve_name, pm_locators, degree)

    # Restore line width
    if line_width >= 0:
        try:
            new_curve.attr("lineWidth").set(line_width)
        except Exception:
            pass

    # Connect x-ray attribute (replicates guide.connect_x_ray behavior)
    guide_model = find_guide_model(node)
    if guide_model:
        connect_x_ray(new_curve, guide_model)

    return str(new_curve)


def add_locator_to_chain(nodes=None):
    """Add a new locator at the end of each selected chain.

    If a locator in the middle of the chain is selected, this function
    will find the end of the chain and add a new locator there with
    the correct incremented index. The new locator position is calculated
    based on the direction and distance from the previous locator to the
    chain end.

    Args:
        nodes (list[str] or None): Nodes to process. If None, the current
            selection (transforms) is used.

    Returns:
        list[tuple[str, str]]: List of (parent, new_node) name pairs.

    Raises:
        RuntimeError: If no valid nodes are provided.
    """
    if nodes is None:
        nodes = cmds.ls(sl=True, type="transform") or []

    if not nodes:
        raise RuntimeError("No transform selected or provided.")

    results = []
    processed_ends = set()

    for node in nodes:
        if not cmds.objExists(node):
            print("Warning: node not found, skipping: %s" % node)
            continue

        # Find the end of the chain and its parent
        chain_end, chain_end_parent = find_chain_end(node)

        # Skip if we already processed this chain end
        if chain_end in processed_ends:
            continue
        processed_ends.add(chain_end)

        # Calculate the offset for the new locator
        offset = calculate_chain_offset(chain_end, chain_end_parent)

        # Duplicate the chain end
        dup_list = cmds.duplicate(chain_end, rr=True)
        if not dup_list:
            print("Warning: could not duplicate: %s" % chain_end)
            continue

        dup = dup_list[0]

        # Get the current index and increment by 1
        short = chain_end.split("|")[-1]
        current_index, _, _ = get_name_index(short)

        if current_index is not None:
            new_index = current_index + 1
        else:
            new_index = 1

        new_name = set_name_index(short, new_index)

        # Handle name conflicts
        if cmds.objExists(new_name):
            # Find a unique name by incrementing further
            while cmds.objExists(new_name):
                new_index += 1
                new_name = set_name_index(short, new_index)

        new_name = cmds.rename(dup, new_name)

        # Parent the duplicate under the chain end
        cmds.parent(new_name, chain_end)

        # Apply the position offset to the new locator
        if offset != [0.0, 0.0, 0.0]:
            current_pos = get_world_position(new_name)
            new_pos = [
                current_pos[0] + offset[0],
                current_pos[1] + offset[1],
                current_pos[2] + offset[2]
            ]
            cmds.xform(new_name, worldSpace=True, translation=new_pos)

        results.append((chain_end, new_name))
        print("Added '%s' to chain (parented under '%s')"
              % (new_name, chain_end))

        # Connect x-ray attribute to the new locator
        guide_model = find_guide_model(new_name)
        if guide_model:
            connect_x_ray(new_name, guide_model)

        # Regenerate the display curve to include the new locator
        regenerate_display_curve(new_name)

    return results


# =============================================================================
# UI Dialog
# =============================================================================


class ChainUtilsDialog(QtWidgets.QDialog):
    """UI tool for chain manipulation utilities."""

    WINDOW_TITLE = "Chain Utilities"

    def __init__(self, parent=None):
        """Initialize dialog.

        Args:
            parent (QWidget, optional): Parent widget. Defaults to Maya main
                window.
        """
        if parent is None:
            parent = pyqt.maya_main_window()

        super(ChainUtilsDialog, self).__init__(parent)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setObjectName("mgear_chain_utils")
        self.setMinimumWidth(300)

        self._create_widgets()
        self._create_layout()
        self._create_connections()

    def _create_widgets(self):
        """Create UI widgets."""
        self.add_locator_group = QtWidgets.QGroupBox("Add Locator to Chain")

        self.add_locator_btn = QtWidgets.QPushButton("Add Locator")
        self.add_locator_btn.setToolTip(
            "Add a new locator at the end of the selected chain.\n\n"
            "Select any locator in a chain - the new locator will be\n"
            "added at the end with the correct incremented index."
        )

    def _create_layout(self):
        """Create UI layouts."""
        add_locator_layout = QtWidgets.QVBoxLayout(self.add_locator_group)
        add_locator_layout.addWidget(self.add_locator_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.add_locator_group)
        main_layout.addStretch()

    def _create_connections(self):
        """Connect signals and slots."""
        self.add_locator_btn.clicked.connect(self._on_add_locator)

    def _on_add_locator(self):
        """Handle add locator button click."""
        try:
            results = add_locator_to_chain()
            if results:
                # Select the newly created nodes
                new_nodes = [r[1] for r in results]
                cmds.select(new_nodes, r=True)
        except RuntimeError as exc:
            cmds.warning(str(exc))


# =============================================================================
# Entry Points
# =============================================================================


def open_chain_utils():
    """Open (or raise) the Chain Utilities UI.

    Returns:
        ChainUtilsDialog: The dialog instance.
    """
    return pyqt.showDialog(ChainUtilsDialog)


if __name__ == "__main__":
    open_chain_utils()
