"""Blendshape Transfer - Config I/O and execution wrapper.

Handles saving/loading .bst configuration files and provides
a convenience wrapper to run transfer_blendshapes from a config.
"""

import datetime
import getpass
import json

from maya import cmds

from mgear.core import blendshape


# Config file extension
BST_EXT = ".bst"


def export_config(
    filepath, target, sources, bs_node_name=None,
    reconnect=True, metadata=None,
):
    """Save a blendshape transfer configuration to disk.

    Args:
        filepath (str): Path to save the .bst JSON file.
        target (str): Target mesh name.
        sources (list): List of source mesh names.
        bs_node_name (str, optional): BlendShape node name.
        reconnect (bool, optional): Reconnect flag.
        metadata (dict, optional): Extra metadata fields
            (name, description, tags).

    Returns:
        bool: True if successful.
    """
    meta = metadata or {}
    now = datetime.datetime.now().strftime("%Y-%m-%d")

    config = {
        "version": 1,
        "name": meta.get("name", ""),
        "description": meta.get("description", ""),
        "author": meta.get("author", getpass.getuser()),
        "date": now,
        "tags": meta.get("tags", []),
        "target_mesh": target,
        "source_meshes": list(sources),
        "bs_node_name": bs_node_name or "",
        "reconnect": reconnect,
    }

    try:
        with open(filepath, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except (IOError, OSError) as e:
        cmds.warning(
            "Failed to export config: {}".format(e)
        )
        return False


def import_config(filepath):
    """Load a blendshape transfer configuration from disk.

    Args:
        filepath (str): Path to the .bst JSON file.

    Returns:
        dict: Configuration dictionary, or None on failure.
    """
    try:
        with open(filepath, "r") as f:
            config = json.load(f)
        return config
    except (IOError, ValueError, OSError) as e:
        cmds.warning(
            "Failed to import config: {}".format(e)
        )
        return None


def run_from_config(config):
    """Execute blendshape transfer from a configuration dict.

    Args:
        config (dict): Configuration with keys
            ``target_mesh``, ``source_meshes``, and optionally
            ``bs_node_name`` and ``reconnect``.

    Returns:
        str: The created blendShape node name, or None.
    """
    target = config.get("target_mesh")
    sources = config.get("source_meshes", [])

    if not target or not sources:
        cmds.warning(
            "Config must have target_mesh and source_meshes"
        )
        return None

    bs_name = config.get("bs_node_name") or None
    reconnect = config.get("reconnect", True)

    return blendshape.transfer_blendshapes(
        sources=sources,
        target=target,
        bs_node_name=bs_name,
        reconnect=reconnect,
    )
