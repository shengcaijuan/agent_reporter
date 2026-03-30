"""
报告相关数据模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class SaleFilter(BaseModel):
    """销售人员筛选条件"""
    type: str = Field("all", description="筛选类型: all/filter/specific")
    job_ids: Optional[List[str]] = Field(None, description="指定的销售工号列表")
    region: Optional[str] = Field(None, description="大区筛选")
    province: Optional[str] = Field(None, description="省区筛选")
    sale_class: Optional[str] = Field(None, description="岗位筛选")


class ReportGenerateRequest(BaseModel):
    """报告生成请求（统一接口）"""
    task_id: str = Field(..., description="任务 ID")
    time: str = Field(..., description="报告时间，如 202401")
    max_concurrent: int = Field(3, ge=1, le=100, description="并发限制")
    sale_filter: Optional[SaleFilter] = Field(None, description="销售人员筛选条件")


class SingleReportRequest(BaseModel):
    """单个报告生成请求"""
    task_id: str = Field(..., description="任务 ID")
    sale_id: str = Field(..., description="销售 ID")
    sale_name: str = Field(..., description="销售姓名")
    report_time: str = Field(..., description="报告时间，如 202401")


class BatchGenerateRequest(BaseModel):
    """批量报告生成请求"""
    task_id: str = Field(..., description="任务 ID")
    report_time: str = Field(..., description="报告时间")
    sale_ids: Optional[List[str]] = Field(None, description="指定销售 ID 列表，为空则生成所有")
    concurrent_limit: int = Field(3, ge=1, le=10, description="并发限制")


# ==================== 响应模型 ====================

class ReportJobResponse(BaseModel):
    """报告任务响应"""
    job_id: str
    task_id: str
    sale_id: str
    sale_name: str
    report_time: str
    status: str
    progress: int
    error_message: Optional[str] = None
    report_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BatchJobResponse(BaseModel):
    """批量任务响应"""
    batch_id: str
    task_id: str
    report_time: str
    total_count: int
    completed_count: int
    failed_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BatchJobDetail(BatchJobResponse):
    """批量任务详情（包含子任务列表）"""
    jobs: List[ReportJobResponse] = []


class ReportContent(BaseModel):
    """报告内容"""
    job_id: str
    sale_id: str
    sale_name: str
    report_time: str
    content: str  # Markdown 内容
    html_content: Optional[str] = None  # HTML 内容
    created_at: datetime


class GeneratedReportItem(BaseModel):
    """已生成报告项（从文件系统读取）"""
    filename: str = Field(..., description="文件名")
    sale_name: str = Field(..., description="销售姓名")
    job_id: Optional[str] = Field(None, description="工号")
    report_time: str = Field(..., description="报告月份")
    business_department: Optional[str] = Field(None, description="事业部")
    region: Optional[str] = Field(None, description="大区")
    province: Optional[str] = Field(None, description="省区")
    city_operation_department: Optional[str] = Field(None, description="城市经营部")
    file_path: str = Field(..., description="文件路径")


class GeneratedReportListResponse(BaseModel):
    """已生成报告列表响应"""
    reports: List[GeneratedReportItem]
    total: int


class SaleProgressItem(BaseModel):
    """销售进度项"""
    job_id: str = ""
    sale_name: str = ""
    province: Optional[str] = ""
    region: Optional[str] = ""
    stage: str = ""


class GenerationStatusResponse(BaseModel):
    """生成任务状态响应"""
    batch_id: Optional[str] = None
    task_id: str
    task_name: Optional[str] = None
    status: str  # idle, running, paused, completed, error
    total: int = 0
    completed: int = 0
    failed: int = 0
    in_progress: int = 0
    paused: int = 0  # 暂停的任务数
    start_time: Optional[datetime] = None
    report_time: Optional[str] = None
    processing_sales: List[SaleProgressItem] = []
    pending_sales: List[SaleProgressItem] = []


class OrganizationItem(BaseModel):
    """组织架构项"""
    name: str
    type: str  # region, province, department
    children: Optional[List['OrganizationItem']] = None


class OrganizationResponse(BaseModel):
    """组织架构响应"""
    regions: List[str]
    provinces: List[str]
    sale_classes: List[str]
    tree: Optional[List[OrganizationItem]] = None