"""
数据库 CRUD 操作
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from app.db.models import User, ReportJob, BatchJob
from app.core.password import get_password_hash, verify_password


# ==================== 用户操作 ====================

def get_user(db: Session, user_id: int) -> Optional[User]:
    """根据 ID 获取用户"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """根据邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """获取用户列表"""
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, username: str, email: str, password: str, is_superuser: bool = False) -> User:
    """创建用户"""
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_superuser=is_superuser
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户"""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def update_user(db: Session, user_id: int, **kwargs) -> Optional[User]:
    """更新用户"""
    user = get_user(db, user_id)
    if not user:
        return None
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    """删除用户"""
    user = get_user(db, user_id)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


# ==================== 报告任务操作 ====================

def get_report_job(db: Session, job_id: str) -> Optional[ReportJob]:
    """获取报告任务"""
    return db.query(ReportJob).filter(ReportJob.job_id == job_id).first()


def get_report_jobs_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[ReportJob]:
    """获取用户的报告任务列表"""
    return db.query(ReportJob).filter(ReportJob.user_id == user_id).offset(skip).limit(limit).all()


def get_report_jobs_by_status(db: Session, status: str) -> List[ReportJob]:
    """根据状态获取报告任务"""
    return db.query(ReportJob).filter(ReportJob.status == status).all()


def create_report_job(
    db: Session,
    task_id: str,
    sale_id: str,
    sale_name: str,
    report_time: str,
    user_id: Optional[int] = None,
    batch_id: Optional[str] = None
) -> ReportJob:
    """创建报告任务"""
    job = ReportJob(
        job_id=str(uuid.uuid4()),
        user_id=user_id,
        batch_id=batch_id,
        task_id=task_id,
        sale_id=sale_id,
        sale_name=sale_name,
        report_time=report_time,
        status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_report_job(db: Session, job_id: str, **kwargs) -> Optional[ReportJob]:
    """更新报告任务"""
    job = get_report_job(db, job_id)
    if not job:
        return None
    for key, value in kwargs.items():
        if hasattr(job, key):
            setattr(job, key, value)
    if kwargs.get("status") == "completed":
        job.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job


def delete_report_job(db: Session, job_id: str) -> bool:
    """删除报告任务"""
    job = get_report_job(db, job_id)
    if not job:
        return False
    db.delete(job)
    db.commit()
    return True


# ==================== 批量任务操作 ====================

def get_batch_job(db: Session, batch_id: str) -> Optional[BatchJob]:
    """获取批量任务"""
    return db.query(BatchJob).filter(BatchJob.batch_id == batch_id).first()


def get_batch_jobs_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[BatchJob]:
    """获取用户的批量任务列表"""
    return db.query(BatchJob).filter(BatchJob.user_id == user_id).offset(skip).limit(limit).all()


def create_batch_job(
    db: Session,
    task_id: str,
    report_time: str,
    total_count: int,
    user_id: Optional[int] = None
) -> BatchJob:
    """创建批量任务"""
    batch = BatchJob(
        batch_id=str(uuid.uuid4()),
        user_id=user_id,
        task_id=task_id,
        report_time=report_time,
        total_count=total_count,
        status="pending"
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def update_batch_job(db: Session, batch_id: str, **kwargs) -> Optional[BatchJob]:
    """更新批量任务"""
    batch = get_batch_job(db, batch_id)
    if not batch:
        return None
    for key, value in kwargs.items():
        if hasattr(batch, key):
            setattr(batch, key, value)
    db.commit()
    db.refresh(batch)
    return batch


def increment_batch_progress(db: Session, batch_id: str, success: bool = True) -> Optional[BatchJob]:
    """更新批量任务进度"""
    batch = get_batch_job(db, batch_id)
    if not batch:
        return None

    if success:
        batch.completed_count += 1
    else:
        batch.failed_count += 1

    # 检查是否完成
    if batch.completed_count + batch.failed_count >= batch.total_count:
        batch.status = "completed"

    db.commit()
    db.refresh(batch)
    return batch