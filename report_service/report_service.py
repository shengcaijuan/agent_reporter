# report_service.py
"""
报告服务模块 - 提供报告生成和HTML包装的统一接口

核心功能：
1. 接收前端请求，生成完整报告
2. 协调 report_generator 和 report_wrapping 模块
3. 返回生成的HTML文件路径
"""

import asyncio
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

from runtime.task_runtime import TaskRuntimeLoader
from report_generator.dynamic_report_generator import DynamicReportGenerator
from model import create_model
from logger import get_sales_logger


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
        model_type: str = "cloud"
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
            model_type: 模型类型 ("cloud" 或 "local")
        """
        self.task_id = task_id
        self.time = time
        self.sale_config = sale_config
        self.model_type = model_type

        # 验证任务是否存在
        if not TaskRuntimeLoader.task_exists(task_id):
            raise ValueError(f"任务不存在: {task_id}")

        # 加载任务配置
        self.task_runtime = TaskRuntimeLoader.load_task(task_id)

        # 获取销售信息
        self.sale_id = sale_config.get("job_id", "")
        self.sale_name = sale_config.get("sale_name", "")

        # 创建模型
        self.llm = create_model(model_type=model_type)

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
        # 初始化日志
        sale_id = self.sale_config.get("job_id", "unknown")
        logger = get_sales_logger(
            sale_id=sale_id,
            progress_report_dir=Path("."),
            log_file_name="report_service.log"
        )

        logger.info(f"开始生成报告 - 任务: {self.task_id}, 销售: {self.sale_name}")

        try:
            # 创建报告生成器
            generator = DynamicReportGenerator(
                task_id=self.task_id,
                llm=self.llm,
                time=self.time,
                report_time=self._format_report_time(),
                sale_config=self.sale_config
            )

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


async def generate_report_for_sale(
    task_id: str,
    time: str,
    sale_config: Dict[str, Any],
    model_type: str = "cloud"
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
        sale_config=sale_config,
        model_type=model_type
    )
    return await service.generate_report()


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

        # ========== 测试2: 获取任务详情 ==========
        task_id = tasks[0]["task_id"]
        print(f"\n【测试2】获取任务详情 ({task_id})")
        print("-" * 40)
        info = ReportService.get_task_info(task_id)
        if info:
            print(f"  任务ID: {info['task_id']}")
            print(f"  任务名称: {info['task_name']}")
            print(f"  事业部: {info['business_department']}")
            print(f"  章节数: {info['chapter_count']}")
            print("  章节列表:")
            for ch in info['chapters']:
                tools_str = f", 工具: 是" if ch['has_tools'] else ""
                print(f"    - 章节{ch['chapter_id']}: {ch['chapter_name']} [{ch['chapter_type']}] {tools_str}")

        # ========== 测试3: 测试不存在的任务 ==========
        print("\n【测试3】测试不存在的任务")
        print("-" * 40)
        non_exist_info = ReportService.get_task_info("non_exist_task")
        print(f"  不存在任务返回: {non_exist_info}")

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
                sale_config=test_sale_config,
                model_type="local"
            )
            print(f"  实例创建成功")
            print(f"  任务ID: {service.task_id}")
            print(f"  销售ID: {service.sale_id}")
            print(f"  销售姓名: {service.sale_name}")
            print(f"  报告时间: {service._format_report_time()}")
        except ValueError as e:
            print(f"  实例创建失败: {e}")
            return

        # ========== 测试5: 测试不存在任务的异常 ==========
        print("\n【测试5】测试不存在任务的异常")
        print("-" * 40)
        try:
            invalid_service = ReportService(
                task_id="invalid_task",
                time="202401",
                sale_config=test_sale_config
            )
            print("  异常：应该抛出 ValueError")
        except ValueError as e:
            print(f"  正确捕获异常: {e}")

        # ========== 测试6: 完整报告生成流程 ==========
        print(f"\n【测试6】完整报告生成流程")
        print("-" * 40)
        print(f"  开始生成报告... (这可能需要一些时间)")
        print(f"  任务: {task_id}")
        print(f"  销售: {test_sale_config['sale_name']}")

        result = await service.generate_report()

        print(f"\n  生成结果:")
        print(f"    成功: {result.get('success')}")
        if result.get('success'):
            print(f"    HTML路径: {result.get('html_path')}")
            print(f"    MD路径: {result.get('md_path')}")
            print(f"    报告目录: {result.get('report_dir')}")
        else:
            print(f"    错误信息: {result.get('error')}")
            if result.get('traceback'):
                print(f"\n    详细堆栈:")
                for line in result.get('traceback').split('\n'):
                    print(f"      {line}")

        # ========== 测试7: 使用便捷函数 ==========
        print(f"\n【测试7】使用便捷函数 generate_report_for_sale")
        print("-" * 40)
        result2 = await generate_report_for_sale(
            task_id=task_id,
            time="202402",
            sale_config=test_sale_config,
            model_type="local"
        )
        print(f"  成功: {result2.get('success')}")
        if result2.get('success'):
            print(f"  HTML路径: {result2.get('html_path')}")

        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)

    asyncio.run(test_report_service())