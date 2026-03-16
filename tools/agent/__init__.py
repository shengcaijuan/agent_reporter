"""统一的工具函数代理模块

提供统一的接口来创建不同类型的归因分析工具代理：
- Contribution: 贡献度归因（加法/乘法关系）
- Variation: 变动归因
- Threshold: 阈值归因

使用示例:
    from Tools.ToolFunctionAgent import ToolFunctionAgent, AttributionType, get_tool_agents

    # 创建单个工具代理
    agent = ToolFunctionAgent(
        attr_type=AttributionType.THRESHOLD,
        class_name_root="Chapter1",
        indicators_config=[...],
        tools_config={...}
    )

    # 批量创建工具代理
    agents = create_tool_agents(tool_agent_config)
"""

from .attribution_type import AttributionType
from .tool_agent import ToolFunctionAgent
from .tool_agent_register import create_tool_agents

__all__ = [
    "AttributionType",
    "ToolFunctionAgent",
    "create_tool_agents"
]