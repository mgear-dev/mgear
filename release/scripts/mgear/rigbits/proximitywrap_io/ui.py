"""Proximity Wrap IO - Main UI Module.

Dockable window to export and import proximityWrap configurations, built
on the shared :class:`mgear.rigbits.deformer_io_ui.DeformerIOUI`.
"""

from mgear.core import deformer
from mgear.core import deformer_io

from mgear.rigbits.deformer_io_ui import DeformerIOUI

from . import core


class ProximityWrapIOUI(DeformerIOUI):
    """Dockable dialog to export and import proximity wrap configurations."""

    TOOL_NAME = "ProximityWrapIO"
    toolName = TOOL_NAME
    TOOL_TITLE = "Proximity Wrap IO"
    FORMAT = core.FORMAT
    FILE_LABEL = "mGear Proximity Wrap Config"
    SETTINGS_PREFIX = "proximitywrap_io"
    NAME_COLUMN = "Proximity Wrap"
    EXTRA_COLUMN = "Drivers"

    def scene_nodes(self):
        """Return the proximityWrap deformers in the scene.

        Returns:
            list: proximityWrap names.
        """
        return core.get_proximitywrap_nodes()

    def scene_label(self, node):
        """Return the Export list label: name, driver and geometry count.

        Args:
            node (str): proximityWrap name.

        Returns:
            str: Label.
        """
        return "{}   ({} drivers, {} geo)".format(
            node,
            len(core.get_drivers(node)),
            len(deformer.get_deformer_geometry(node)),
        )

    def find_from_selection(self, nodes):
        """Return the proximityWraps related to the selected nodes.

        Args:
            nodes (list): Selected node or component names.

        Returns:
            list: proximityWrap names.
        """
        return core.find_proximitywrap_nodes(nodes)

    def select_nodes(self, node):
        """Return the driver transforms of a proximityWrap.

        Args:
            node (str): proximityWrap name.

        Returns:
            list: Node names.
        """
        return [transform for _, transform, _ in core.get_drivers(node)]

    def item_extra(self, config):
        """Return the driver short names.

        Args:
            config (dict): Proximity wrap configuration.

        Returns:
            str: Comma separated driver names.
        """
        return ", ".join(
            deformer_io.entry_label(driver) for driver in config.get("drivers", [])
        )
