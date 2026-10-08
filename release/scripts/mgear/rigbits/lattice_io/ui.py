"""Lattice IO - Main UI Module.

Dockable window to export and import ffd lattice configurations, built on
the shared :class:`mgear.rigbits.deformer_io_ui.DeformerIOUI`.
"""

from mgear.core import deformer
from mgear.core import node_remap

from mgear.rigbits.deformer_io_ui import DeformerIOUI

from . import core


class LatticeIOUI(DeformerIOUI):
    """Dockable dialog to export and import lattice configurations."""

    TOOL_NAME = "LatticeIO"
    toolName = TOOL_NAME
    TOOL_TITLE = "Lattice IO"
    FORMAT = core.FORMAT
    FILE_LABEL = "mGear Lattice Config"
    EXTRA_FILTERS = ("Legacy JSON (*.json)",)
    SETTINGS_PREFIX = "lattice_io"
    NAME_COLUMN = "Lattice"
    EXTRA_COLUMN = "Divisions"

    def scene_nodes(self):
        """Return the ffd deformers in the scene.

        Returns:
            list: ffd names.
        """
        return deformer.get_ffd_nodes()

    def scene_label(self, node):
        """Return the Export list label: ffd, lattice and geometry count.

        Args:
            node (str): ffd name.

        Returns:
            str: Label.
        """
        lat_tfm = deformer.get_lattice_nodes(node)[0]
        return "{}   ({}, {} geo)".format(
            node,
            node_remap.leaf_name(lat_tfm) if lat_tfm else "no lattice",
            len(deformer.get_deformer_geometry(node)),
        )

    def find_from_selection(self, nodes):
        """Return the ffds related to the selected nodes.

        Args:
            nodes (list): Selected node or component names.

        Returns:
            list: ffd names.
        """
        return deformer.find_ffd_nodes(nodes)

    def select_nodes(self, node):
        """Return the lattice transform of an ffd.

        Args:
            node (str): ffd name.

        Returns:
            list: Node names.
        """
        lat_tfm = deformer.get_lattice_nodes(node)[0]
        return [lat_tfm] if lat_tfm else []

    def item_extra(self, config):
        """Return the lattice divisions, e.g. ``2x5x2``.

        Args:
            config (dict): Lattice configuration.

        Returns:
            str: Divisions.
        """
        return "x".join(str(d) for d in config["lattice"]["divisions"])
