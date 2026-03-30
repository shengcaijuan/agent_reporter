"""
通用响应模型
"""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar("T")


class ResponseBase(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"


class DataResponse(ResponseBase, Generic[T]):
    """数据响应模型"""
    data: Optional[T] = None


class ListResponse(ResponseBase, Generic[T]):
    """列表响应模型"""
    data: List[T] = []
    total: int = 0


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    message: str
    detail: Optional[str] = None