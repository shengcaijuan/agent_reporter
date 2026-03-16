from pydantic import BaseModel
from langchain_core.tools import StructuredTool
from typing import Type
from ..analyzer import (
    DimensionAttributionBlock,
    AttributionRelationType,
    AttributionAnalyzer,
    DimensionAttributionOutput
)
from .add_arg_model import AddDimArgModel

class AddDimAttribution:
    def __init__(
            self,
            arg_model4llm: Type[BaseModel],  # LLM输入参数模型
            arg_model: Type[BaseModel],  # 内部输入参数模型
            args_model_creator: AddDimArgModel,
            relation_type: AttributionRelationType = AttributionRelationType.ADDITIVE,  # 维度关系类型
    ):
        """
        初始化函数
        Args:
            arg_model4llm: LLM输入参数模型
            arg_model: 内部输入参数模型
            relation_type: 维度关系类型
            args_model_creator: AddDimArgModel实例
        Returns:
            None
        """
        self.arg_model4llm = arg_model4llm
        self.arg_model = arg_model
        self.relation_type = relation_type
        self.args_model_creator = args_model_creator
        self.analyzer = AttributionAnalyzer()

    def attribution_function(
            self,
            dimension_attribution_block: DimensionAttributionBlock
    ) -> DimensionAttributionOutput:
        """
        归因分析函数
        Args:
            dimension_attribution_block: 维度归因块
        Returns:
            Tuple[ParentIndicatorAttributionOutput, List[str]]: 父指标归因分析结果
        """
        if not isinstance(dimension_attribution_block, DimensionAttributionBlock):
            raise TypeError(f"Expected {DimensionAttributionBlock.__name__}, got {type(dimension_attribution_block)}")
        return self.analyzer.dimension_attribution_analysis(dimension_attribution_block)

    def wrapped_attribution_function(
            self,
            **kwargs
    ) -> DimensionAttributionOutput:
        """
        包装函数
        Args:
            kwargs: 关键字参数
        Returns:
            Tuple[ParentIndicatorAttributionOutput, List[str]]: 父指标归因分析结果
        """
        llm_input = self.arg_model4llm(**kwargs)
        attribution_input = self.arg_model.from_llm(llm_input)
        dimension_attribution_block = self.args_model_creator.create_dimension_attribution_block(
            input_data=attribution_input,
            relation_type=self.relation_type
        )

        return self.attribution_function(dimension_attribution_block)

    def create_langchain_tool(
            self,
            tool_name: str,
            description: str
    ) -> StructuredTool:
        """
        创建LangChain工具
        Args:
            tool_name: 工具名称
            description: 工具描述
        Returns:
            StructuredTool: LangChain结构化工具
        """
        return StructuredTool.from_function(
            name=tool_name,
            description=description,
            func=self.wrapped_attribution_function,
            args_schema=self.arg_model4llm
        )