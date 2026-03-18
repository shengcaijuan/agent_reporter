# report_service.py
"""
报告服务模块 - 提供报告生成和HTML包装的统一接口

核心功能：
1. 接收前端请求，生成完整报告
2. 支持单个/批量销售报告生成
3. 协调 report_generator 和 report_wrapping 模块
4. 返回生成的HTML文件路径
"""

import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

from pydantic import BaseModel, Field

from runtime.task_runtime import TaskRuntimeLoader
from report_generator.dynamic_report_generator import DynamicReportGenerator
from model import qwen_model, AnaModel
from logger import get_sales_logger


class ReportResult(BaseModel):
    """单个报告生成结果"""
    job_id: str
    sale_name: str
    success: bool
    html_path: Optional[str] = None
    md_path: Optional[str] = None
    report_dir: Optional[str] = None
    error: Optional[str] = None
    traceback: Optional[str] = None


class BatchReportResult(BaseModel):
    """批量报告生成结果"""
    task_id: str
    time: str
    total_count: int
    success_count: int = 0
    failed_count: int = 0
    results: List[ReportResult] = Field(default_factory=list)
    start_time: str = ""
    end_time: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.model_dump(exclude_none=True)


class ReportService:
    """
    报告服务 - 统一的报告生成入口

    提供完整的报告生成流程：
    1. 验证任务配置
    2. 创建报告生成器
    3. 执行报告生成
    4. 返回HTML文件路径
    """

    def __init__(
        self,
        task_id: str,
        time: str,
        sale_config: Dict[str, Any],
        model: AnaModel = qwen_model
    ):
        """
        初始化报告服务

        Args:
            task_id: 任务ID (如: "mashangzhu")
            time: 报告时间 (如: "202401")
            sale_config: 销售人员配置，包含:
                - job_id: 工号
                - sale_name: 姓名
                - region: 大区
                - province: 省区
                - city_operation_department: 城市经营部
                - sale_class: 销售类别
                - business_department: 事业部
            model: 模型实例
        """
        self.task_id = task_id
        self.time = time
        self.sale_config = sale_config
        self.llm = model

        # 验证任务是否存在
        if not TaskRuntimeLoader.task_exists(task_id):
            raise ValueError(f"任务不存在: {task_id}")

        # 加载任务配置
        self.task_runtime = TaskRuntimeLoader.load_task(task_id)

        # 获取销售信息
        self.sale_id = sale_config.get("job_id", "")
        self.sale_name = sale_config.get("sale_name", "")

    async def generate_report(self) -> Dict[str, Any]:
        """
        生成完整报告

        Returns:
            Dict containing:
                - success: bool - 是否成功
                - html_path: str - HTML文件路径（成功时）
                - md_path: str - Markdown文件路径（成功时）
                - error: str - 错误信息（失败时）
        """
        try:
            # 获取省份销售人员数量
            province_sales_count = TaskRuntimeLoader.load_province_sales_count(self.task_id)

            # 创建报告生成器
            generator = DynamicReportGenerator(
                task_id=self.task_id,
                llm=self.llm,
                time=self.time,
                report_time=self._format_report_time(),
                sale_config=self.sale_config,
                province_sales_count=province_sales_count
            )

            # 使用 generator 创建的 logger（日志写入 progress_report 目录）
            logger = generator.logger
            logger.info(f"开始生成报告 - 任务: {self.task_id}, 销售: {self.sale_name}")

            # 执行报告生成
            html_path = await generator.run_async()

            logger.info(f"报告生成成功: {html_path}")

            return {
                "success": True,
                "html_path": str(html_path),
                "md_path": str(generator.progress_report_dir / f"{self.sale_name}_report.md"),
                "report_dir": str(generator.report_dir)
            }

        except Exception as e:
            # 如果 generator 创建失败，使用临时 logger
            logger = get_sales_logger(
                sale_id=self.sale_config.get("job_id", "unknown"),
                progress_report_dir=Path("."),
                log_file_name="report_service.log"
            )
            logger.error(f"报告生成失败: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    def _format_report_time(self) -> str:
        """
        格式化报告时间显示

        将 time (如 "202401") 转换为可读格式 (如 "2024年1月")
        """
        if not self.time or len(self.time) < 6:
            return f"{self.time}"

        year = self.time[:4]
        month = int(self.time[4:6])

        return f"{year}年{month}月"

    @staticmethod
    def list_available_tasks() -> list:
        """列出所有可用任务"""
        return TaskRuntimeLoader.list_tasks()

    @staticmethod
    def get_task_info(task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务配置信息，不存在返回 None
        """
        if not TaskRuntimeLoader.task_exists(task_id):
            return None

        runtime = TaskRuntimeLoader.load_task(task_id)
        return {
            "task_id": runtime.task_id,
            "task_name": runtime.task_name,
            "business_department": runtime.business_department,
            "chapter_count": runtime.chapter_count,
            "chapters": [
                {
                    "chapter_id": ch.chapter_id,
                    "chapter_name": ch.chapter_name,
                    "chapter_type": ch.chapter_type,
                    "has_tools": ch.has_tools
                }
                for ch in runtime.chapters
            ]
        }

    @staticmethod
    def list_sales(task_id: str) -> List[Dict[str, Any]]:
        """
        获取任务的销售名单

        Args:
            task_id: 任务ID

        Returns:
            销售名单列表
        """
        return TaskRuntimeLoader.load_sales_list(task_id)

    @staticmethod
    def get_sale_config(task_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定销售的配置信息

        Args:
            task_id: 任务ID
            job_id: 销售工号

        Returns:
            销售配置，未找到返回 None
        """
        return TaskRuntimeLoader.get_sale_config(task_id, job_id)


class BatchReportService:
    """
    批量报告服务 - 支持批量生成销售报告

    使用方式：
    1. 通过工号列表生成：传入 job_ids
    2. 通过销售配置列表生成：传入 sale_configs
    3. 生成全部销售报告：不传参数，使用全部销售名单
    """

    def __init__(
        self,
        task_id: str,
        time: str,
        model: AnaModel = qwen_model
    ):
        """
        初始化批量报告服务

        Args:
            task_id: 任务ID (如: "mashangzhu")
            time: 报告时间 (如: "202401")
            model: 模型实例
        """
        self.task_id = task_id
        self.time = time
        self.llm = model

        # 验证任务是否存在
        if not TaskRuntimeLoader.task_exists(task_id):
            raise ValueError(f"任务不存在: {task_id}")

        # 加载任务配置
        self.task_runtime = TaskRuntimeLoader.load_task(task_id)

        # 销售名单缓存
        self._sales_list: Optional[List[Dict[str, Any]]] = None

        # 省份销售人员数量缓存
        self._province_sales_count: Optional[Dict[str, int]] = None

    @property
    def sales_list(self) -> List[Dict[str, Any]]:
        """获取销售名单（延迟加载）"""
        if self._sales_list is None:
            self._sales_list = TaskRuntimeLoader.load_sales_list(self.task_id)
        return self._sales_list

    @property
    def province_sales_count(self) -> Dict[str, int]:
        """获取省份销售人员数量（延迟加载）"""
        if self._province_sales_count is None:
            self._province_sales_count = TaskRuntimeLoader.load_province_sales_count(self.task_id)
        return self._province_sales_count

    def _format_report_time(self) -> str:
        """格式化报告时间显示"""
        if not self.time or len(self.time) < 6:
            return f"{self.time}"
        year = self.time[:4]
        month = int(self.time[4:6])
        return f"{year}年{month}月"

    def _get_sale_configs(
        self,
        job_ids: Optional[List[str]] = None,
        sale_configs: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取要生成报告的销售配置列表

        Args:
            job_ids: 工号列表（可选）
            sale_configs: 销售配置列表（可选）

        Returns:
            销售配置列表
        """
        # 优先使用传入的销售配置
        if sale_configs:
            return sale_configs

        # 根据工号列表筛选
        if job_ids:
            job_id_set = set(job_ids)
            return [s for s in self.sales_list if s.get("job_id") in job_id_set]

        # 返回全部销售
        return self.sales_list

    async def generate_single_report(
        self,
        sale_config: Dict[str, Any]
    ) -> ReportResult:
        """
        生成单个销售报告

        Args:
            sale_config: 销售配置

        Returns:
            ReportResult: 生成结果
        """
        job_id = sale_config.get("job_id", "")
        sale_name = sale_config.get("sale_name", "")

        try:
            generator = DynamicReportGenerator(
                task_id=self.task_id,
                llm=self.llm,
                time=self.time,
                report_time=self._format_report_time(),
                sale_config=sale_config,
                province_sales_count=self.province_sales_count
            )

            html_path = await generator.run_async()

            return ReportResult(
                job_id=job_id,
                sale_name=sale_name,
                success=True,
                html_path=str(html_path),
                md_path=str(generator.progress_report_dir / f"{sale_name}_report.md"),
                report_dir=str(generator.report_dir)
            )

        except Exception as e:
            return ReportResult(
                job_id=job_id,
                sale_name=sale_name,
                success=False,
                error=str(e),
                traceback=traceback.format_exc()
            )

    async def generate_reports(
        self,
        job_ids: Optional[List[str]] = None,
        sale_configs: Optional[List[Dict[str, Any]]] = None,
        concurrent_limit: int = 3,
        progress_callback: Optional[Callable[[int, int, ReportResult], None]] = None
    ) -> BatchReportResult:
        """
        批量生成报告

        Args:
            job_ids: 工号列表（可选，与 sale_configs 二选一）
            sale_configs: 销售配置列表（可选，与 job_ids 二选一）
            concurrent_limit: 并发限制数量，默认3
            progress_callback: 进度回调函数 (completed, total, result)

        Returns:
            BatchReportResult: 批量生成结果
        """
        # 获取要生成的销售配置
        target_sales = self._get_sale_configs(job_ids, sale_configs)

        if not target_sales:
            return BatchReportResult(
                task_id=self.task_id,
                time=self.time,
                total_count=0,
                start_time=datetime.now().isoformat(),
                end_time=datetime.now().isoformat()
            )

        # 初始化结果
        batch_result = BatchReportResult(
            task_id=self.task_id,
            time=self.time,
            total_count=len(target_sales),
            start_time=datetime.now().isoformat()
        )

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(concurrent_limit)
        completed_count = 0

        async def generate_with_semaphore(sale_config: Dict[str, Any]) -> ReportResult:
            nonlocal completed_count
            async with semaphore:
                result = await self.generate_single_report(sale_config)
                completed_count += 1

                # 回调进度
                if progress_callback:
                    progress_callback(completed_count, len(target_sales), result)

                return result

        # 并发生成所有报告
        tasks = [generate_with_semaphore(sale) for sale in target_sales]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 汇总结果
        for result in results:
            if isinstance(result, Exception):
                # 不应该发生，但作为保险
                batch_result.failed_count += 1
                batch_result.results.append(ReportResult(
                    job_id="unknown",
                    sale_name="unknown",
                    success=False,
                    error=str(result)
                ))
            else:
                batch_result.results.append(result)
                if result.success:
                    batch_result.success_count += 1
                else:
                    batch_result.failed_count += 1

        batch_result.end_time = datetime.now().isoformat()
        return batch_result

    async def generate_all_reports(
        self,
        concurrent_limit: int = 3,
        progress_callback: Optional[Callable[[int, int, ReportResult], None]] = None
    ) -> BatchReportResult:
        """
        生成全部销售报告

        Args:
            concurrent_limit: 并发限制数量
            progress_callback: 进度回调函数

        Returns:
            BatchReportResult: 批量生成结果
        """
        return await self.generate_reports(
            concurrent_limit=concurrent_limit,
            progress_callback=progress_callback
        )


async def generate_report_for_sale(
    task_id: str,
    time: str,
    sale_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    便捷函数：为销售人员生成报告

    Args:
        task_id: 任务ID
        time: 报告时间
        sale_config: 销售人员配置
        model_type: 模型类型

    Returns:
        生成结果
    """
    service = ReportService(
        task_id=task_id,
        time=time,
        sale_config=sale_config
    )
    return await service.generate_report()


async def generate_reports_batch(
    task_id: str,
    time: str,
    job_ids: Optional[List[str]] = None,
    sale_configs: Optional[List[Dict[str, Any]]] = None,
    concurrent_limit: int = 3,
    progress_callback: Optional[Callable[[int, int, ReportResult], None]] = None
) -> BatchReportResult:
    """
    便捷函数：批量生成销售报告

    Args:
        task_id: 任务ID
        time: 报告时间
        job_ids: 工号列表（可选）
        sale_configs: 销售配置列表（可选）
        concurrent_limit: 并发限制
        progress_callback: 进度回调

    Returns:
        BatchReportResult: 批量生成结果
    """
    service = BatchReportService(task_id=task_id, time=time)
    return await service.generate_reports(
        job_ids=job_ids,
        sale_configs=sale_configs,
        concurrent_limit=concurrent_limit,
        progress_callback=progress_callback
    )


if __name__ == "__main__":
    # 测试报告服务
    async def test_report_service():
        print("=" * 60)
        print("ReportService 测试")
        print("=" * 60)

        # ========== 测试1: 列出可用任务 ==========
        print("\n【测试1】列出可用任务")
        print("-" * 40)
        tasks = ReportService.list_available_tasks()
        print(f"可用任务数量: {len(tasks)}")
        for task in tasks:
            print(f"  - {task['task_id']}: {task['task_name']} ({task['business_department']})")

        if not tasks:
            print("没有可用任务，测试终止")
            return

        task_id = tasks[0]["task_id"]

        # ========== 测试2: 获取销售名单 ==========
        print(f"\n【测试2】获取销售名单 ({task_id})")
        print("-" * 40)
        sales_list = ReportService.list_sales(task_id)
        print(f"销售人数: {len(sales_list)}")
        if sales_list:
            for i, sale in enumerate(sales_list[:5]):
                print(f"  [{i+1}] {sale.get('sale_name')} ({sale.get('job_id')}) - {sale.get('province')}")
            if len(sales_list) > 5:
                print(f"  ... 还有 {len(sales_list) - 5} 个销售")

        # ========== 测试3: 获取任务详情 ==========
        print(f"\n【测试3】获取任务详情 ({task_id})")
        print("-" * 40)
        info = ReportService.get_task_info(task_id)
        if info:
            print(f"  任务ID: {info['task_id']}")
            print(f"  任务名称: {info['task_name']}")
            print(f"  事业部: {info['business_department']}")
            print(f"  章节数: {info['chapter_count']}")

        # ========== 测试4: 创建 ReportService 实例 ==========
        print(f"\n【测试4】创建 ReportService 实例")
        print("-" * 40)
        test_sale_config = {
            "job_id": "TEST001",
            "sale_name": "测试销售员",
            "region": "华东区",
            "province": "浙江省",
            "city_operation_department": "杭州运营部",
            "sale_class": "A类",
            "business_department": "马上住焕新事业部"
        }

        try:
            service = ReportService(
                task_id=task_id,
                time="202401",
                sale_config=test_sale_config
            )
            print(f"  实例创建成功")
            print(f"  任务ID: {service.task_id}")
            print(f"  销售ID: {service.sale_id}")
            print(f"  销售姓名: {service.sale_name}")
        except ValueError as e:
            print(f"  实例创建失败: {e}")
            return

        # ========== 测试5: BatchReportService 批量生成测试 ==========
        print(f"\n【测试5】BatchReportService 批量生成测试")
        print("-" * 40)

        if sales_list and len(sales_list) >= 2:
            # 取前2个销售进行测试
            test_sales = sales_list[:2]
            print(f"测试销售: {[s.get('sale_name') for s in test_sales]}")

            # 创建批量服务
            batch_service = BatchReportService(task_id=task_id, time="202601")
            print(f"批量服务创建成功")

            # 进度回调函数
            def progress_callback(completed: int, total: int, result: ReportResult):
                status = "成功" if result.success else "失败"
                print(f"  进度: {completed}/{total} - {result.sale_name}: {status}")

            # 执行批量生成
            print(f"\n开始批量生成...")
            batch_result = await batch_service.generate_reports(
                sale_configs=test_sales,
                concurrent_limit=2,
                progress_callback=progress_callback
            )

            # 打印结果
            print(f"\n批量生成结果:")
            print(f"  总数: {batch_result.total_count}")
            print(f"  成功: {batch_result.success_count}")
            print(f"  失败: {batch_result.failed_count}")
            print(f"  开始时间: {batch_result.start_time}")
            print(f"  结束时间: {batch_result.end_time}")

            for r in batch_result.results:
                status = "成功" if r.success else f"失败: {r.error}"
                print(f"    - {r.sale_name} ({r.job_id}): {status}")
        else:
            print("  销售名单为空，跳过批量测试")

        # ========== 测试6: 使用便捷函数 generate_reports_batch ==========
        print(f"\n【测试6】使用便捷函数 generate_reports_batch")
        print("-" * 40)

        if sales_list and len(sales_list) >= 2:
            job_ids = [sales_list[0].get('job_id'), sales_list[1].get('job_id')]
            print(f"测试工号: {job_ids}")

            batch_result = await generate_reports_batch(
                task_id=task_id,
                time="202601",
                job_ids=job_ids,
                concurrent_limit=2
            )

            print(f"  成功: {batch_result.success_count}/{batch_result.total_count}")
        else:
            print("  销售名单为空，跳过便捷函数测试")

        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)

    asyncio.run(test_report_service())