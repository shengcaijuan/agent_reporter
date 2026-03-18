"""
模板相关数据模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== 模板基础模型 ====================

class TemplateBase(BaseModel):
    """模板基础模型"""
    template_name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")


class TemplateCreate(TemplateBase):
    """创建模板请求"""
    content: str = Field(..., description="HTML内容")


class TemplateUpdate(TemplateBase):
    """更新模板请求"""
    template_name: Optional[str] = Field(None, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    content: Optional[str] = Field(None, description="HTML内容")


# ==================== 模板响应模型 ====================

class TemplateListItem(BaseModel):
    """模板列表项"""
    template_id: str = Field(..., description="模板ID")
    template_name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    is_default: bool = Field(False, description="是否为默认模板")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    file_size: int = Field(0, description="文件大小（字节）")


class TemplateDetail(BaseModel):
    """模板详情"""
    template_id: str = Field(..., description="模板ID")
    template_name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    content: str = Field(..., description="HTML内容")
    is_default: bool = Field(False, description="是否为默认模板")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")


# ==================== 请求模型 ====================

class ApplyTemplateRequest(BaseModel):
    """应用模板请求"""
    task_id: str = Field(..., description="目标任务ID")