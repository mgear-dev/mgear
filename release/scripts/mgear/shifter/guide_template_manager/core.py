"""Guide Template Manager - Core logic.

Folder scanning, metadata I/O, viewport capture, and component
extraction for the guide template manager.
"""

import datetime
import getpass
import json
import os

from maya import cmds

from mgear.shifter import io as shifter_io

# Sidecar file extensions
SGTINFO_EXT = ".sgtInfo"
THUMBNAIL_EXT = ".png"
SGT_EXT = ".sgt"

# Default thumbnail dimensions
THUMBNAIL_SIZE = (256, 256)


# =================================================================
# PATHS
# =================================================================


def get_default_templates_dir():
    """Get the path to the built-in default templates directory.

    Returns:
        str: Absolute path to ``shifter/component/_templates/``.
    """
    shifter_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(shifter_dir, "component", "_templates")


def get_sgt_info_path(sgt_path):
    """Get the .sgtInfo sidecar path for a given .sgt file.

    Args:
        sgt_path (str): Path to the .sgt file.

    Returns:
        str: Path to the corresponding .sgtInfo file.
    """
    base = os.path.splitext(sgt_path)[0]
    return base + SGTINFO_EXT


def get_thumbnail_path(sgt_path):
    """Get the expected thumbnail path for a given .sgt file.

    Args:
        sgt_path (str): Path to the .sgt file.

    Returns:
        str: Path to the corresponding .png file.
    """
    base = os.path.splitext(sgt_path)[0]
    return base + THUMBNAIL_EXT


# =================================================================
# FOLDER SCANNING
# =================================================================


class TemplateEntry:
    """Represents a single .sgt template file with its sidecar status.

    Args:
        sgt_path (str): Full path to the .sgt file.
    """

    def __init__(self, sgt_path):
        self.sgt_path = sgt_path
        self.name = os.path.splitext(os.path.basename(sgt_path))[0]
        self.has_info = os.path.isfile(get_sgt_info_path(sgt_path))
        self.info = None


class FolderEntry:
    """Represents a folder containing template files.

    Args:
        path (str): Full path to the folder.
        label (str): Display label for the folder.
    """

    def __init__(self, path, label=None):
        self.path = path
        self.label = label or os.path.basename(path)
        self.templates = []
        self.subfolders = []


def scan_template_folders(folder_paths):
    """Scan a list of folders for .sgt template files.

    Walks each folder recursively, building a tree of
    ``FolderEntry`` objects containing ``TemplateEntry`` leaves.

    Args:
        folder_paths (list): List of folder path strings.

    Returns:
        list: List of FolderEntry root nodes.
    """
    roots = []
    for folder_path in folder_paths:
        if not os.path.isdir(folder_path):
            continue
        root = _scan_folder(folder_path)
        if root:
            roots.append(root)
    return roots


def _scan_folder(folder_path, label=None):
    """Recursively scan a single folder.

    Args:
        folder_path (str): Folder to scan.
        label (str): Optional display label.

    Returns:
        FolderEntry: The folder entry, or None if empty.
    """
    entry = FolderEntry(folder_path, label)

    try:
        items = sorted(os.listdir(folder_path))
    except OSError:
        return None

    for item in items:
        full_path = os.path.join(folder_path, item)
        if os.path.isdir(full_path):
            subfolder = _scan_folder(full_path)
            if subfolder:
                entry.subfolders.append(subfolder)
        elif item.lower().endswith(SGT_EXT):
            entry.templates.append(TemplateEntry(full_path))

    if entry.templates or entry.subfolders:
        return entry
    return None


def ensure_all_sgt_info(folder_entries):
    """Ensure .sgtInfo exists for all templates and cache the result.

    Runs before tree population so cached info is available
    for tag extraction without redundant file reads.

    Args:
        folder_entries (list): List of FolderEntry objects.
    """
    for folder in folder_entries:
        for template in folder.templates:
            template.info = ensure_sgt_info(template.sgt_path)
        for subfolder in folder.subfolders:
            ensure_all_sgt_info([subfolder])


# =================================================================
# METADATA I/O
# =================================================================


def read_sgt_info(sgt_path):
    """Read the .sgtInfo metadata for a template.

    Args:
        sgt_path (str): Path to the .sgt file.

    Returns:
        dict: Metadata dictionary, or None if not found.
    """
    info_path = get_sgt_info_path(sgt_path)
    try:
        with open(info_path, "r") as f:
            return json.load(f)
    except (IOError, ValueError, OSError):
        return None


def write_sgt_info(sgt_path, info_dict):
    """Write metadata to the .sgtInfo sidecar file.

    Args:
        sgt_path (str): Path to the .sgt file.
        info_dict (dict): Metadata dictionary to write.

    Returns:
        bool: True if successful.
    """
    info_path = get_sgt_info_path(sgt_path)
    try:
        with open(info_path, "w") as f:
            json.dump(info_dict, f, indent=2)
        return True
    except (IOError, OSError):
        return False


def generate_sgt_info(sgt_path):
    """Auto-generate a minimal .sgtInfo from the .sgt content.

    Reads the template to extract component count and list.

    Args:
        sgt_path (str): Path to the .sgt file.

    Returns:
        dict: Generated metadata dictionary.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    info = {
        "version": 1,
        "name": os.path.splitext(os.path.basename(sgt_path))[0],
        "description": "",
        "author": getpass.getuser(),
        "date_created": now,
        "date_modified": now,
        "tags": [],
        "components_count": 0,
        "components_list": [],
        "thumbnail": "",
    }

    try:
        conf = shifter_io._import_guide_template(sgt_path)
        if conf:
            comp_list = conf.get("components_list", [])
            info["components_count"] = len(comp_list)
            info["components_list"] = comp_list
    except Exception as e:
        cmds.warning(
            "读取模板失败：{}：{}".format(sgt_path, e)
        )

    return info


def ensure_sgt_info(sgt_path):
    """Ensure a .sgtInfo file exists for the given template.

    If the sidecar doesn't exist, generates and writes one.
    Silently skips if the folder is read-only.

    Args:
        sgt_path (str): Path to the .sgt file.

    Returns:
        dict: The metadata dictionary.
    """
    existing = read_sgt_info(sgt_path)
    if existing:
        return existing

    info = generate_sgt_info(sgt_path)
    write_sgt_info(sgt_path, info)
    return info


# =================================================================
# VIEWPORT CAPTURE
# =================================================================


def capture_viewport_thumbnail(save_path, width=None, height=None):
    """Capture the active 3D viewport as a thumbnail image.

    Args:
        save_path (str): Full path to save the PNG file.
        width (int): Image width in pixels.
        height (int): Image height in pixels.

    Returns:
        str: The saved file path, or None if capture failed.
    """
    if width is None:
        width = THUMBNAIL_SIZE[0]
    if height is None:
        height = THUMBNAIL_SIZE[1]

    try:
        current_frame = cmds.currentTime(query=True)
        result = cmds.playblast(
            frame=current_frame,
            format="image",
            compression="png",
            completeFilename=save_path,
            widthHeight=[width, height],
            percent=100,
            viewer=False,
            showOrnaments=False,
            offScreen=True,
        )
        if result:
            return save_path
    except Exception as e:
        cmds.warning(
            "视口捕获失败：{}".format(str(e))
        )
    return None


# =================================================================
# COMPONENT EXTRACTION
# =================================================================


def get_components_from_template(sgt_path):
    """Extract component information from a template file.

    Args:
        sgt_path (str): Path to the .sgt file.

    Returns:
        list: List of dicts with keys: name, comp_type,
            parent, children. Returns empty list on failure.
    """
    try:
        conf = shifter_io._import_guide_template(sgt_path)
    except Exception as e:
        cmds.warning(
            "读取模板失败：{}：{}".format(sgt_path, e)
        )
        return []

    if not conf:
        return []

    return _extract_components(conf)


def _extract_components(conf):
    """Extract component data from a template config dict.

    Args:
        conf (dict): Template configuration dictionary.

    Returns:
        list: List of component info dicts.
    """
    components = []
    comp_dict = conf.get("components_dict", {})
    comp_list = conf.get("components_list", [])

    for name in comp_list:
        comp_data = comp_dict.get(name, {})
        params = comp_data.get("param_values", {})
        components.append({
            "name": name,
            "comp_type": params.get("comp_type", "unknown"),
            "parent": comp_data.get("parent_fullName"),
            "children": comp_data.get("child_components", []),
        })

    return components
