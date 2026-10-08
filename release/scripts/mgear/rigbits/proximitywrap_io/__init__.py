"""Proximity Wrap IO - Export and import proximityWrap deformer setups.

Serialize Maya proximityWrap deformers (settings and falloff ramps,
drivers with their own settings, incoming connections, affected geometry,
weights and deformer order) to ``.pxw`` files and rebuild them, for
example from a Shifter custom step when a rig is regenerated.

Example:
    >>> from mgear.rigbits import proximitywrap_io
    >>> proximitywrap_io.show()
    >>> proximitywrap_io.export_proximitywraps(["pw1"], "C:/tmp/cloth.pxw")
    >>> proximitywrap_io.import_proximitywraps("C:/tmp/cloth.pxw")
"""

__version__ = "1.0.0"

from mgear.core import pyqt

from mgear.core.deformer_io import ORDER_CURRENT
from mgear.core.deformer_io import ORDER_FRONT
from mgear.core.deformer_io import ORDER_LAST
from mgear.core.deformer_io import ORDER_MODES

from .core import FILE_TYPE
from .core import PROXIMITYWRAP_FILE_EXT
from .core import SCHEMA_VERSION
from .core import build_proximitywrap
from .core import export_proximitywraps
from .core import find_proximitywrap_nodes
from .core import get_drivers
from .core import get_proximitywrap_config
from .core import import_proximitywraps
from .core import load_file


def show(*args):
    """Show the Proximity Wrap IO UI.

    Returns:
        ProximityWrapIOUI: The UI instance.
    """
    from .ui import ProximityWrapIOUI

    return pyqt.showDialog(ProximityWrapIOUI, dockable=True)
