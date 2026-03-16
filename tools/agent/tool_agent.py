"""统一的工具函数代理创建器"""
from typing import Union, Dict, Any, List, Optional
from pathlib import Path
from langchain_core.tools import StructuredTool
from .tool_executor import ToolFunctionLLM

# 导入归因类型枚举
from .attribution_type import AttributionType

# 导入各种归因模块
from ..attribution.contribution import (
    AddDimArgModel, MulDimArgModel,
    AddDimAttribution, MulDimAttribution,
    AttributionRelationType
)
from ..attribution.variation import (
    VariationArgModel, VariationBasedAttribution
)
from ..attribution.threshold import (
    ThresholdArgModel, ThresholdBasedAttribution
)

class ToolFunctionAgent:
    """统一的工具函数代理

    支持三种归因类型：
    - Contribution: 贡献度归因（加法/乘法关系）
    - Variation: 变动归因
    - Threshold: 阈值归因
    """

    def __init__(
        self,
        attr_type: Union[AttributionType, str],
        indicators_config: Union[Dict[str, Any], List[Dict[str, Any]], List[str]],
        tools_config: Dict[str, Any],
        class_name_root: Union[str, None] = None,
        sale_id: Optional[str] = None,
        sale_name: Optional[str] = None,
        progress_report_dir: Optional[Path] = None,
        **kwargs
    ):
        """
        初始化工具函数代理

        Args:
            attr_type: 归因类型 (AttributionType.CONTRIBUTION | AttributionType.VARIATION | AttributionType.THRESHOLD)
            indicators_config: 指标配置（格式根据 attr_type 不同而不同）
                - Contribution: Dict[str, Any] - {
                    "parent_indicator": "收入",
                    "dimension": "产品价值维度",
                    "child_indicators": ["高值品收入", "非高值品收入"],
                    "relation_type": "additive"  # 可选，默认为 "additive"
                  }
                - Threshold: List[Dict[str, Any]] - [
                    {"indicator": "销售额", "baseline": "销售目标", "threshold_type": ...},
                    ...
                  ]
                - Variation: List[str] - ["指标1", "指标2", ...]
            tools_config: 工具配置 - {
                "tool_name": "tool_name",
                "tool_description": "tool description"
            }
            class_name_root: 类名根（可选，Contribution 类型不需要）
            sale_id: 销售工号（可选，用于创建专属日志）
            sale_name: 销售姓名（可选，用于日志记录）
            progress_report_dir: 报告目录（可选，用于存放专属日志）
            **kwargs: 其他扩展参数
        """
        # 转换为枚举类型（如果传入的是字符串）
        if isinstance(attr_type, str):
            attr_type = AttributionType(attr_type)

        self.attr_type = attr_type
        self.indicators_config = indicators_config
        self.tools_config = tools_config
        self.class_name_root = class_name_root

        # 销售标识信息（用于创建专属日志）
        self.sale_id = sale_id
        self.sale_name = sale_name
        self.progress_report_dir = progress_report_dir

        # 根据 attr_type 创建对应的模型和工具
        self.args_model_creator = self._create_args_model()
        self.args_model4llm = self.args_model_creator.create_args_model4llm()
        self.args_model = self.args_model_creator.create_args_model()
        self.tool_creator = self._create_tool()

    def _create_args_model(self) -> Union[
        AddDimArgModel, MulDimArgModel,
        VariationArgModel, ThresholdArgModel
    ]:
        """根据 attr_type 创建参数模型"""
        if self.attr_type == AttributionType.CONTRIBUTION:
            # Contribution 类型需要处理加法/乘法关系
            relation_type = self.indicators_config.get(
                "relation_type",
                AttributionRelationType.ADDITIVE
            )
            if relation_type == AttributionRelationType.ADDITIVE:
                return AddDimArgModel(
                    parent_indicator_name=self.indicators_config["parent_indicator"],
                    dimension_name=self.indicators_config["dimension"],
                    child_indicator_names=self.indicators_config["child_indicators"]
                )
            elif relation_type == AttributionRelationType.MULTIPLICATIVE:
                return MulDimArgModel(
                    parent_indicator_name=self.indicators_config["parent_indicator"],
                    dimension_name=self.indicators_config["dimension"],
                    child_indicator_name_1=self.indicators_config["child_indicators"][0],
                    child_indicator_name_2=self.indicators_config["child_indicators"][1]
                )
            else:
                raise ValueError(f"Unknown relation_type: {relation_type}")

        elif self.attr_type == AttributionType.VARIATION:
            if self.class_name_root is None:
                raise ValueError("Variation 类型需要提供 class_name_root 参数")
            return VariationArgModel(
                model_name_root=self.class_name_root,
                indicators_config=self.indicators_config
            )

        elif self.attr_type == AttributionType.THRESHOLD:
            if self.class_name_root is None:
                raise ValueError("Threshold 类型需要提供 class_name_root 参数")
            return ThresholdArgModel(
                model_name_root=self.class_name_root,
                indicators_config=self.indicators_config
            )

        else:
            raise ValueError(f"Unknown attr_type: {self.attr_type}")

    def _create_tool(self) -> Union[
        AddDimAttribution, MulDimAttribution,
        VariationBasedAttribution, ThresholdBasedAttribution
    ]:
        """根据 attr_type 创建归因工具"""
        if self.attr_type == AttributionType.CONTRIBUTION:
            relation_type = self.indicators_config.get(
                "relation_type",
                AttributionRelationType.ADDITIVE
            )
            if relation_type == AttributionRelationType.ADDITIVE:
                return AddDimAttribution(
                    arg_model4llm=self.args_model4llm,
                    arg_model=self.args_model,
                    args_model_creator=self.args_model_creator
                )
            elif relation_type == AttributionRelationType.MULTIPLICATIVE:
                return MulDimAttribution(
                    arg_model4llm=self.args_model4llm,
                    arg_model=self.args_model,
                    args_model_creator=self.args_model_creator
                )
            else:
                raise ValueError(f"Unknown relation_type: {relation_type}")

        elif self.attr_type == AttributionType.VARIATION:
            return VariationBasedAttribution(
                arg_model4llm=self.args_model4llm,
                arg_model=self.args_model,
                args_model_creator=self.args_model_creator
            )

        elif self.attr_type == AttributionType.THRESHOLD:
            return ThresholdBasedAttribution(
                arg_model4llm=self.args_model4llm,
                arg_model=self.args_model,
                args_model_creator=self.args_model_creator
            )

        else:
            raise ValueError(f"Unknown attr_type: {self.attr_type}")

    def langchain_tool_function(self) -> StructuredTool:
        """创建 LangChain 工具函数"""
        return self.tool_creator.create_langchain_tool(
            tool_name=self.tools_config["tool_name"],
            description=self.tools_config["tool_description"]
        )

    def tool_function_agent(self, data: str) -> ToolFunctionLLM:
        """创建工具函数代理"""
        tool_function = self.langchain_tool_function()
        return ToolFunctionLLM(
            data=data,
            tools=[tool_function],
            sale_id=self.sale_id,
            sale_name=self.sale_name,
            progress_report_dir=self.progress_report_dir
        )

    def run(self, data: str) -> tuple[str, Any]:
        """同步执行分析"""
        agent = self.tool_function_agent(data)
        return agent.analysis()

    async def run_async(self, data: str) -> tuple[str, Any]:
        """异步执行分析"""
        agent = self.tool_function_agent(data)
        return await agent.async_analysis()
