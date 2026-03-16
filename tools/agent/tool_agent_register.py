# ToolAgentManager.py
"""统一的工具代理管理器"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from .tool_agent import ToolFunctionAgent

logger = logging.getLogger(__name__)


def create_tool_agents(
    tool_agent_config: List[Dict[str, Any]],
    sale_id: Optional[str] = None,
    sale_name: Optional[str] = None,
    progress_report_dir: Optional[Path] = None
) -> List[ToolFunctionAgent]:
    """
    获取工具代理列表（统一接口）

    Args:
        tool_agent_config: 工具代理配置列表
            每个配置应包含：
            - attr_type: 归因类型 ("contribution" | "variation" | "threshold")
            - indicators_config: 指标配置
            - tools_config: 工具配置
            - class_name_root: 类名根（可选，contribution 类型不需要）
        sale_id: 销售工号（可选，用于创建专属日志）
        sale_name: 销售姓名（可选，用于日志记录）
        progress_report_dir: 报告目录（可选，用于存放专属日志）

    Returns:
        工具代理列表

    Raises:
        ValueError: 当配置缺少必要字段时
        KeyError: 当 attr_type 无效时

    示例配置:
        [
            {
                "attr_type": "contribution",
                "indicators_config": {
                    "parent_indicator": "收入",
                    "dimension": "产品价值维度",
                    "child_indicators": ["高值品收入", "非高值品收入"],
                    "relation_type": "additive"
                },
                "tools_config": {
                    "tool_name": "income_value_dim_analysis_tool",
                    "tool_description": "收入价值维度归因分析工具"
                }
            },
            {
                "attr_type": "threshold",
                "class_name_root": "Chapter1",
                "indicators_config": [
                    {"indicator": "高值品收入", "baseline": "高值品收入目标"}
                ],
                "tools_config": {
                    "tool_name": "chapter1_achievement_tool",
                    "tool_description": "第一章达成率分析工具"
                }
            },
            {
                "attr_type": "variation",
                "class_name_root": "Chapter3",
                "indicators_config": ["指标1", "指标2"],
                "tools_config": {
                    "tool_name": "variation_tool",
                    "tool_description": "变动归因分析工具"
                }
            }
        ]
    """
    tool_agents = []
    for config in tool_agent_config:
        # 验证必要字段
        attr_type = config.get("attr_type")
        if not attr_type:
            raise ValueError("配置中必须包含 'attr_type' 字段")

        indicators_config = config.get("indicators_config")
        if indicators_config is None:
            raise ValueError("配置中必须包含 'indicators_config' 字段")

        tools_config = config.get("tools_config")
        if tools_config is None:
            raise ValueError("配置中必须包含 'tools_config' 字段")

        # class_name_root 是可选参数，默认为 None
        class_name_root = config.get("class_name_root", None)

        # 创建工具代理
        try:
            tool_agent = ToolFunctionAgent(
                attr_type=attr_type,
                indicators_config=indicators_config,
                tools_config=tools_config,
                class_name_root=class_name_root,
                sale_id=sale_id,
                sale_name=sale_name,
                progress_report_dir=progress_report_dir
            )
            tool_agents.append(tool_agent)
        except Exception as e:
            logger.error(f"创建工具代理失败: {e}")
            raise

    logger.info(f"已创建 {len(tool_agents)} 个工具代理")
    return tool_agents
