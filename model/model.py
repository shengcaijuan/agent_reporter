"""
模型配置模块 - 支持本地VLLM部署
配置通过 .env 文件管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatTongyi
from typing import Literal, Union

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# 模型类型
AnaModel = Union[ChatOpenAI, ChatTongyi]

# 从环境变量读取配置
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:9997/v1")
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "Qwen3-Instruct")
LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "")
CLOUD_MODEL_NAME = os.getenv("CLOUD_MODEL_NAME", "qwen3.5-plus")
CLOUD_CODER_MODEL_NAME = os.getenv("CLOUD_CODER_MODEL_NAME", "qwen3-coder-480b-a35b-instruct")
CLOUD_API_KEY = os.getenv("CLOUD_API_KEY", "")
DEFAULT_MODEL_TYPE = os.getenv("DEFAULT_MODEL_TYPE", "cloud")

def create_model(
    model_type: Literal["cloud", "local"],
    temperature: float = 0.1
    ):
    """
    创建本地/远程VLLM模型实例
    
    通过ChatOpenAI连接VLLM的OpenAI-compatible API

    Args:
        temperature: 温度参数
    """
    if model_type == "cloud":
        return ChatTongyi(
            model=CLOUD_MODEL_NAME,
            dashscope_api_key=CLOUD_API_KEY,
        )
    elif model_type == "local":
        return ChatOpenAI(
            model=LOCAL_MODEL_NAME,
            temperature=temperature,
            api_key=SecretStr(LOCAL_API_KEY),
            base_url=VLLM_BASE_URL,
            timeout=600,
            max_retries=2,
        )
    elif model_type == "cloud_coder":
        return ChatTongyi(
            model=CLOUD_CODER_MODEL_NAME,
            dashscope_api_key=CLOUD_API_KEY,
        )

qwen_model = create_model(model_type=DEFAULT_MODEL_TYPE)  # type: ignore
qwen_coder = create_model(model_type="cloud_coder")  # type: ignore

if __name__ == "__main__":
    print("=" * 50)
    print(f"Qwen_model类型: {type(qwen_model).__name__}")
    print(f"Qwen_model配置: {qwen_model}")
    response = qwen_model.invoke("你好")
    print(response.content)
    print("=" * 50)

    print("=" * 50)
    print(f"Qwen_coder类型: {type(qwen_coder).__name__}")
    print(f"Qwen_coder配置: {qwen_coder}")
    print("=" * 50)
    response = qwen_coder.invoke("你好")
    print(response.content)
