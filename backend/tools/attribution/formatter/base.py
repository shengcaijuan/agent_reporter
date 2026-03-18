"""
归因输出格式化器抽象基类

定义了所有归因输出格式化器必须遵循的接口
"""
from abc import ABC, abstractmethod
from typing import Type
from pydantic import BaseModel


class BaseAttrOutputFormatter(ABC):
    """
    归因输出格式化器抽象基类

    所有具体的格式化器必须继承此类并实现 format() 方法

    设计模式：策略模式（Strategy Pattern）
    - 将格式化算法封装成独立的类
    - 使得算法可以独立于使用它的客户端变化
    """

    @property
    @abstractmethod
    def supported_output_type(self) -> Type[BaseModel]:
        """
        返回支持的输出模型类型

        用于格式化器注册时的类型匹配

        Returns:
            Type[BaseModel]: 支持的 Pydantic 模型类型
        """
        pass

    @abstractmethod
    def format(self, attr_output: BaseModel) -> str:
        """
        将归因输出转换为自然语言描述

        Args:
            attr_output: 归因分析输出（各种归因模块的输出模型）

        Returns:
            str: 自然语言描述字符串

        Raises:
            ValueError: 当输入为 None 或格式不符合预期时
        """
        pass

    def can_format(self, attr_output: BaseModel) -> bool:
        """
        判断是否可以格式化指定的输出

        Args:
            attr_output: 归因分析输出

        Returns:
            bool: 是否支持该类型的输出
        """
        if attr_output is None:
            return False
        return isinstance(attr_output, self.supported_output_type)

    def _validate_input(self, attr_output: BaseModel) -> None:
        """
        验证输入的有效性

        Args:
            attr_output: 归因分析输出

        Raises:
            ValueError: 当输入为 None 时
        """
        if attr_output is None:
            raise ValueError("归因输出不能为 None")
