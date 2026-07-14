"""Qt/Maya-free shape library for picker items.

A library shape is one of two kinds:

- **polygon** -- a named list of handle points (``[[x, y], ...]``, the same
  a ``PickerItem`` stores); applying it is just ``set_handles``.
- **vector** -- curved subpaths, either a bundled ``.svg`` template (parsed via
  ``mgear.core.svg_import``) or a saved vector item's subpaths; applying it is
  ``set_svg_shape``.

Two sources are merged:

- **bundled** premade shapes shipped next to the package: polygon entries in
  ``anim_picker/shapes/default_shapes.json`` (an entry may name an ``.svg``
  template in the same folder), read-only;
- **user** shapes saved to ``mGear_anim_picker_shapes.json`` in the Maya user
  preferences directory (alongside ``mGear_user_settings.ini``), editable.

No hard Qt or Maya dependency (Maya is imported lazily only to resolve the
prefs dir, ``svg_import`` lazily only to parse a bundled template), so the
load/save round-trip is unit-testable; the Qt picker UI lives in
``widgets/dialogs/shape_library_dialog.py``.
"""

import os
import json


_USER_SHAPES_FILE = "mGear_anim_picker_shapes.json"

# Drag-and-drop mime type carrying a shape *name* from a library tile to the
# canvas; the view resolves the name and creates the item at the drop point.
SHAPE_MIME = "application/x-mgear-anim-picker-shape"

# Resolved shape kinds.
KIND_POLYGON = "polygon"
KIND_VECTOR = "vector"

# Default vector render mode (kept in sync with svg_import.MODE_FILL so the
# heavy import stays lazy).
_DEFAULT_MODE = "fill"

# Cache of parsed bundled ``.svg`` templates: {filename: (subpaths, mode)}.
_SVG_CACHE = {}


def bundled_shapes_path():
    """Return the path to the bundled default shapes JSON."""
    here = os.path.dirname(__file__)
    return os.path.join(
        os.path.dirname(here), "shapes", "default_shapes.json"
    )


def _user_prefs_dir():
    """Return the Maya user prefs dir (mGear convention), or a home fallback."""
    try:
        from maya import cmds

        return cmds.internalVar(userPrefDir=True)
    except Exception:
        return os.path.join(os.path.expanduser("~"), "mgear")


def user_shapes_path():
    """Return the path to the user's custom shapes JSON (Maya prefs dir)."""
    return os.path.join(_user_prefs_dir(), _USER_SHAPES_FILE)


def _legacy_user_shapes_path():
    """Return the pre-5.3.4 shapes location (migrated on first load)."""
    return os.path.join(
        os.path.expanduser("~"), "mgear", "anim_picker", "user_shapes.json"
    )


def _shapes_dir():
    """Return the bundled shapes directory (holds JSON + .svg templates)."""
    return os.path.dirname(bundled_shapes_path())


def _read_raw_shapes(path):
    """Read a shapes JSON, returning raw entries ([] on missing / invalid).

    An entry is kept when it has a name and one geometry field: ``handles``
    (polygon), ``subpaths`` (a saved vector) or ``svg`` (a bundled .svg name).
    The raw entry is preserved so the user file round-trips both kinds.
    """
    if not (path and os.path.exists(path)):
        return []
    try:
        with open(path, "r") as shape_file:
            data = json.load(shape_file)
    except (ValueError, IOError):
        return []
    shapes = []
    for entry in data or []:
        if not entry.get("name"):
            continue
        if entry.get("handles") or entry.get("subpaths") or entry.get("svg"):
            shapes.append(entry)
    return shapes


def _load_bundled_svg(svg_name):
    """Parse a bundled ``.svg`` template into ``(subpaths, mode)``, cached.

    Returns None when the file is missing or has no supported geometry, so a
    bad template is skipped rather than fatal.
    """
    if svg_name in _SVG_CACHE:
        return _SVG_CACHE[svg_name]
    result = None
    path = os.path.join(_shapes_dir(), svg_name)
    try:
        with open(path, "r") as svg_file:
            text = svg_file.read()
    except (IOError, OSError):
        text = None
    if text:
        # svg_import is Qt/Maya-free; import it lazily so the module load stays
        # light. flip_y: templates are authored y-down (SVG) and the picker
        # scene is y-up, matching how dropped .svg files are imported.
        from mgear.core import svg_import

        subpaths, _dropped, mode = svg_import.parse_svg(text, flip_y=True)
        if subpaths:
            result = (subpaths, mode)
    _SVG_CACHE[svg_name] = result
    return result


def _resolve_entry(entry, builtin):
    """Resolve a raw entry to a normalized shape (with ``kind``), or None.

    Args:
        entry (dict): a raw entry (``handles`` / ``subpaths`` / ``svg``).
        builtin (bool): True for a bundled entry.

    Returns:
        dict: ``{name, kind, builtin, ...geometry}`` or None when unresolvable.
    """
    name = entry.get("name")
    if not name:
        return None
    resolved = {"name": name, "builtin": builtin}
    if entry.get("handles"):
        resolved.update(kind=KIND_POLYGON, handles=entry["handles"])
        return resolved
    if entry.get("subpaths"):
        resolved.update(
            kind=KIND_VECTOR,
            subpaths=entry["subpaths"],
            mode=entry.get("mode", _DEFAULT_MODE),
        )
        return resolved
    svg_name = entry.get("svg")
    if svg_name:
        parsed = _load_bundled_svg(svg_name)
        if parsed is not None:
            subpaths, mode = parsed
            resolved.update(kind=KIND_VECTOR, subpaths=subpaths, mode=mode)
            return resolved
    return None


def load_bundled_shapes():
    """Return the raw bundled shape entries."""
    return _read_raw_shapes(bundled_shapes_path())


def load_user_shapes():
    """Return the user's raw saved shape entries.

    Reads from the Maya prefs dir; on first run, a pre-existing legacy file
    (``~/mgear/anim_picker/user_shapes.json``) is migrated to the new location.
    """
    path = user_shapes_path()
    if os.path.exists(path):
        return _read_raw_shapes(path)
    legacy = _read_raw_shapes(_legacy_user_shapes_path())
    if legacy:
        try:
            _write_user_shapes(legacy)
        except (IOError, OSError):
            pass
    return legacy


def load_shapes():
    """Return all shapes resolved to normalized entries (with ``kind``).

    Each entry has ``name``, ``kind`` (polygon / vector), the geometry
    (``handles`` or ``subpaths`` + ``mode``) and ``builtin`` (bundled) flag.
    Entries that fail to resolve (e.g. a missing / empty ``.svg``) are skipped.
    """
    sources = [(entry, True) for entry in load_bundled_shapes()]
    sources += [(entry, False) for entry in load_user_shapes()]
    shapes = []
    for entry, builtin in sources:
        resolved = _resolve_entry(entry, builtin)
        if resolved is not None:
            shapes.append(resolved)
    return shapes


def get_shape(name):
    """Return the resolved shape named ``name`` (bundled or user), or None."""
    for shape in load_shapes():
        if shape["name"] == name:
            return shape
    return None


def _write_user_shapes(shapes):
    """Write the user shapes list to disk, creating the directory."""
    path = user_shapes_path()
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w") as shape_file:
        json.dump(shapes, shape_file, indent=2)


def save_user_shape(name, handles=None, subpaths=None, mode=None):
    """Add or replace a user shape by name (polygon handles or vector).

    Args:
        name (str): shape name.
        handles (list, optional): ``[[x, y], ...]`` for a polygon shape.
        subpaths (list, optional): subpaths for a vector shape.
        mode (str, optional): vector render mode (fill / stroke).

    Returns:
        bool: True on success.
    """
    if not name:
        return False
    if handles:
        entry = {"name": name, "handles": handles}
    elif subpaths:
        entry = {
            "name": name,
            "subpaths": subpaths,
            "mode": mode or _DEFAULT_MODE,
        }
    else:
        return False
    shapes = load_user_shapes()
    shapes = [shape for shape in shapes if shape.get("name") != name]
    shapes.append(entry)
    _write_user_shapes(shapes)
    return True


def remove_user_shape(name):
    """Remove a user shape by name. Returns True if one was removed."""
    shapes = load_user_shapes()
    kept = [shape for shape in shapes if shape.get("name") != name]
    if len(kept) == len(shapes):
        return False
    _write_user_shapes(kept)
    return True
