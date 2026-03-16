from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

class BaseMessage(BaseModel):
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

class UserMessage(BaseMessage):
    """ 用户消息 """
    role: str = "user"

class ToolCall(BaseModel):
    id: str
    function_name: str
    arguments: str  # 通常是 JSON 格式字符串

class AIMessage(BaseMessage):
    """ AI 消息 """
    role: str = "assistant"
    # 允许 content 为空（因为如果调用工具, content 可能是 None)
    content: Optional[str] = None
    # 显式定义 tool_calls 字段
    tool_calls: List[ToolCall] = Field(default_factory=list)

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


