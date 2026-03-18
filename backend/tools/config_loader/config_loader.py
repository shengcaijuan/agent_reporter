# config_loader.py
"""
通用配置加载器 - 从JSON文件加载工具代理配置
支持将JSON中的字符串转换为对应的Python枚举类型

支持的枚举类型：
- AttributionRelationType: "additive" | "multiplicative"
- ThresholdType: "TARGET_ACHIEVEMENT" | "TOTAL_PERFORMANCE_SCORE" |
                 "RECEIVABLES_CONCENTRATION_RATE" | "DUE_RECEIVABLES_COLLECTION_RATE" |
                 "HISTORICAL_OVERDUE_RECEIVABLES_COLLECTION_RATE" |
                 "RATIO_OF_OVERDUE_RECEIVABLES_EXCEEDING_30_DAYS" |
                 "AVERAGE_DEALER_CREDIT_LIMIT_PER_HOUSEHOLD" |
                 "PROBABILITY_OF_OVERDUE_IN_THE_CURRENT_YEAR" | "OUTLET_VISIT_COVERAGE"
"""
import json
from pathlib import Path
from sys import exception
from typing import List, Dict, Any, Union

from tools.attribution.contribution import AttributionRelationType
from tools.attribution.threshold import ThresholdType


def load_agent_config(config_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """
    从JSON文件加载工具代理配置，并转换为Python对象

    Args:
        config_path: 配置文件路径

    Returns:
        配置列表，枚举值已转换为对应的Python枚举对象
    """
    config_path = Path(config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    raw_config = config_data.get("tools", [])

    return _convert_config(raw_config)


def _convert_config(raw_config: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将JSON配置中的字符串转换为对应的Python枚举对象

    Args:
        raw_config: 原始JSON配置列表

    Returns:
        转换后的配置列表
    """
    converted_config = []

    for item in raw_config:
        converted_item = dict(item)

        # 转换 indicators_config 中的枚举值
        if "indicators_config" in converted_item:
            converted_item["indicators_config"] = _convert_indicators_config(
                converted_item["attr_type"],
                converted_item["indicators_config"]
            )

        converted_config.append(converted_item)

    return converted_config


def _convert_indicators_config(
    attr_type: str,
    indicators_config: Any
) -> Any:
    """
    根据归因类型转换 indicators_config 中的枚举值

    Args:
        attr_type: 归因类型 (contribution, variation, threshold)
        indicators_config: 指标配置

    Returns:
        转换后的指标配置
    """
    if attr_type == "contribution":
        # contribution 类型：转换 relation_type
        config = dict(indicators_config)
        if "relation_type" in config:
            relation_type_str = config["relation_type"]
            config["relation_type"] = AttributionRelationType(relation_type_str)
        return config

    elif attr_type == "threshold":
        # threshold 类型：转换 threshold_type
        config_list = []
        for item in indicators_config:
            converted_item = dict(item)
            if "threshold_type" in converted_item:
                threshold_type_str = converted_item["threshold_type"]
                converted_item["threshold_type"] = ThresholdType(threshold_type_str)
            config_list.append(converted_item)
        return config_list

    elif attr_type == "variation":
        # variation 类型：指标列表，无需转换
        return indicators_config

    else:
        return indicators_config


def load_chapter_config(chapter: int) -> List[Dict[str, Any]]:
    """
    加载指定章节的配置（便捷方法）

    Args:
        chapter: 章节号 (1-6)

    Returns:
        配置列表
    """
    config_path = Path(__file__).parent.parent.parent / "report_tasks" / "mashangzhu" / "config_files" / "tool_agent_configs" / f"chapter{chapter}.json"
    return load_agent_config(config_path)


if __name__ == "__main__":
    # 测试所有章节配置加载
    for chapter in [2, 3, 4]:
        try:
            config = load_chapter_config(chapter)
            print(f"\n=== Chapter {chapter} ===")
            print(f"加载了 {len(config)} 个工具配置")
            for i, item in enumerate(config):
                print(f"  {i+1}. {item['tools_config']['tool_name']} ({item['attr_type']})")
        except FileNotFoundError:
            print(f"\n=== Chapter {chapter} ===")
            print(f"  配置文件不存在")