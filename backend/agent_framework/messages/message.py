from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """消息基类"""
    role: str
    content: Union[str, List[Dict]] # 支持纯文本或多模态

    def to_openai(self) -> Dict[str, Any]:
        """ 将对象转为 OpenAI API 需要的字典格式 """
        message = {
            "role": self.role,
            "content": self.content
        }
        return message


class SystemMessage(BaseMessage):
    """ 系统消息 """
    role: str = "system"


class HumanMessage(BaseMessage):
    """ 用户消息 (别名: UserMessage) """
    role: str = "user"


# 别名，与 UserMessage 等价
UserMessage = HumanMessage


class ToolCallResult(BaseModel):
    """
    工具调用结果 - 兼容 langchain 格式
    包含 name 和 args 字段，方便工具调用
    """
    name: str
    args: Dict[str, Any]
    id: str = ""
    type: str = "tool_call"


class ToolCall(BaseModel):
    """工具调用 - OpenAI API 格式"""
    id: str
    function_name: str
    arguments: str  # JSON 格式字符串


class AIMessage(BaseMessage):
    """ AI 消息 """
    role: str = "assistant"
    # 允许 content 为空（因为如果调用工具, content 可能是 None)
    content: Optional[str] = None
    # 内部存储 OpenAI 格式的 tool_calls
    tool_calls: List[ToolCall] = Field(default_factory=list)

    @property
    def tool_calls_lc(self) -> List[ToolCallResult]:
        """
        返回 langchain 兼容格式的 tool_calls
        格式: [{"name": "tool_name", "args": {...}, "id": "xxx", "type": "tool_call"}]
        """
        import json
        result = []
        for tc in self.tool_calls:
            try:
                args = json.loads(tc.arguments) if tc.arguments else {}
            except json.JSONDecodeError:
                args = {}
            result.append(ToolCallResult(
                name=tc.function_name,
                args=args,
                id=tc.id,
                type="tool_call"
            ))
        return result

    def to_openai(self) -> Dict[str, Any]:
        message = {"role": self.role}
        if self.content:
            message["content"] = self.content

        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function_name,
                        "arguments": tc.arguments
                    }
                }
                for tc in self.tool_calls
            ]

        return message


class ToolMessage(BaseMessage):
    """ 工具消息 """
    role: str = "tool"
    tool_call_id: str   # 必须字段，对应 AI Message 里的 id

    def to_openai(self) -> Dict[str, Any]:
        message = {
            "role": self.role,
            "content": self.content,
            "tool_call_id": self.tool_call_id
        }
        return message


