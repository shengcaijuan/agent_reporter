"""
数据源配置数据模型
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class AuthType(str, Enum):
    """认证类型"""
    URL_PARAM = "url_param"      # URL参数传递 (如 ?apikey=xxx)
    HEADER = "header"            # Header传递 (如 X-API-Key: xxx)
    BEARER = "bearer"            # Bearer Token (Authorization: Bearer xxx)


class DataSourceType(str, Enum):
    """数据源类型"""
    API = "api"
    DATABASE = "database"
    FILE = "file"


class DataSourceConfig(BaseModel):
    """数据源连接配置"""
    base_url: str = Field(..., description="API基础URL")
    auth_type: AuthType = Field(AuthType.URL_PARAM, description="认证方式")
    auth_key_name: str = Field("apikey", description="认证参数名称")
    api_key: str = Field(..., description="API密钥")
    timeout: int = Field(15, ge=5, le=120, description="请求超时时间（秒）")
    ssl_verify: bool = Field(False, description="是否验证SSL证书")

    @field_validator('base_url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('base_url must start with http:// or https://')
        return v.rstrip('/')


class RequestParamsConfig(BaseModel):
    """请求参数配置"""
    job_id_field: str = Field("ZEMPLOYEE", description="工号字段名")
    time_field: str = Field("CALMONTH", description="时间字段名")
    module_field: str = Field("MOUDLE", description="模块字段名")
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="额外参数")


class DataSource(BaseModel):
    """完整数据源配置"""
    type: DataSourceType = Field(DataSourceType.API, description="数据源类型")
    name: str = Field("默认数据源", description="数据源名称")
    description: Optional[str] = Field(None, description="数据源描述")
    config: DataSourceConfig = Field(..., description="连接配置")
    request_params: RequestParamsConfig = Field(
        default_factory=RequestParamsConfig,
        description="请求参数配置"
    )
    is_default: bool = Field(True, description="是否为默认数据源")
    is_active: bool = Field(True, description="是否启用")


class DataSourceTestRequest(BaseModel):
    """数据源测试请求"""
    base_url: str
    api_key: str
    auth_type: AuthType = AuthType.URL_PARAM
    auth_key_name: str = "apikey"
    test_job_id: Optional[str] = Field(None, description="测试用销售工号")
    test_time: Optional[str] = Field(None, description="测试时间")


class DataSourceTestResponse(BaseModel):
    """数据源测试响应"""
    success: bool
    message: str
    response_time_ms: Optional[int] = None
    data_preview: Optional[Dict[str, Any]] = None