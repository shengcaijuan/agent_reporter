"""
格式化器注册器

管理所有归因输出格式化器的注册、查找和调用

设计模式：注册器模式（Registry Pattern）
- 集中管理格式化器实例
- 支持运行时动态注册新的格式化器
- 提供类型查找和列表功能
"""
from typing import Dict, List, Type, Optional
from pydantic import BaseModel
from .base import BaseAttrOutputFormatter


class FormatterRegistry:
    """
    格式化器注册器（单例模式）

    管理所有归因输出格式化器的注册和查找

    使用示例:
        # 获取单例实例
        registry = FormatterRegistry()

        # 注册格式化器
        registry.register(MyFormatter())

        # 获取格式化器
        formatter = registry.get_formatter(attr_output)

        # 列出支持的类型
        types = registry.list_supported_types()
    """

    _instance: Optional['FormatterRegistry'] = None
    _formatters: Dict[Type[BaseModel], BaseAttrOutputFormatter] = {}

    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(
        cls,
        formatter: BaseAttrOutputFormatter
    ) -> BaseAttrOutputFormatter:
        """
        注册格式化器

        Args:
            formatter: 格式化器实例

        Returns:
            BaseAttrOutputFormatter: 注册的格式化器（支持链式调用）

        Raises:
            TypeError: 当 formatter 不是 BaseAttrOutputFormatter 的实例时

        Note:
            如果已存在相同类型的格式化器，将被覆盖
        """
        if not isinstance(formatter, BaseAttrOutputFormatter):
            raise TypeError(
                f"格式化器必须继承自 BaseAttrOutputFormatter，"
                f"但得到 {type(formatter).__name__}"
            )

        output_type = formatter.supported_output_type
        cls._formatters[output_type] = formatter
        return formatter

    @classmethod
    def get_formatter(
        cls,
        attr_output: BaseModel
    ) -> Optional[BaseAttrOutputFormatter]:
        """
        根据输出类型获取格式化器

        Args:
            attr_output: 归因分析输出

        Returns:
            Optional[BaseAttrOutputFormatter]: 格式化器实例，找不到返回 None
        """
        if attr_output is None:
            return None
        output_type = type(attr_output)
        return cls._formatters.get(output_type)

    @classmethod
    def list_supported_types(cls) -> List[Type[BaseModel]]:
        """
        列出所有支持的输出类型

        Returns:
            List[Type[BaseModel]]: 支持的输出类型列表
        """
        return list(cls._formatters.keys())

    @classmethod
    def list_supported_type_names(cls) -> List[str]:
        """
        列出所有支持的输出类型名称

        Returns:
            List[str]: 支持的输出类型名称列表
        """
        return [t.__name__ for t in cls._formatters.keys()]

    @classmethod
    def clear(cls) -> None:
        """
        清空所有注册的格式化器

        Note:
            主要用于测试，生产环境慎用
        """
        cls._formatters.clear()

    @classmethod
    def is_supported(cls, attr_output: BaseModel) -> bool:
        """
        判断指定的输出类型是否支持

        Args:
            attr_output: 归因分析输出

        Returns:
            bool: 是否支持该类型
        """
        return cls.get_formatter(attr_output) is not None
