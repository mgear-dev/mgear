"""Shrink Wrap IO - Main UI Module.

Dockable window to export and import shrinkWrap configurations, built on
the shared :class:`mgear.rigbits.deformer_io_ui.DeformerIOUI`.
"""

from mgear.core import deformer
from mgear.core import deformer_io
from mgear.core import node_remap

from mgear.rigbits.deformer_io_ui import DeformerIOUI

from . import core


class ShrinkWrapIOUI(DeformerIOUI):
    """Dockable dialog to export and import shrink wrap configurations."""

    TOOL_NAME = "ShrinkWrapIO"
    toolName = TOOL_NAME
    TOOL_TITLE = "Shrink Wrap IO"
    FORMAT = core.FORMAT
    FILE_LABEL = "mGear Shrink Wrap Config"
    SETTINGS_PREFIX = "shrinkwrap_io"
    NAME_COLUMN = "Shrink Wrap"
    EXTRA_COLUMN = "Target"

    def scene_nodes(self):
        """Return the shrinkWrap deformers in the scene.

        Returns:
            list: shrinkWrap names.
        """
        return core.get_shrinkwrap_nodes()

    def scene_label(self, node):
        """Return the Export list label: name, target and geometry count.

        Args:
            node (str): shrinkWrap name.

        Returns:
            str: Label.
        """
        transform = core.get_target(node)[0]
        return "{}   (target: {}, {} geo)".format(
            node,
            node_remap.leaf_name(transform) if transform else "none",
            len(deformer.get_deformer_geometry(node)),
        )

    def find_from_selection(self, nodes):
        """Return the shrinkWraps related to the selected nodes.

        Args:
            nodes (list): Selected node or component names.

        Returns:
            list: shrinkWrap names.
        """
        return core.find_shrinkwrap_nodes(nodes)

    def item_extra(self, config):
        """Return the target mesh short name.

        Args:
            config (dict): Shrink wrap configuration.

        Returns:
            str: Target name.
        """
        return deformer_io.entry_label(config.get("target") or {})
