"""Optional C++ acceleration for mGear RGP -- falls back to pure Python."""

try:
    from mgear.shifter._rgp_accel_cpp import (  # type: ignore[import]
        record_primary,
        record_mirror,
        reposition_all_guides,
    )
    HAS_ACCEL = True
except ImportError:
    HAS_ACCEL = False
    record_primary = None
    record_mirror = None
    reposition_all_guides = None
