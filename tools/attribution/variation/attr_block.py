# VariationBasedAttrBlock.py
from pydantic import BaseModel
from langchain_core.tools import StructuredTool
from typing import Type
from tools.attribution.variation.arg_model import VariationArgModel
from tools.attribution.variation.analyzer import VariationBasedAttrAnalyzer, VariationBasedIndicatorsBlock, VariationBasedAttrOutput

class VariationBasedAttribution:
    def __init__(
            self,
            arg_model4llm: Type[BaseModel],
            arg_model: Type[BaseModel],
            args_model_creator: VariationArgModel
    ):
        """
        :param arg_model4llm: LLM输入参数模型
        :param arg_model: 内部输入参数模型
        :param args_model_creator: VariationArgModel实例
        """
        self.arg_model4llm = arg_model4llm
        self.arg_model = arg_model
        self.args_model_creator = args_model_creator
        self.analyzer = VariationBasedAttrAnalyzer()

    def attribution_function(
            self,
            indicators_block: VariationBasedIndicatorsBlock
    ) -> VariationBasedAttrOutput:
        """
        :param indicators_block: 指标列表
        :return: 指标归因分析结果
        """
        if not isinstance(indicators_block, VariationBasedIndicatorsBlock):
            raise TypeError(f"Expected {VariationBasedIndicatorsBlock.__name__}, got {type(indicators_block)}")
        return self.analyzer.evaluate_indicators(indicators_block)
    
    def wrapped_attribution_function(
            self,
            **kwargs
    ) -> VariationBasedAttrOutput:
        """
        :param kwargs: 关键字参数
        :return: 指标归因分析结果
        """
        llm_input = self.arg_model4llm(**kwargs)
        attribution_input = self.arg_model.from_llm(llm_input)
        indicators_block = self.args_model_creator.create_indicators_input_block(attribution_input)
        return self.attribution_function(indicators_block)
    
    def create_langchain_tool(
            self,
            tool_name: str,
            description: str
    ) -> StructuredTool:
        """
        :param tool_name: 工具名称
        :param description: 工具描述
        :return: LangChain结构化工具
        """
        return StructuredTool.from_function(
            name=tool_name,
            description=description,
            func=self.wrapped_attribution_function,
            args_schema=self.arg_model4llm
        )