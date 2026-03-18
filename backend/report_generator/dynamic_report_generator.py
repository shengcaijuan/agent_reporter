# dynamic_report_generator.py
"""
动态报告生成器 - 根据任务配置动态创建章节生成器

核心功能：
1. 根据任务配置动态创建章节生成器
2. 支持可变章节数量
3. 支持配置驱动的工具链
4. 支持动态加载guideline
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from runtime.task_runtime import TaskRuntimeLoader
from report_generator.generic_chapter_generator import GenericChapterGenerator, ChapterResult
from report_generator.report_manager import ReportManager
from data.fetch_data import fetch_raw_data_batch
from data.postprocess_data import postproces_chapter_data
from data.check_data import check_data
from report_wrapping.report_wrapping import ReportDecorator
from logger import get_sales_logger, log_raw_data, log_processed_data


class DynamicReportGenerator:
    """
    动态报告生成器

    根据任务配置动态创建章节生成器，支持：
    - 可变章节数量
    - 配置驱动的工具链
    - 动态加载guideline
    """

    def __init__(
        self,
        task_id: str,
        llm,
        time: str,
        report_time: str,
        sale_config: Dict[str, Any],
        province_sales_count: Optional[Dict[str, int]] = None,
        coder_llm=None
    ):
        # 加载任务配置
        self.task_runtime = TaskRuntimeLoader.load_task(task_id)
        self.task_id = task_id

        # 基础配置
        self.llm = llm
        self.coder_llm = coder_llm or llm
        self.time = time
        self.report_time = report_time
        self.sale_config = sale_config
        self.province_sales_count = province_sales_count or {}

        # 销售人员信息
        self.sale_id = sale_config.get("job_id", "")
        self.sale_name = sale_config.get("sale_name", "")

        # 报告目录管理
        self.report_manager = ReportManager(
            task_id=task_id,
            time=time,
            sale_config=sale_config
        )

        # 创建报告目录并获取路径
        self.report_dir, self.progress_report_dir = self.report_manager.create_report_directory()

        # 初始化日志
        self.logger = get_sales_logger(
            sale_id=self.sale_id,
            progress_report_dir=self.progress_report_dir,
            log_file_name="report_generation.log"
        )

        # 存储各章节数据和结果
        self.chapter_data: Dict[int, Dict[str, Any]] = {}
        self.chapter_results: Dict[int, ChapterResult] = {}

    async def run_async(self) -> Path:
        """
        执行完整的报告生成流程

        Returns:
            Path: 生成的PDF文件路径
        """
        self.logger.info(f"开始生成报告 - 任务: {self.task_runtime.task_name}")
        self.logger.info(f"销售人员: {self.sale_name} ({self.sale_id})")

        try:
            # 1. 批量获取章节数据
            await self._fetch_all_chapter_data()

            # 3. 数据检查和后处理
            await self._process_data()

            # 4. 生成各章节内容
            await self._generate_all_chapters()

            # 5. 组装完整报告
            report_content = self._assemble_report()

            # 6. 保存Markdown文件
            md_path = self._save_markdown(report_content)

            # 6. 包装为HTML
            html_path = await self._wrap_to_html(md_path)

            self.logger.info(f"报告生成完成: {html_path}")
            return html_path

        except Exception as e:
            self.logger.error(f"报告生成失败: {str(e)}")
            raise

    async def _fetch_all_chapter_data(self):
        """批量获取所有需要数据的章节的数据"""
        # 收集需要数据的章节（非总结章节）
        chapters_needing_data = [
            ch for ch in self.task_runtime.chapters
            if ch.chapter_type != "summary"
        ]

        if not chapters_needing_data:
            self.logger.info("没有需要获取数据的章节")
            return

        # 构建请求列表（data_module 与 chapter_id 一致）
        requests = [
            {
                "job_id": self.sale_id,
                "time": self.time,
                "module": ch.chapter_id
            }
            for ch in chapters_needing_data
        ]

        self.logger.info(f"开始批量获取 {len(requests)} 个章节的数据")

        # 批量获取数据 (返回字典 {1: result1, 2: result2, ...})
        data_dict = await fetch_raw_data_batch(requests, concurrent_limit=5)

        # 存储数据 - 按索引顺序获取对应的数据
        for i, ch in enumerate(chapters_needing_data, 1):
            raw_data = data_dict.get(i, {})
            self.chapter_data[ch.chapter_id] = raw_data

            # 记录原始数据
            log_raw_data(
                sale_id=self.sale_id,
                sale_name=self.sale_name,
                progress_report_dir=self.progress_report_dir,
                chapter=ch.chapter_id,
                data=raw_data
            )
            self.logger.info(f"章节 {ch.chapter_id} 数据获取完成")

    async def _process_data(self):
        """数据检查和后处理"""
        # 获取销售所属省份
        sale_province = self.sale_config.get("province", "")

        for chapter_id, data in self.chapter_data.items():
            # 检查数据是否为空 (返回 (is_anomaly, message), True表示数据异常)
            is_anomaly, message = check_data(data, module=chapter_id)
            if is_anomaly:
                self.logger.warning(f"章节 {chapter_id} 数据检查未通过: {message}")
                continue

            # 数据后处理（传入省份销售人数用于计算省份排名）
            processed_data = postproces_chapter_data(
                module=chapter_id,
                data=data,
                sale_province=sale_province,
                province_sales_count=self.province_sales_count
            )
            self.chapter_data[chapter_id] = processed_data

            # 记录处理后的数据
            log_processed_data(
                sale_id=self.sale_id,
                sale_name=self.sale_name,
                progress_report_dir=self.progress_report_dir,
                chapter=chapter_id,
                data=processed_data
            )
            self.logger.info(f"章节 {chapter_id} 数据处理完成")

    async def _generate_all_chapters(self):
        """生成所有章节内容"""
        # 分离总结章节和其他章节
        regular_chapters = [
            ch for ch in self.task_runtime.chapters
            if ch.chapter_type != "summary"
        ]
        summary_chapter = self.task_runtime.get_summary_chapter()

        # 并发生成普通章节
        self.logger.info(f"开始并发生成 {len(regular_chapters)} 个普通章节")

        tasks = []
        for chapter in regular_chapters:
            generator = GenericChapterGenerator(
                llm=self.llm,
                chapter_config=chapter,
                data=self.chapter_data.get(chapter.chapter_id, {}),
                sale_id=self.sale_id,
                sale_name=self.sale_name,
                progress_report_dir=self.progress_report_dir
            )
            tasks.append(generator.run_async())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for chapter, result in zip(regular_chapters, results):
            if isinstance(result, Exception):
                self.logger.error(f"章节 {chapter.chapter_id} 生成异常: {str(result)}")
                self.chapter_results[chapter.chapter_id] = ChapterResult(
                    chapter_id=chapter.chapter_id,
                    chapter_name=chapter.chapter_name,
                    content=f"章节生成失败: {str(result)}",
                    success=False,
                    error_message=str(result)
                )
            else:
                self.chapter_results[chapter.chapter_id] = result

        # 生成总结章节（需要等待其他章节完成）
        if summary_chapter:
            self.logger.info(f"开始生成总结章节 {summary_chapter.chapter_id}")

            # 收集前面章节的内容
            previous_contents = {
                ch_id: result.content
                for ch_id, result in self.chapter_results.items()
                if result.success
            }

            summary_generator = GenericChapterGenerator(
                llm=self.llm,
                chapter_config=summary_chapter,
                sale_id=self.sale_id,
                sale_name=self.sale_name,
                progress_report_dir=self.progress_report_dir,
                previous_chapters=previous_contents
            )

            summary_result = await summary_generator.run_async()
            self.chapter_results[summary_chapter.chapter_id] = summary_result

    def _assemble_report(self) -> str:
        """组装完整报告内容"""
        sections = []

        # 添加报告标题
        title = f"# {self.sale_name} {self.report_time} {self.task_runtime.task_name}"
        sections.append(title)

        # 按章节顺序添加内容
        for chapter in self.task_runtime.chapters:
            result = self.chapter_results.get(chapter.chapter_id)
            if result and result.success:
                section = f"\n\n## 第{chapter.chapter_id}章 {chapter.chapter_name}\n\n{result.content}"
                sections.append(section)
            elif result:
                sections.append(f"\n\n## 第{chapter.chapter_id}章 {chapter.chapter_name}\n\n*章节生成失败*")

        return "\n".join(sections)

    def _save_markdown(self, content: str) -> Path:
        """保存Markdown文件"""
        md_path = self.progress_report_dir / f"{self.sale_name}_report.md"

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)

        self.logger.info(f"Markdown文件保存完成: {md_path}")
        return md_path

    async def _wrap_to_html(self, md_path: Path) -> Path:
        """将Markdown包装为HTML"""
        # 读取Markdown内容
        with open(md_path, 'r', encoding='utf-8') as f:
            initial_report = f.read()

        # 获取任务特定的模板路径
        template_path = TaskRuntimeLoader.get_template_path(self.task_id)

        decorator = ReportDecorator(
            llm=self.llm,
            sale_name=self.sale_name,
            initial_report=initial_report,
            html_report_folder=self.report_dir,
            template_path=template_path,
            sale_config=self.sale_config,
            lay_out_requirements=self.task_runtime.lay_out_requirements,
            time=self.time
        )

        html_path = await decorator.wrapping_reports()
        return html_path


if __name__ == "__main__":
    # 测试动态报告生成器
    import asyncio
    from runtime.task_runtime import TaskRuntimeLoader
    from model import qwen_model

    async def test_dynamic_generator():
        # 1. 列出可用任务
        print("=" * 50)
        print("列出可用任务...")
        tasks = TaskRuntimeLoader.list_tasks()
        print(f"可用任务数量: {len(tasks)}")
        for task in tasks:
            print(f"  - {task.get('task_id')}: {task.get('task_name')}")

        # 2. 准备测试配置
        print("\n" + "=" * 50)
        print("准备测试配置...")
        test_sale_config = {
            "job_id": "TEST001",
            "sale_name": "测试销售员",
            "region": "华东区",
            "province": "浙江省",
            "city_operation_department": "杭州运营部",
            "sale_class": "A类",
            "business_department": "马上住焕新事业部"
        }

        # 3. 创建模型实例
        print("\n" + "=" * 50)
        print("创建模型实例...")
        llm = qwen_model

        # 4. 创建动态报告生成器
        print("\n" + "=" * 50)
        print("创建动态报告生成器...")
        generator = DynamicReportGenerator(
            task_id="mashangzhu",
            llm=llm,
            time="202401",  # 测试月份
            report_time="2024年1月",
            sale_config=test_sale_config
        )

        # 5. 显示任务配置信息
        print("\n" + "=" * 50)
        print("任务配置信息:")
        print(f"  任务ID: {generator.task_runtime.task_id}")
        print(f"  任务名称: {generator.task_runtime.task_name}")
        print(f"  事业部: {generator.task_runtime.business_department}")
        print(f"  章节数量: {generator.task_runtime.chapter_count}")

        # 6. 显示各章节信息
        print("\n" + "=" * 50)
        print("章节信息:")
        for chapter in generator.task_runtime.chapters:
            print(f"\n  章节 {chapter.chapter_id}: {chapter.chapter_name}")
            print(f"    - 类型: {chapter.chapter_type}")
            print(f"    - 有工具: {chapter.has_tools}")
            if chapter.summarize_chapters:
                print(f"    - 汇总章节: {chapter.summarize_chapters}")
            if chapter.tool_configs:
                print(f"    - 工具数量: {len(chapter.tool_configs)}")

        # 7. 显示报告目录信息
        print("\n" + "=" * 50)
        print("报告目录信息:")
        print(f"  报告目录: {generator.report_dir}")
        print(f"  进度报告目录: {generator.progress_report_dir}")

        print("\n" + "=" * 50)
        print("测试完成!")
        print("提示: 要执行完整的报告生成，请调用 await generator.run_async()")

    asyncio.run(test_dynamic_generator())