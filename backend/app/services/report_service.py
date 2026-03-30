"""
报告生成服务
封装现有的报告生成逻辑，并提供异步任务管理
"""
import asyncio
import os
from typing import Optional, List, Callable
from datetime import datetime
from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import ReportJob, BatchJob
from app.schemas.report import ReportGenerateRequest, BatchGenerateRequest


class ReportService:
    """报告生成服务"""

    def __init__(self, db: Session):
        self.db = db
        self._running_tasks = {}  # 存储正在运行的任务

    async def generate_single_report(
        self,
        request: ReportGenerateRequest,
        user_id: Optional[int] = None,
        batch_id: Optional[str] = None
    ) -> ReportJob:
        """生成单个报告"""
        # 创建任务记录
        job = crud.create_report_job(
            self.db,
            task_id=request.task_id,
            sale_id=request.sale_id,
            sale_name=request.sale_name,
            report_time=request.report_time,
            user_id=user_id,
            batch_id=batch_id
        )

        # 更新状态为运行中
        crud.update_report_job(self.db, job.job_id, status="running")

        try:
            # 调用现有的报告生成逻辑
            # TODO: 集成现有的 report_service 模块
            # from report_service.report_service import ReportService as OriginalReportService
            # original_service = OriginalReportService(request.task_id, request.report_time, {...})
            # result = await original_service.generate_report()

            # 模拟报告生成（实际集成时替换）
            await asyncio.sleep(2)  # 模拟处理时间

            # 更新任务状态
            report_path = self._get_report_path(request)
            job = crud.update_report_job(
                self.db,
                job.job_id,
                status="completed",
                progress=100,
                report_path=report_path
            )

        except Exception as e:
            # 更新失败状态
            job = crud.update_report_job(
                self.db,
                job.job_id,
                status="failed",
                error_message=str(e)
            )
            raise

        return job

    async def generate_batch_reports(
        self,
        request: BatchGenerateRequest,
        user_id: Optional[int] = None,
        progress_callback: Optional[Callable] = None
    ) -> BatchJob:
        """批量生成报告"""
        # 获取销售名单
        sales = await self._get_sales_list(request.task_id, request.sale_ids)
        total_count = len(sales)

        if total_count == 0:
            raise ValueError("没有找到需要生成报告的销售人员")

        # 创建批量任务记录
        batch = crud.create_batch_job(
            self.db,
            task_id=request.task_id,
            report_time=request.report_time,
            total_count=total_count,
            user_id=user_id
        )

        # 更新状态为运行中
        crud.update_batch_job(self.db, batch.batch_id, status="running")

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(request.concurrent_limit)

        async def generate_with_semaphore(sale_info: dict):
            async with semaphore:
                try:
                    report_request = ReportGenerateRequest(
                        task_id=request.task_id,
                        sale_id=sale_info["sale_id"],
                        sale_name=sale_info["sale_name"],
                        report_time=request.report_time
                    )
                    result = await self.generate_single_report(
                        report_request,
                        user_id=user_id,
                        batch_id=batch.batch_id
                    )
                    crud.increment_batch_progress(self.db, batch.batch_id, success=True)
                    if progress_callback:
                        progress_callback(batch.batch_id, result)
                    return result
                except Exception as e:
                    crud.increment_batch_progress(self.db, batch.batch_id, success=False)
                    raise

        # 并发执行所有任务
        tasks = [generate_with_semaphore(sale) for sale in sales]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 更新最终状态
        batch = crud.get_batch_job(self.db, batch.batch_id)
        return batch

    async def _get_sales_list(self, task_id: str, sale_ids: Optional[List[str]] = None) -> List[dict]:
        """获取销售名单"""
        # TODO: 从配置文件或数据库读取销售名单
        # 这里暂时返回模拟数据
        sales_file = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "report_tasks", task_id, "config_files", "sales", "sales.json"
        )

        if os.path.exists(sales_file):
            import json
            with open(sales_file, "r", encoding="utf-8") as f:
                all_sales = json.load(f)
        else:
            # 返回空列表或模拟数据
            all_sales = []

        # 如果指定了 sale_ids，则过滤
        if sale_ids:
            all_sales = [s for s in all_sales if s.get("sale_id") in sale_ids]

        return all_sales

    def _get_report_path(self, request: ReportGenerateRequest) -> str:
        """获取报告存储路径"""
        return os.path.join(
            "report_tasks",
            request.task_id,
            "reports",
            request.report_time,
            request.sale_id,
            "report.md"
        )

    def get_job_status(self, job_id: str) -> Optional[ReportJob]:
        """获取任务状态"""
        return crud.get_report_job(self.db, job_id)

    def get_batch_status(self, batch_id: str) -> Optional[BatchJob]:
        """获取批量任务状态"""
        return crud.get_batch_job(self.db, batch_id)

    def list_user_reports(self, user_id: int, skip: int = 0, limit: int = 20) -> List[ReportJob]:
        """获取用户的报告列表"""
        return crud.get_report_jobs_by_user(self.db, user_id, skip, limit)