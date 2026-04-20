"""向后兼容模块。

所有混合形状工具已移至 ``mgear.core.blendshape``。
此模块重新导出它们以确保现有代码继续工作。
"""

from mgear.core.blendshape import getDeformerNode  # noqa: F401
from mgear.core.blendshape import getBlendShape  # noqa: F401
from mgear.core.blendshape import getMorph  # noqa: F401
from mgear.core.blendshape import blendshape_foc  # noqa: F401
from mgear.core.blendshape import connectWithBlendshape  # noqa: F401
from mgear.core.blendshape import connectWithMorph  # noqa: F401
from mgear.core.blendshape import morph_foc  # noqa: F401
