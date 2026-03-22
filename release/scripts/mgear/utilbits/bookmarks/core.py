"""Bookmarks core logic.

Data model, scene storage, export/import, selection/isolate recall,
and shelf button generation. No UI code.
"""

import colorsys
import json
import logging
import random

import maya.mel as mel
from maya import cmds

from mgear.core.pyqt import get_icon_path

logger = logging.getLogger("mgear.utilbits.bookmarks")

#############################################
# CONSTANTS
#############################################

BOOKMARK_SELECTION = "selection"
BOOKMARK_ISOLATE = "isolate"
CONFIG_FILE_EXT = ".sbk"
CONFIG_VERSION = "1.0"
SCENE_NODE_NAME = "mgear_selection_bookmarks"
SCENE_NODE_TYPE_ATTR = "is_selection_bookmarks_data"
SCENE_NODE_DATA_ATTR = "bookmarks_data"

LAYOUT_NAMES = ("horizontal", "vertical", "grid")
LAYOUT_MAP = {name: i for i, name in enumerate(LAYOUT_NAMES)}


#############################################
# DATA MODEL
#############################################


def random_pastel_color():
    """Generate a random pastel color.

    Uses HSV with full hue range, low saturation, and high value
    to produce soft pastel tones.

    Returns:
        tuple: RGB 0-1 tuple.
    """
    h = random.random()
    s = random.uniform(0.25, 0.45)
    v = random.uniform(0.80, 0.95)
    return colorsys.hsv_to_rgb(h, s, v)


def create_bookmark(name, bookmark_type, items, color=None):
    """Create a bookmark dictionary.

    Args:
        name (str): Display name for the bookmark.
        bookmark_type (str): BOOKMARK_SELECTION or BOOKMARK_ISOLATE.
        items (list): List of Maya object or component names.
        color (tuple, optional): RGB 0-1 tuple. Random pastel if None.

    Returns:
        dict: Bookmark dictionary.
    """
    if color is None:
        color = random_pastel_color()
    return {
        "name": name,
        "color": list(color),
        "type": bookmark_type,
        "items": list(items),
    }


def bookmark_from_selection(name, bookmark_type, color=None):
    """Create a bookmark from the current Maya selection.

    Args:
        name (str): Display name for the bookmark.
        bookmark_type (str): BOOKMARK_SELECTION or BOOKMARK_ISOLATE.
        color (tuple, optional): RGB 0-1 tuple. Auto-assigned if None.

    Returns:
        dict: Bookmark dictionary, or None if nothing selected.
    """
    sel = cmds.ls(selection=True, long=True, flatten=True)
    if not sel:
        return None
    return create_bookmark(name, bookmark_type, sel, color)


def validate_bookmark_items(bookmark):
    """Filter bookmark items to only those that exist in the scene.

    Args:
        bookmark (dict): The bookmark to validate.

    Returns:
        list: Valid item names that exist in the current scene.
    """
    items = bookmark["items"]
    if not items:
        return []
    return cmds.ls(items, long=True) or []


def build_tooltip(bookmark):
    """Build a detailed tooltip string for a bookmark.

    Lists objects (truncated at 50) and summarizes components
    by type per object.

    Args:
        bookmark (dict): The bookmark dictionary.

    Returns:
        str: Multi-line tooltip text.
    """
    if bookmark["type"] == BOOKMARK_SELECTION:
        type_label = "Selection Bookmark"
    else:
        type_label = "Isolate Bookmark"

    items = bookmark["items"]
    objects = []
    components = {}
    for item in items:
        if "." in item and "[" in item:
            obj, comp = item.split(".", 1)
            comp_type = comp.split("[")[0]
            if obj not in components:
                components[obj] = {}
            components[obj].setdefault(comp_type, 0)
            components[obj][comp_type] += 1
        else:
            objects.append(item.rsplit("|", 1)[-1])

    lines = [type_label]
    lines.append("{} items total".format(len(items)))
    lines.append("")

    if objects:
        lines.append("Objects ({}):".format(len(objects)))
        for obj in objects[:50]:
            lines.append("  " + obj)
        if len(objects) > 50:
            lines.append("  ... +{} more".format(len(objects) - 50))

    if components:
        if objects:
            lines.append("")
        lines.append("Components:")
        for obj, types in sorted(components.items()):
            short = obj.rsplit("|", 1)[-1]
            parts = []
            for comp_type, count in sorted(types.items()):
                parts.append("{} {}".format(count, comp_type))
            lines.append("  {}: {}".format(short, ", ".join(parts)))

    return "\n".join(lines)


def text_color_for_background(color):
    """Determine readable text color for a given background.

    Uses relative luminance: 0.299*R + 0.587*G + 0.114*B.

    Args:
        color (tuple): RGB 0-1 tuple.

    Returns:
        tuple: (1, 1, 1) for white or (0.1, 0.1, 0.1) for dark.
    """
    luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
    if luminance > 0.5:
        return (0.1, 0.1, 0.1)
    return (1.0, 1.0, 1.0)


#############################################
# SELECTION LOGIC
#############################################


def recall_selection(bookmark, mode="replace"):
    """Recall a selection bookmark.

    Args:
        bookmark (dict): The bookmark dictionary.
        mode (str): "replace", "add", or "deselect".
    """
    valid = validate_bookmark_items(bookmark)
    if not valid:
        cmds.warning("No bookmark items found in scene")
        return
    if mode == "add":
        cmds.select(valid, add=True)
    elif mode == "deselect":
        cmds.select(valid, deselect=True)
    else:
        cmds.select(valid, replace=True)


def add_selected_to_bookmark(bookmark):
    """Add the current Maya selection to a bookmark's items.

    Args:
        bookmark (dict): The bookmark dictionary to modify.

    Returns:
        int: Number of items added.
    """
    sel = cmds.ls(selection=True, long=True, flatten=True)
    if not sel:
        return 0
    existing = set(bookmark["items"])
    new_items = [i for i in sel if i not in existing]
    bookmark["items"].extend(new_items)
    return len(new_items)


def remove_selected_from_bookmark(bookmark):
    """Remove the current Maya selection from a bookmark's items.

    Args:
        bookmark (dict): The bookmark dictionary to modify.

    Returns:
        int: Number of items removed.
    """
    sel = set(cmds.ls(selection=True, long=True, flatten=True) or [])
    if not sel:
        return 0
    original_count = len(bookmark["items"])
    bookmark["items"] = [i for i in bookmark["items"] if i not in sel]
    return original_count - len(bookmark["items"])


#############################################
# ISOLATE LOGIC
#############################################


def toggle_isolate(bookmark):
    """Toggle isolate visibility for bookmark items in the active viewport.

    For components, extracts parent transforms to isolate the objects
    and selects the components so Maya displays them in isolate mode.
    Uses enableIsolateSelect MEL command to properly sync the viewport
    toolbar button.

    Args:
        bookmark (dict): The bookmark dictionary.
    """
    valid = validate_bookmark_items(bookmark)
    if not valid:
        cmds.warning("No bookmark items found in scene")
        return

    panel = _get_active_model_panel()
    if not panel:
        cmds.warning("No active model panel found")
        return

    is_isolated = cmds.isolateSelect(panel, query=True, state=True)
    if is_isolated:
        mel.eval("enableIsolateSelect {} {}".format(panel, 0))
    else:
        # Store current selection to restore for object-only bookmarks
        prev_sel = cmds.ls(selection=True, long=True) or []

        # Select bookmark items, then isolate with addSelectedObjects
        # This handles both objects and components natively
        cmds.select(valid, replace=True)
        mel.eval("enableIsolateSelect {} {}".format(panel, 1))
        cmds.isolateSelect(panel, addSelectedObjects=True)

        # For object-only bookmarks, restore previous selection
        has_components = any(
            "." in item and "[" in item for item in valid
        )
        if not has_components:
            if prev_sel:
                cmds.select(prev_sel, replace=True)
            else:
                cmds.select(clear=True)


def _get_active_model_panel():
    """Get the active model panel name.

    Returns:
        str: Model panel name, or None if none found.
    """
    panel = cmds.getPanel(withFocus=True)
    if panel and cmds.getPanel(typeOf=panel) == "modelPanel":
        return panel
    panels = cmds.getPanel(type="modelPanel") or []
    return panels[0] if panels else None


#############################################
# CONFIGURATION
#############################################


def bookmarks_to_config(bookmarks, layout="horizontal"):
    """Convert bookmarks list to exportable config dictionary.

    Args:
        bookmarks (list): List of bookmark dicts.
        layout (str): Layout mode.

    Returns:
        dict: Configuration dictionary.
    """
    return {
        "version": CONFIG_VERSION,
        "layout": layout,
        "bookmarks": [
            {
                "name": bm["name"],
                "color": list(bm["color"]),
                "type": bm["type"],
                "items": list(bm["items"]),
            }
            for bm in bookmarks
        ],
    }


def config_to_bookmarks(config):
    """Extract bookmarks list and layout from config dictionary.

    Args:
        config (dict): Configuration dictionary.

    Returns:
        tuple: (list of bookmark dicts, layout string).
    """
    bookmarks = config.get("bookmarks", [])
    layout = config.get("layout", "horizontal")
    return bookmarks, layout


#############################################
# EXPORT / IMPORT
#############################################


def export_bookmarks(file_path, bookmarks, layout="horizontal"):
    """Export bookmarks to a JSON file.

    Args:
        file_path (str): Path to save the .sbk file.
        bookmarks (list): List of bookmark dicts.
        layout (str): Current layout mode.

    Returns:
        bool: True if successful.
    """
    if not file_path.endswith(CONFIG_FILE_EXT):
        file_path += CONFIG_FILE_EXT
    config = bookmarks_to_config(bookmarks, layout)
    try:
        with open(file_path, "w") as f:
            json.dump(config, f, indent=2)
        logger.info("Exported bookmarks to %s", file_path)
        return True
    except Exception as e:
        cmds.warning("Failed to export bookmarks: {}".format(e))
        return False


def import_bookmarks(file_path):
    """Import bookmarks from a JSON file.

    Args:
        file_path (str): Path to the .sbk file.

    Returns:
        dict: Configuration dictionary, or None if failed.
    """
    try:
        with open(file_path, "r") as f:
            config = json.load(f)
        logger.info("Imported bookmarks from %s", file_path)
        return config
    except Exception as e:
        cmds.warning("Failed to import bookmarks: {}".format(e))
        return None


#############################################
# SCENE STORAGE
#############################################

# Cache to avoid scanning all network nodes on every save
_scene_node_cache = None


def save_to_scene(bookmarks, layout="horizontal"):
    """Save bookmarks to a network node in the Maya scene.

    Creates or updates the network node with JSON-serialized data.

    Args:
        bookmarks (list): List of bookmark dicts.
        layout (str): Current layout mode.

    Returns:
        bool: True if successful.
    """
    config = bookmarks_to_config(bookmarks, layout)
    try:
        node = _get_or_create_scene_node()
        cmds.setAttr(
            "{}.{}".format(node, SCENE_NODE_DATA_ATTR),
            json.dumps(config),
            type="string",
        )
        return True
    except Exception as e:
        cmds.warning("Failed to save bookmarks to scene: {}".format(e))
        return False


def load_from_scene():
    """Load bookmarks from the scene's network node.

    Returns:
        dict: Configuration dictionary, or None if no node exists.
    """
    node = _find_scene_node()
    if not node:
        return None
    try:
        data = cmds.getAttr("{}.{}".format(node, SCENE_NODE_DATA_ATTR))
        if not data:
            return None
        return json.loads(data)
    except Exception as e:
        cmds.warning("Failed to load bookmarks from scene: {}".format(e))
        return None


def _get_or_create_scene_node():
    """Get existing or create new network node for storage.

    Returns:
        str: The network node name.
    """
    node = _find_scene_node()
    if node:
        return node
    node = cmds.createNode("network", name=SCENE_NODE_NAME)
    cmds.addAttr(
        node,
        longName=SCENE_NODE_TYPE_ATTR,
        attributeType="bool",
        defaultValue=True,
    )
    cmds.addAttr(node, longName=SCENE_NODE_DATA_ATTR, dataType="string")
    global _scene_node_cache
    _scene_node_cache = node
    return node


def _find_scene_node():
    """Find the bookmarks network node in the scene.

    Uses cached name first, falls back to scanning network nodes.

    Returns:
        str: Node name, or None if not found.
    """
    global _scene_node_cache
    if _scene_node_cache and cmds.objExists(_scene_node_cache):
        return _scene_node_cache

    # Fast path: check well-known name
    if cmds.objExists(SCENE_NODE_NAME):
        if cmds.attributeQuery(
            SCENE_NODE_TYPE_ATTR, node=SCENE_NODE_NAME, exists=True
        ):
            _scene_node_cache = SCENE_NODE_NAME
            return SCENE_NODE_NAME

    # Slow path: scan all network nodes (handles renamed nodes)
    for node in cmds.ls(type="network") or []:
        if cmds.attributeQuery(
            SCENE_NODE_TYPE_ATTR, node=node, exists=True
        ):
            _scene_node_cache = node
            return node
    return None


#############################################
# SHELF
#############################################


def add_bookmark_to_shelf(bookmark):
    """Add a bookmark as a button on Maya's current shelf.

    The shelf button calls core functions directly via a compact
    Python command.

    Args:
        bookmark (dict): The bookmark dictionary.

    Returns:
        str: The shelf button name, or None if failed.
    """
    try:
        current_shelf = mel.eval(
            "tabLayout -query -selectTab $gShelfTopLevel"
        )
    except Exception:
        cmds.warning("Could not find current shelf")
        return None

    name = bookmark["name"]
    r, g, b = bookmark["color"]
    bm_data = json.dumps(bookmark)
    is_selection = bookmark["type"] == BOOKMARK_SELECTION

    command = (
        "from mgear.utilbits.bookmarks import core\n"
        "import json\n"
        "bm = json.loads({data!r})\n"
    ).format(data=bm_data)

    if is_selection:
        command += (
            "import maya.cmds as cmds\n"
            "mods = cmds.getModifiers()\n"
            "if mods & 1:\n"
            "    core.recall_selection(bm, 'add')\n"
            "elif mods & 4:\n"
            "    core.recall_selection(bm, 'deselect')\n"
            "else:\n"
            "    core.recall_selection(bm, 'replace')\n"
        )
        icon = get_icon_path("mgear_mouse-pointer.svg")
    else:
        command += "core.toggle_isolate(bm)\n"
        icon = get_icon_path("mgear_eye.svg")

    btn = cmds.shelfButton(
        parent=current_shelf,
        label=name,
        annotation=build_tooltip(bookmark),
        imageOverlayLabel=name,
        image1=icon,
        overlayLabelColor=[0, 0, 0],
        overlayLabelBackColor=list(bookmark["color"]) + [0.5],
        command=command,
        sourceType="python",
        backgroundColor=[r, g, b],
    )
    return btn
