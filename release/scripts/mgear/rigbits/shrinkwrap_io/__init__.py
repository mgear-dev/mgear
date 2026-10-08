"""Shrink Wrap IO - Export and import shrinkWrap deformer setups.

Serialize Maya shrinkWrap deformers (settings, target and other incoming
connections, affected geometry, weights and deformer order) to ``.shw``
files and rebuild them, for example from a Shifter custom step when a rig
is regenerated.

Example:
    >>> from mgear.rigbits import shrinkwrap_io
    >>> shrinkwrap_io.show()
    >>> shrinkwrap_io.export_shrinkwraps(["shrinkWrap1"], "C:/tmp/cloth.shw")
    >>> shrinkwrap_io.import_shrinkwraps("C:/tmp/cloth.shw", order="last")
"""

__version__ = "1.0.0"

from mgear.core import pyqt

from mgear.core.deformer_io import ORDER_CURRENT
from mgear.core.deformer_io import ORDER_FRONT
from mgear.core.deformer_io import ORDER_LAST
from mgear.core.deformer_io import ORDER_MODES

from .core import FILE_TYPE
from .core import SCHEMA_VERSION
from .core import SHRINKWRAP_FILE_EXT
from .core import build_shrinkwrap
from .core import export_shrinkwraps
from .core import find_shrinkwrap_nodes
from .core import get_shrinkwrap_config
from .core import import_shrinkwraps
from .core import load_file


def show(*args):
    """Show the Shrink Wrap IO UI.

    Returns:
        ShrinkWrapIOUI: The UI instance.
    """
    from .ui import ShrinkWrapIOUI

    return pyqt.showDialog(ShrinkWrapIOUI, dockable=True)
