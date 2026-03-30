"""
任务相关数据模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== 任务配置响应 ====================

class ChapterInfo(BaseModel):
    """章节信息"""
    chapter_id: int
    chapter_name: str
    chapter_type: str  # simple, with_tools, summary
    has_tools: bool = False


class SaleInfo(BaseModel):
    """销售人员信息"""
    sale_id: str
    sale_name: str
    department: Optional[str] = None


class TaskDetail(BaseModel):
    """任务详情"""
    task_id: str
    task_name: str
    business_department: Optional[str] = None
    description: Optional[str] = None
    chapters: List[ChapterInfo] = []
    sales: List[SaleInfo] = []


class TaskListItem(BaseModel):
    """任务列表项"""
    task_id: str
    task_name: str
    business_department: Optional[str] = None
    description: Optional[str] = None
    chapters: int = 0  # 章节数量
    status: str = "active"  # 状态：active/inactive
    created_at: Optional[str] = None
    report_count: int = 0  # 已生成的报告数量