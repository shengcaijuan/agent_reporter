"""
AgentFramework - Lightweight Agent Framework for LLM applications
"""

from agent_framework.agents import ToolAgent
from agent_framework.tools import tool, BaseTool, StructuredTool
from agent_framework.models import QwenModel, create_model, AnaModel, qwen_model, qwen_coder
from agent_framework.messages import (
    SystemMessage, HumanMessage, UserMessage,
    AIMessage, ToolMessage, BaseMessage
)

__version__ = "0.1.0"
__all__ = [
    # Agents
    "ToolAgent",
    # Tools
    "tool",
    "BaseTool",
    "StructuredTool",
    # Models
    "QwenModel",
    "create_model",
    "AnaModel",
    "qwen_model",
    "qwen_coder",
    # Messages
    "SystemMessage",
    "HumanMessage",
    "UserMessage",
    "AIMessage",
    "ToolMessage",
    "BaseMessage",
]