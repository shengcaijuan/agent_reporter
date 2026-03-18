"""
ContributionBasedAttrModule 输出格式化器

将基于贡献度分析的归因输出（DimensionAttributionOutput 和 ParentIndicatorAttributionOutput）
转换为自然语言描述

为了避免循环导入，使用字符串类型标注和延迟导入
"""
from typing import Any
from .base import BaseAttrOutputFormatter

class DimensionAttrFormatter(BaseAttrOutputFormatter):
    """
    DimensionAttributionOutput 格式化器

    将 ContributionBasedAttrModule 的维度归因输出转换为自然语言

    支持的归因类型：
    - 加法关系归因（additive）
    - 乘法关系归因（multiplicative）
    """

    @property
    def supported_output_type(self):
        # 延迟导入以避免循环依赖
        from tools.attribution.contribution.analyzer import DimensionAttributionOutput
        return DimensionAttributionOutput

    def format(self, attr_output: Any) -> str:
        """
        格式化维度归因输出

        Args:
            attr_output: 维度归因分析输出

        Returns:
            str: 自然语言描述
        """
        self._validate_input(attr_output)

        # 获取父指标信息
        parent_indicator = attr_output.parent_indicator
        parent_name = parent_indicator.indicator_name
        dim_name = attr_output.dim_name or "未知维度"

        # 构建输出文本
        result_lines = [f"父指标【{parent_name}】的【{dim_name}】维度下："]

        # 格式化正向指标
        positive_indicators = attr_output.positive_sub_indicators
        if positive_indicators:
            result_lines.append("正向指标：")
            for indicator in positive_indicators:
                formatted = self._format_sub_indicator(indicator)
                result_lines.append(formatted)

        # 格式化负向指标
        negative_indicators = attr_output.negative_sub_indicators
        if negative_indicators:
            result_lines.append("负向指标：")
            for indicator in negative_indicators:
                formatted = self._format_sub_indicator(indicator)
                result_lines.append(formatted)

        # 如果没有子指标
        if not positive_indicators and not negative_indicators:
            result_lines.append("暂无子指标数据。")

        return "\n".join(result_lines)

    def _format_sub_indicator(self, sub_indicator: Any) -> str:
        """
        格式化单个子指标的输出

        Args:
            sub_indicator: 子指标归因输出

        Returns:
            str: 格式化后的子指标描述
        """
        parts = [sub_indicator.indicator_name]

        # 同比相对变化（变化率）
        if sub_indicator.change_rate is not None:
            parts.append(f"同比相对变化{sub_indicator.change_rate:.2f}%")

        # 同比绝对变化（变化值）
        if sub_indicator.change_value is not None:
            parts.append(f"同比绝对变化{sub_indicator.change_value}")

        # 对父指标变化贡献值
        if sub_indicator.change_contribution_value is not None:
            parts.append(f"对父指标变化贡献{sub_indicator.change_contribution_value}")

        # 对父指标变化贡献占比
        if sub_indicator.change_contribution_ratio is not None:
            parts.append(f"占比{sub_indicator.change_contribution_ratio:.2f}%")

        # 对父指标值贡献占比
        if sub_indicator.contribution_ratio is not None:
            parts.append(f"对父指标值贡献占比{sub_indicator.contribution_ratio:.2f}%")

        return "，".join(parts) + "；"


class ParentIndicatorAttrFormatter(BaseAttrOutputFormatter):
    """
    ParentIndicatorAttributionOutput 格式化器

    将 ContributionBasedAttrModule 的父指标归因输出转换为自然语言

    用于处理包含多个维度的父指标归因分析结果
    """

    @property
    def supported_output_type(self):
        # 延迟导入以避免循环依赖
        from tools.attribution.contribution.analyzer import ParentIndicatorAttributionOutput
        return ParentIndicatorAttributionOutput

    def format(self, attr_output: Any) -> str:
        """
        格式化父指标归因输出

        Args:
            attr_output: 父指标归因分析输出

        Returns:
            str: 自然语言描述
        """
        self._validate_input(attr_output)

        result_lines = [
            f"父指标【{attr_output.parent_indicator_name}】的归因分析："
        ]

        # 使用 DimensionAttrFormatter 格式化每个维度
        dimension_formatter = DimensionAttrFormatter()

        for dim_output in attr_output.dimension_attribution_outputs:
            dim_text = dimension_formatter.format(dim_output)
            result_lines.append(dim_text)

        return "\n\n".join(result_lines)
