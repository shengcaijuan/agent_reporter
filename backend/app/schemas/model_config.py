"""
模型配置相关 Schema
"""
from typing import Optional
from pydantic import BaseModel


class ModelInfo(BaseModel):
    """单个模型信息"""
    model_name: str
    api_key: str
    base_url: Optional[str] = None
    description: str = ""
    enabled: bool = True


class ModelType(BaseModel):
    """模型类型"""
    type: str
    display_name: str
    description: str = ""


class ModelConfigResponse(BaseModel):
    """模型配置响应"""
    config_name: str
    description: str = ""
    last_updated: str = ""
    default_model_type: str
    models: dict[str, ModelInfo]
    model_types: list[ModelType]


class ModelConfigUpdate(BaseModel):
    """更新模型配置请求"""
    default_model_type: Optional[str] = None
    models: Optional[dict] = None


class ModelInfoUpdate(BaseModel):
    """更新单个模型信息"""
    model_type: str  # cloud 或 local
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None