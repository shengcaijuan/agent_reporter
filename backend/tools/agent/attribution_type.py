# AttributionType.py
"""归因类型枚举定义"""
from enum import Enum


class AttributionType(str, Enum):
    """归因类型枚举

    用于指定工具代理使用哪种归因分析方法：
    - CONTRIBUTION: 贡献度归因（支持加法/乘法关系）
    - VARIATION: 变动归因
    - THRESHOLD: 阈值归因
    """
    CONTRIBUTION = "contribution"  # 贡献度归因（加法/乘法）
    VARIATION = "variation"        # 变动归因
    THRESHOLD = "threshold"        # 阈值归因
