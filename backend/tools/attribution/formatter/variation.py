"""
VariationBasedAttrModule 输出格式化器

将基于变化率的归因输出（VariationBasedAttrOutput）转换为自然语言描述

为了避免循环导入，使用字符串类型标注和延迟导入
"""
from typing import Any
from .base import BaseAttrOutputFormatter


class VariationAttrFormatter(BaseAttrOutputFormatter):
    """
    VariationBasedAttrOutput 格式化器

    将 VariationBasedAttrModule 的变化率归因输出转换为自然语言

    支持的归因类型：
    - 简单的期间变化分析（当前值 vs 上期值）
    - 自动分类正向和负向指标（基于 change_value）
    """

    @property
    def supported_output_type(self):
        # 延迟导入以避免循环依赖
        from tools.attribution.variation.analyzer import VariationBasedAttrOutput
        return VariationBasedAttrOutput

    def format(self, attr_output: Any) -> str:
        """
        格式化变化率归因输出

        Args:
            attr_output: 变化率归因分析输出

        Returns:
            str: 自然语言描述
        """
        self._validate_input(attr_output)

        # 构建输出文本
        result_lines = ["指标变化分析："]

        # 格式化正向指标（变化值 >= 0）
        positive_indicators = attr_output.positive_indicators
        if positive_indicators:
            result_lines.append("正向指标：")
            for indicator in positive_indicators:
                formatted = self._format_indicator(indicator)
                result_lines.append(formatted)

        # 格式化负向指标（变化值 < 0）
        negative_indicators = attr_output.negative_indicators
        if negative_indicators:
            result_lines.append("负向指标：")
            for indicator in negative_indicators:
                formatted = self._format_indicator(indicator)
                result_lines.append(formatted)

        # 如果没有指标
        if not positive_indicators and not negative_indicators:
            result_lines.append("暂无指标数据。")

        return "\n".join(result_lines)

    def _format_indicator(self, indicator: Any) -> str:
        """
        格式化单个指标的输出

        Args:
            indicator: 指标归因输出

        Returns:
            str: 格式化后的指标描述
        """
        parts = [indicator.indicator_name]

        # 上期值和当期值
        parts.append(f"上期值{indicator.prior_value}")
        parts.append(f"当期值{indicator.current_value}")

        # 绝对变化值
        change_value_str = f"绝对变化{indicator.change_value}"
        # 添加正负号
        if indicator.change_value > 0:
            change_value_str = f"绝对变化+{indicator.change_value}"
        parts.append(change_value_str)

        # 相对变化率
        change_rate_str = f"相对变化{indicator.change_rate:.2f}%"
        # 添加正负号
        if indicator.change_rate > 0:
            change_rate_str = f"相对变化+{indicator.change_rate:.2f}%"
        parts.append(change_rate_str)

        return "，".join(parts) + "；"
