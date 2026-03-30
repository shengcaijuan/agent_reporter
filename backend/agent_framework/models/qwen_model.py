"""
Qwen model implementation using OpenAI-compatible API.
Supports DashScope, VLLM, and other OpenAI-compatible endpoints.
"""
import os
import json
from pathlib import Path
from openai import OpenAI, AsyncOpenAI
from typing import List, Optional, Sequence, Any, Dict, Literal, Union
from dotenv import load_dotenv
from .base import BaseModel, BoundModel
from ..tools import BaseTool
from ..messages import BaseMessage, AIMessage, ToolCall


# 加载 .env 文件
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


# Pre-defined endpoints
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
VLLM_BASE_URL = "http://10.20.87.1:9997/v1"

# 从环境变量读取默认配置（作为后备）
DEFAULT_CLOUD_MODEL = os.getenv("CLOUD_MODEL_NAME", "qwen3.5-plus")
DEFAULT_CODER_MODEL = os.getenv("CLOUD_CODER_MODEL_NAME", "qwen3-coder-480b-a35b-instruct")
DEFAULT_LOCAL_MODEL = os.getenv("LOCAL_MODEL_NAME", "Qwen3-Instruct")
DEFAULT_CLOUD_API_KEY = os.getenv("CLOUD_API_KEY", "")
DEFAULT_LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "")
DEFAULT_VLLM_URL = os.getenv("VLLM_BASE_URL", VLLM_BASE_URL)


def _get_model_config_path() -> Path:
    """获取模型配置文件路径"""
    return Path(__file__).parent.parent.parent / "config_files" / "model" / "model_config.json"


def load_model_config() -> Dict[str, Any]:
    """
    从配置文件加载模型配置。

    Returns:
        包含模型配置的字典，如果文件不存在则返回空字典
    """
    config_path = _get_model_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_model_info(model_type: str) -> Dict[str, Any]:
    """
    获取指定类型的模型配置信息。

    优先级：配置文件 > 环境变量 > 默认值

    Args:
        model_type: 模型类型，"cloud" 或 "local"

    Returns:
        包含 model_name, api_key, base_url 的字典
    """
    config = load_model_config()
    models = config.get("models", {})

    if model_type in models:
        model_info = models[model_type]
        return {
            "model_name": model_info.get("model_name"),
            "api_key": model_info.get("api_key"),
            "base_url": model_info.get("base_url"),
            "enabled": model_info.get("enabled", True)
        }

    # 回退到环境变量
    if model_type == "cloud":
        return {
            "model_name": DEFAULT_CLOUD_MODEL,
            "api_key": DEFAULT_CLOUD_API_KEY,
            "base_url": DASHSCOPE_BASE_URL,
            "enabled": True
        }
    elif model_type == "local":
        return {
            "model_name": DEFAULT_LOCAL_MODEL,
            "api_key": DEFAULT_LOCAL_API_KEY,
            "base_url": DEFAULT_VLLM_URL,
            "enabled": True
        }

    return {}


def get_default_model_type() -> str:
    """
    获取默认模型类型。

    Returns:
        默认模型类型，"cloud" 或 "local"
    """
    config = load_model_config()
    return config.get("default_model_type", "cloud")


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
        temperature: float = 0.1,
        **kwargs
    ):
        """
        Initialize the Qwen model.

        Args:
            model: Model name (e.g., "qwen3-max", "Qwen3-Instruct")
            api_key: API key for authentication
            base_url: API endpoint URL
            timeout: Request timeout in seconds
            temperature: Temperature parameter
            **kwargs: Additional parameters passed to the API
        """
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.temperature = temperature
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

    def _convert_message(self, m) -> Dict[str, Any]:
        """
        Convert message to OpenAI format.
        Supports both BaseMessage objects and dict.
        """
        if isinstance(m, dict):
            return m
        if hasattr(m, 'to_openai'):
            return m.to_openai()
        raise ValueError(f"Unsupported message type: {type(m)}")

    def _build_params(
        self,
        messages: Sequence[BaseMessage],
        tools: Optional[List[BaseTool]] = None
    ) -> Dict[str, Any]:
        """Build API request parameters"""
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": [self._convert_message(m) for m in messages],
            "temperature": self.temperature,
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


def create_model(
    model_type: Literal["cloud", "local", "cloud_coder"] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.1,
    use_default: bool = True,
    **kwargs
) -> QwenModel:
    """
    Factory function to create a model instance.

    Args:
        model_type: "cloud" for DashScope, "local" for VLLM, "cloud_coder" for coder model.
                    If None and use_default=True, uses the default type from config file.
        api_key: API key for authentication (optional, uses config file or env var if not provided)
        model: Model name (optional, uses config file or defaults)
        base_url: Custom base URL (optional)
        temperature: Temperature parameter
        use_default: If True and model_type is None, use default model type from config
        **kwargs: Additional parameters

    Returns:
        QwenModel instance

    Example:
        # Use default model type from config
        model = create_model()

        # Cloud model (DashScope)
        model = create_model("cloud", model="qwen3-max")

        # Local model (VLLM)
        model = create_model("local", model="Qwen3-Instruct")
    """
    # 如果没有指定 model_type，使用配置文件中的默认类型
    if model_type is None:
        if use_default:
            model_type = get_default_model_type()
        else:
            model_type = "cloud"  # 默认使用云端模型

    if model_type == "cloud":
        # 从配置文件获取云端模型配置
        config_info = get_model_info("cloud")
        final_model = model or config_info.get("model_name") or DEFAULT_CLOUD_MODEL
        final_api_key = api_key or config_info.get("api_key") or DEFAULT_CLOUD_API_KEY
        final_base_url = base_url or config_info.get("base_url") or DASHSCOPE_BASE_URL

        return QwenModel(
            model=final_model,
            api_key=final_api_key,
            base_url=final_base_url,
            temperature=temperature,
            **kwargs
        )
    elif model_type == "local":
        # 从配置文件获取本地模型配置
        config_info = get_model_info("local")
        final_model = model or config_info.get("model_name") or DEFAULT_LOCAL_MODEL
        final_api_key = api_key or config_info.get("api_key") or DEFAULT_LOCAL_API_KEY
        final_base_url = base_url or config_info.get("base_url") or DEFAULT_VLLM_URL

        return QwenModel(
            model=final_model,
            api_key=final_api_key,
            base_url=final_base_url,
            temperature=temperature,
            **kwargs
        )
    elif model_type == "cloud_coder":
        return QwenModel(
            model=model or DEFAULT_CODER_MODEL,
            api_key=api_key or DEFAULT_CLOUD_API_KEY,
            base_url=base_url or DASHSCOPE_BASE_URL,
            temperature=temperature,
            **kwargs
        )
    else:
        raise ValueError(f"Unknown model_type: {model_type}. Use 'cloud', 'local', or 'cloud_coder'.")


# 预创建的默认模型实例（使用配置文件中的默认类型）
qwen_model = create_model()  # 使用配置文件中的默认模型类型
qwen_coder = create_model(model_type="cloud_coder")

# 类型别名，兼容原项目
AnaModel = Union[QwenModel, BoundModel]