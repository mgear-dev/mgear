"""Backward-compatibility module.

All blendshape utilities have moved to ``mgear.core.blendshape``.
This module re-exports them so existing code continues to work.
"""

from mgear.core.blendshape import getDeformerNode  # noqa: F401
from mgear.core.blendshape import getBlendShape  # noqa: F401
from mgear.core.blendshape import getMorph  # noqa: F401
from mgear.core.blendshape import blendshape_foc  # noqa: F401
from mgear.core.blendshape import connectWithBlendshape  # noqa: F401
from mgear.core.blendshape import connectWithMorph  # noqa: F401
from mgear.core.blendshape import morph_foc  # noqa: F401
