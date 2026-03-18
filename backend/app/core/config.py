"""
配置管理模块
使用 Pydantic Settings 管理应用配置
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "销售报告生成系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API 配置
    API_PREFIX: str = "/api"

    # CORS 配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # JWT 配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./backend/data/app.db"

    # LLM 模型配置 - 云端
    CLOUD_API_KEY: str = ""
    CLOUD_MODEL_NAME: str = "qwen3.5-plus"
    CLOUD_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # LLM 模型配置 - 本地
    LOCAL_API_KEY: str = ""
    LOCAL_MODEL_NAME: str = ""
    LOCAL_BASE_URL: str = ""
    VLLM_BASE_URL: str = ""

    # 默认模型类型
    DEFAULT_MODEL_TYPE: str = "cloud"

    # 数据源配置
    DATA_API_BASE_URL: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略未定义的字段


# 创建全局配置实例
_settings = None


def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    global _settings
    if _settings is None:
        # 尝试从项目根目录加载 .env
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
        if os.path.exists(env_path):
            os.environ["ENV_FILE"] = env_path
        _settings = Settings()
    return _settings


settings = get_settings()