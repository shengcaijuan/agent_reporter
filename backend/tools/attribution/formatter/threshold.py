# threshold_formatter.py
"""
ThresholdBasedAttrModule 输出格式化器

将基于阈值分析的归因输出（ThresholdBasedAttrOutput）转换为自然语言描述

为了避免循环导入，使用延迟导入
"""
from typing import Any
from .base import BaseAttrOutputFormatter


class ThresholdAttrFormatter(BaseAttrOutputFormatter):
    """
    ThresholdBasedAttrOutput 格式化器

    将 ThresholdBasedAttrModule 的阈值归因输出转换为自然语言

    支持的评估类型：
    - 目标达成率评估（TARGET_ACHIEVEMENT）
    - 绩效总分评估（TOTAL_PERFORMANCE_SCORE）
    """

    @property
    def supported_output_type(self):
        # 延迟导入以避免循环依赖
        from tools.attribution.threshold.analyzer import ThresholdBasedAttrOutput
        return ThresholdBasedAttrOutput

    def format(self, attr_output: Any) -> str:
        """
        格式化阈值归因输出

        Args:
            attr_output: 阈值归因分析输出

        Returns:
            str: 自然语言描述
        """
        self._validate_input(attr_output)

        result_lines = ["基于阈值的指标评估结果："]

        # 格式化负向/风险指标
        negative_indicators = attr_output.negative_indicators
        if negative_indicators:
            result_lines.append("【负向/风险指标】")
            for indicator in negative_indicators:
                formatted = self._format_indicator(indicator)
                result_lines.append(formatted)
            result_lines.append("")  # 空行分隔

        # 格式化正向/正常指标
        positive_indicators = attr_output.positive_indicators
        if positive_indicators:
            result_lines.append("【正向/正常指标】")
            for indicator in positive_indicators:
                formatted = self._format_indicator(indicator)
                result_lines.append(formatted)

        # 如果没有任何分类的指标
        if not negative_indicators and not positive_indicators:
            result_lines.append("暂无指标数据。")

        return "\n".join(result_lines)

    def _format_indicator(self, indicator: Any) -> str:
        """
        格式化单个指标的输出

        Args:
            indicator: 单个指标的归因输出

        Returns:
            str: 格式化后的指标描述
        """
        parts = [f"- {indicator.indicator_name}"]

        # 判断是否有目标值（分母）
        if indicator.baseline_name and indicator.baseline_value is not None:
            # 有目标值的指标（达成率类型）
            achievement_rate = (
                indicator.indicator_value / indicator.baseline_value * 100
                if indicator.baseline_value != 0 else 0
            )
            parts.append(
                f"实际值 {indicator.indicator_value}，"
                f"目标值 {indicator.baseline_value}，"
                f"达成率 {achievement_rate:.2f}%"
            )
        else:
            # 无目标值的指标（绩效总分类型）
            parts.append(f"指标值 {indicator.indicator_value}")

        # 添加状态标签
        parts.append(f"状态：{indicator.status_label}")

        return "，".join(parts)
