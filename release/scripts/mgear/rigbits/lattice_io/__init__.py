"""Lattice IO - Export and import ffd lattice setups.

Serialize ffd lattice deformers (settings, lattice shape and placement,
affected geometry, weights and deformer order) to ``.lat`` files and
rebuild them, for example from a Shifter custom step when a rig is
regenerated.

Example:
    >>> from mgear.rigbits import lattice_io
    >>> lattice_io.show()
    >>> lattice_io.export_lattices(["ffd1"], "C:/tmp/face.lat")
    >>> lattice_io.import_lattices("C:/tmp/face.lat", order="last")
"""

__version__ = "1.0.0"

from mgear.core import pyqt

from mgear.core.deformer_io import ORDER_CURRENT
from mgear.core.deformer_io import ORDER_FRONT
from mgear.core.deformer_io import ORDER_LAST
from mgear.core.deformer_io import ORDER_MODES

from .core import FILE_TYPE
from .core import LATTICE_FILE_EXT
from .core import SCHEMA_VERSION
from .core import build_lattice
from .core import export_lattices
from .core import get_lattice_config
from .core import import_lattices
from .core import load_file


def show(*args):
    """Show the Lattice IO UI.

    Returns:
        LatticeIOUI: The UI instance.
    """
    from .ui import LatticeIOUI

    return pyqt.showDialog(LatticeIOUI, dockable=True)
