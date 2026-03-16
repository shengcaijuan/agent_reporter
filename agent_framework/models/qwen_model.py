"""
Qwen model implementation using OpenAI-compatible API.
Supports DashScope, VLLM, and other OpenAI-compatible endpoints.
"""
from openai import OpenAI, AsyncOpenAI
from typing import List, Optional, Sequence, Any, Dict
from .base import BaseModel
from ..tools import BaseTool
from ..messages import BaseMessage, AIMessage, ToolCall


class QwenModel(BaseModel):
    """
    Qwen model using OpenAI-compatible API.

    Supports:
    - DashScope (阿里云通义千问)
    - VLLM local deployment
    - Any OpenAI-compatible API
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        timeout: int = 600,
        **kwargs
    ):
        """
        Initialize the Qwen model.

        Args:
            model: Model name (e.g., "qwen3-max", "Qwen3-Instruct")
            api_key: API key for authentication
            base_url: API endpoint URL
            timeout: Request timeout in seconds
            **kwargs: Additional parameters passed to the API
        """
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.kwargs = kwargs

        # Initialize sync client
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )

        # Initialize async client
        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )

    def _build_params(
        self,
        messages: Sequence[BaseMessage],
        tools: Optional[List[BaseTool]] = None
    ) -> Dict[str, Any]:
        """Build API request parameters"""
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_openai() for m in messages],
            **self.kwargs
        }

        if tools:
            params["tools"] = [t.to_openai_schema() for t in tools]

        return params

    def _parse_response(self, response) -> AIMessage:
        """Parse OpenAI response into AIMessage"""
        openai_msg = response.choices[0].message

        tool_calls = []
        if openai_msg.tool_calls:
            for tc in openai_msg.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    function_name=tc.function.name,
                    arguments=tc.function.arguments
                ))

        return AIMessage(
            content=openai_msg.content,
            tool_calls=tool_calls
        )

    def invoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Optional[List[BaseTool]] = None
    ) -> AIMessage:
        """
        Synchronously invoke the model.

        Args:
            messages: List of messages in the conversation
            tools: Optional list of tools the model can call

        Returns:
            AIMessage with the model's response
        """
        params = self._build_params(messages, tools)
        response = self.client.chat.completions.create(**params)
        return self._parse_response(response)

    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Optional[List[BaseTool]] = None
    ) -> AIMessage:
        """
        Asynchronously invoke the model.

        Args:
            messages: List of messages in the conversation
            tools: Optional list of tools the model can call

        Returns:
            AIMessage with the model's response
        """
        params = self._build_params(messages, tools)
        response = await self.async_client.chat.completions.create(**params)
        return self._parse_response(response)


# Pre-defined endpoints
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
VLLM_BASE_URL = "http://10.20.87.1:9997/v1"


def create_model(
    model_type: str,
    api_key: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> QwenModel:
    """
    Factory function to create a model instance.

    Args:
        model_type: "cloud" for DashScope, "local" for VLLM
        api_key: API key for authentication
        model: Model name (optional, uses defaults)
        base_url: Custom base URL (optional)
        **kwargs: Additional parameters

    Returns:
        QwenModel instance

    Example:
        # Cloud model (DashScope)
        model = create_model("cloud", api_key="your-key", model="qwen3-max")

        # Local model (VLLM)
        model = create_model("local", api_key="your-key", model="Qwen3-Instruct")
    """
    if model_type == "cloud":
        return QwenModel(
            model=model or "qwen3-max",
            api_key=api_key,
            base_url=base_url or DASHSCOPE_BASE_URL,
            **kwargs
        )
    elif model_type == "local":
        return QwenModel(
            model=model or "Qwen3-Instruct",
            api_key=api_key,
            base_url=base_url or VLLM_BASE_URL,
            **kwargs
        )
    else:
        raise ValueError(f"Unknown model_type: {model_type}. Use 'cloud' or 'local'.")