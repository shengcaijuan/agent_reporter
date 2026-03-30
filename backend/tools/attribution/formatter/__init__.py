"""
归因输出格式化模块

将各种归因模块的结构化输出转换为自然语言描述

支持模块:
- ContributionBasedAttrModule: 基于贡献度分析的归因
- ThresholdBasedAttrModule: 基于阈值分析的归因
- VariationBasedAttrModule: 基于变化率分析的归因

使用示例:
    from Tools.AttrOutputFormatter import format_attr_output

    # 自动识别类型并格式化
    result = format_attr_output(contribution_attr_output)
    result = format_attr_output(threshold_attr_output)

扩展新格式化器:
    from Tools.AttrOutputFormatter import BaseAttrOutputFormatter, FormatterRegistry

    class MyFormatter(BaseAttrOutputFormatter):
        @property
        def supported_output_type(self):
            return MyCustomOutput

        def format(self, attr_output) -> str:
            # 实现格式化逻辑
            return "格式化结果"

    # 注册新格式化器
    FormatterRegistry.register(MyFormatter())
"""

# 版本信息
__version__ = "1.0.0"
__author__ = "SimpleIntellReport Team"

# 导入基础类和接口
from .base import BaseAttrOutputFormatter
from .registry import FormatterRegistry

# 延迟导入标志
_formatters_initialized = False


def _ensure_formatters_registered():
    """确保内置格式化器已注册（延迟注册以避免循环导入）"""
    global _formatters_initialized
    if not _formatters_initialized:
        from .contribution import (
            DimensionAttrFormatter,
            ParentIndicatorAttrFormatter
        )
        from .threshold import ThresholdAttrFormatter
        from .variation import VariationAttrFormatter

        _registry = FormatterRegistry()
        _registry.register(DimensionAttrFormatter())
        _registry.register(ParentIndicatorAttrFormatter())
        _registry.register(ThresholdAttrFormatter())
        _registry.register(VariationAttrFormatter())
        _formatters_initialized = True


def format_attr_output(attr_output) -> str:
    """
    统一的归因输出格式化入口函数

    根据输入类型自动选择合适的格式化器进行格式化

    Args:
        attr_output: 归因分析输出（支持多种类型）
            - DimensionAttributionOutput
            - ParentIndicatorAttributionOutput
            - ThresholdBasedAttrOutput
            - VariationBasedAttrOutput
            - 或其他已注册的归因输出类型

    Returns:
        str: 自然语言描述字符串

    Raises:
        ValueError: 当输入类型不支持时

    Examples:
        >>> from AttrOutputFormatter import format_attr_output
        >>> from ContributionBasedAttrModule.AttributionAnalyzer import DimensionAttributionOutput
        >>>
        >>> result = format_attr_output(dimension_attr_output)
        >>> print(result)
        父指标【收入】的【产品维度】维度下：
        正向指标：
        ...

    Note:
        此函数会自动识别输入类型并路由到对应的格式化器
        如需手动控制格式化行为，可直接使用具体的格式化器类
    """
    if attr_output is None:
        return "未获取到有效的归因分析结果。"

    # 确保格式化器已注册
    _ensure_formatters_registered()

    formatter = FormatterRegistry.get_formatter(attr_output)

    if formatter is None:
        supported_types = FormatterRegistry.list_supported_type_names()
        raise ValueError(
            f"不支持的归因输出类型: {type(attr_output).__name__}. "
            f"支持的类型: {', '.join(supported_types)}"
        )

    return formatter.format(attr_output)


# 导出公共接口
__all__ = [
    # 版本信息
    '__version__',
    '__author__',

    # 统一入口
    'format_attr_output',

    # 基础类
    'BaseAttrOutputFormatter',
    'FormatterRegistry',

    # 内置格式化器（延迟导入）
    'DimensionAttrFormatter',
    'ParentIndicatorAttrFormatter',
    'ThresholdAttrFormatter',
    'VariationAttrFormatter',
]

# 为了支持直接导入格式化器类，使用 __getattr__
def __getattr__(name: str):
    """延迟导入格式化器类"""
    if name in ('DimensionAttrFormatter', 'ParentIndicatorAttrFormatter'):
        from .contribution import (
            DimensionAttrFormatter,
            ParentIndicatorAttrFormatter
        )
        _ensure_formatters_registered()
        if name == 'DimensionAttrFormatter':
            return DimensionAttrFormatter
        elif name == 'ParentIndicatorAttrFormatter':
            return ParentIndicatorAttrFormatter
    elif name == 'ThresholdAttrFormatter':
        from .threshold import ThresholdAttrFormatter
        _ensure_formatters_registered()
        return ThresholdAttrFormatter
    elif name == 'VariationAttrFormatter':
        from .variation import VariationAttrFormatter
        _ensure_formatters_registered()
        return VariationAttrFormatter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
