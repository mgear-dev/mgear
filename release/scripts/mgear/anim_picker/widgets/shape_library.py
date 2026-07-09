"""Qt/Maya-free shape library for picker items.

A shape is a named list of handle coordinates -- the same ``[[x, y], ...]`` a
``PickerItem`` stores -- so applying a library shape is just ``set_handles`` and
saving one is just reading ``get_data()["handles"]``. Two sources are merged:

- **bundled** premade shapes shipped as JSON next to the package
  (``anim_picker/shapes/default_shapes.json``), read-only;
- **user** shapes saved to ``mGear_anim_picker_shapes.json`` in the Maya user
  preferences directory (alongside ``mGear_user_settings.ini``), editable.

No hard Qt or Maya dependency (Maya is imported lazily only to resolve the
prefs dir, with a home-dir fallback), so the load/save round-trip is
unit-testable; the Qt picker UI lives in
``widgets/dialogs/shape_library_dialog.py``.
"""

import os
import json


_USER_SHAPES_FILE = "mGear_anim_picker_shapes.json"


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


def _read_shapes(path):
    """Read a shapes JSON file, returning [] on missing / invalid content."""
    if not (path and os.path.exists(path)):
        return []
    try:
        with open(path, "r") as shape_file:
            data = json.load(shape_file)
    except (ValueError, IOError):
        return []
    shapes = []
    for entry in data or []:
        name = entry.get("name")
        handles = entry.get("handles")
        if name and handles:
            shapes.append({"name": name, "handles": handles})
    return shapes


def load_bundled_shapes():
    """Return the bundled premade shapes."""
    return _read_shapes(bundled_shapes_path())


def load_user_shapes():
    """Return the user's saved custom shapes.

    Reads from the Maya prefs dir; on first run, a pre-existing legacy file
    (``~/mgear/anim_picker/user_shapes.json``) is migrated to the new location.
    """
    path = user_shapes_path()
    if os.path.exists(path):
        return _read_shapes(path)
    legacy = _read_shapes(_legacy_user_shapes_path())
    if legacy:
        try:
            _write_user_shapes(legacy)
        except (IOError, OSError):
            pass
    return legacy


def load_shapes():
    """Return all shapes, each tagged ``builtin`` (bundled) True/False."""
    shapes = []
    for shape in load_bundled_shapes():
        shapes.append(
            {
                "name": shape["name"],
                "handles": shape["handles"],
                "builtin": True,
            }
        )
    for shape in load_user_shapes():
        shapes.append(
            {
                "name": shape["name"],
                "handles": shape["handles"],
                "builtin": False,
            }
        )
    return shapes


def _write_user_shapes(shapes):
    """Write the user shapes list to disk, creating the directory."""
    path = user_shapes_path()
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w") as shape_file:
        json.dump(shapes, shape_file, indent=2)


def save_user_shape(name, handles):
    """Add or replace a user shape by name.

    Args:
        name (str): shape name.
        handles (list): list of ``[x, y]``.

    Returns:
        bool: True on success.
    """
    if not (name and handles):
        return False
    shapes = load_user_shapes()
    shapes = [shape for shape in shapes if shape["name"] != name]
    shapes.append({"name": name, "handles": handles})
    _write_user_shapes(shapes)
    return True


def remove_user_shape(name):
    """Remove a user shape by name. Returns True if one was removed."""
    shapes = load_user_shapes()
    kept = [shape for shape in shapes if shape["name"] != name]
    if len(kept) == len(shapes):
        return False
    _write_user_shapes(kept)
    return True
