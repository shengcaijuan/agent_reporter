"""
Message 模块 - 定义各类消息对象

该模块提供了与 AI 交互过程中不同类型消息的标准化定义，
包括系统消息、用户消息、AI 回复消息、工具调用消息等，
用于统一消息格式和交互流程。
"""

from .message import SystemMessage, UserMessage, AIMessage, ToolMessage, ToolCall, BaseMessage

__all__ = [
    "ToolCall",
    "UserMessage",
    "SystemMessage",
    "AIMessage",
    "ToolMessage",
    "BaseMessage",
]

__version__ = "0.1.0"


__author__ = "Young"

