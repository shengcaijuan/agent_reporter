"""
SQLAlchemy 数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    report_jobs = relationship("ReportJob", back_populates="user")


class ReportJob(Base):
    """报告生成任务表"""
    __tablename__ = "report_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(50), unique=True, index=True, nullable=False)  # 任务唯一标识
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 关联用户
    task_id = Column(String(100), nullable=False)  # 任务类型 ID
    sale_id = Column(String(100), nullable=False)  # 销售 ID
    sale_name = Column(String(100), nullable=False)  # 销售姓名
    report_time = Column(String(20), nullable=False)  # 报告时间（如 202401）

    status = Column(String(20), default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 进度 0-100
    error_message = Column(Text, nullable=True)  # 错误信息
    report_path = Column(String(500), nullable=True)  # 生成的报告路径

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)  # 完成时间

    # 关联
    user = relationship("User", back_populates="report_jobs")


class BatchJob(Base):
    """批量报告生成任务表"""
    __tablename__ = "batch_jobs"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(50), unique=True, index=True, nullable=False)  # 批量任务唯一标识
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    task_id = Column(String(100), nullable=False)  # 任务类型 ID
    report_time = Column(String(20), nullable=False)  # 报告时间

    total_count = Column(Integer, default=0)  # 总数量
    completed_count = Column(Integer, default=0)  # 完成数量
    failed_count = Column(Integer, default=0)  # 失败数量
    status = Column(String(20), default="pending")  # pending, running, completed, failed

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    user = relationship("User")
    report_jobs = relationship("ReportJob", backref="batch_job", foreign_keys="ReportJob.batch_id")


# 为 ReportJob 添加 batch_id 外键（需要在 BatchJob 定义之后）
ReportJob.batch_id = Column(String(50), ForeignKey("batch_jobs.batch_id"), nullable=True)