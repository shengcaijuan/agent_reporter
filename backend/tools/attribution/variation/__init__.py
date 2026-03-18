"""
 基于变化的归因分析模块

该模块用于分析单个指标当期与上期的变化情况，计算绝对变化值和相对变化率。
适用于同比、环比、目标差异等场景。
"""

from .analyzer import (
    VariationBasedIndicatorSpec,
    VariationBasedIndicatorsBlock,
    VariationBasedIndicatorAttrOutput,
    VariationBasedAttrOutput,
    VariationBasedAttrAnalyzer
)

from .arg_model import VariationArgModel
from .attr_block import VariationBasedAttribution

__all__ = [
    "VariationBasedIndicatorSpec",
    "VariationBasedIndicatorsBlock",
    "VariationBasedIndicatorAttrOutput",
    "VariationBasedAttrOutput",
    "VariationBasedAttrAnalyzer",
    "VariationArgModel",
    "VariationBasedAttribution"
]
