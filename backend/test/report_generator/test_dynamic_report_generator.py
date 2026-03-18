# test_dynamic_report_generator.py
"""
DynamicReportGenerator 单元测试

测试功能：
1. 动态报告生成流程
2. 打印工具函数调用、工具返回结果、章节分析结果
3. 验证报告生成完整性
4. 支持使用真实销售数据测试
5. 单章节测试（带详细日志记录）
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

# 项目模块导入
from report_generator.dynamic_report_generator import DynamicReportGenerator
from report_generator.generic_chapter_generator import GenericChapterGenerator
from runtime.task_runtime import TaskRuntimeLoader, load_sales_list, get_sale_config
from model import qwen_model
from tools.agent.tool_agent import ToolFunctionAgent
from tools.agent.tool_executor import ToolNodeAgent
from data.fetch_data import fetch_raw_data, fetch_raw_data_batch


# 日志目录
LOG_DIR = Path(__file__).parent / "log"
LOG_DIR.mkdir(exist_ok=True)


def print_separator(title: str = ""):
    """打印分隔线"""
    print("\n" + "=" * 60)
    if title:
        print(f" {title}")
        print("=" * 60)


def print_tool_call(tool_name: str, tool_args: Dict[str, Any]):
    """打印工具函数调用"""
    print("\n" + "-" * 50)
    print(f"[TOOL_CALL] 工具函数调用")
    print(f"  工具名称: {tool_name}")
    print(f"  工具参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}")
    print("-" * 50)


def print_tool_result(tool_name: str, nl_output: str, raw_output: Any = None):
    """打印工具返回结果"""
    print("\n" + "-" * 50)
    print(f"[TOOL_RESULT] 工具返回结果")
    print(f"  工具名称: {tool_name}")
    print(f"  自然语言输出:\n{nl_output}")
    if raw_output:
        print(f"  原始输出类型: {type(raw_output).__name__}")
    print("-" * 50)


def print_chapter_result(chapter_id: int, chapter_name: str, content: str, success: bool):
    """打印章节分析结果"""
    print("\n" + "-" * 50)
    print(f"[CHAPTER_RESULT] 章节分析结果")
    print(f"  章节ID: {chapter_id}")
    print(f"  章节名称: {chapter_name}")
    print(f"  生成状态: {'成功' if success else '失败'}")
    print(f"  内容长度: {len(content)} 字符")
    print(f"  内容预览:\n{content[:500]}..." if len(content) > 500 else f"  内容:\n{content}")
    print("-" * 50)


class TestDynamicReportGenerator:
    """DynamicReportGenerator 测试类"""

    def __init__(self):
        self.test_sale_config = {
            "job_id": "TEST001",
            "sale_name": "测试销售员",
            "region": "华东区",
            "province": "浙江省",
            "city_operation_department": "杭州运营部",
            "sale_class": "A类",
            "business_department": "马上住焕新事业部"
        }
        self.tool_calls_log = []
        self.tool_results_log = []

    def setup_patches(self):
        """设置补丁以捕获工具调用和结果"""

        # 保存原始方法
        original_execute_tool_call = ToolNodeAgent._execute_tool_call
        original_run = ToolNodeAgent.run
        self._original_execute_tool_call = original_execute_tool_call
        self._original_run = original_run

        def patched_execute_tool_call(self, tool_call: dict):
            """补丁：捕获并打印工具调用"""
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 打印工具调用
            print_tool_call(tool_name, tool_args)

            # 记录日志
            self.tool_calls_log.append({
                "tool_name": tool_name,
                "tool_args": tool_args
            })

            # 调用原始方法
            nl_output, raw_output = original_execute_tool_call(self, tool_call)

            # 打印工具结果
            print_tool_result(tool_name, nl_output, raw_output)

            # 记录日志
            self.tool_results_log.append({
                "tool_name": tool_name,
                "nl_output": nl_output,
                "raw_output": str(raw_output) if raw_output else None
            })

            return nl_output, raw_output

        # 应用补丁
        ToolNodeAgent._execute_tool_call = patched_execute_tool_call

        return self

    def restore_patches(self):
        """恢复原始方法"""
        ToolNodeAgent._execute_tool_call = self._original_execute_tool_call

    async def test_task_list(self):
        """测试1: 列出可用任务"""
        print_separator("测试1: 列出可用任务")

        tasks = TaskRuntimeLoader.list_tasks()
        print(f"可用任务数量: {len(tasks)}")
        for task in tasks:
            print(f"  - {task.get('task_id')}: {task.get('task_name')}")

        return tasks

    async def test_task_loading(self, task_id: str = "mashangzhu"):
        """测试2: 加载任务配置"""
        print_separator("测试2: 加载任务配置")

        try:
            task_runtime = TaskRuntimeLoader.load_task(task_id)

            print(f"任务ID: {task_runtime.task_id}")
            print(f"任务名称: {task_runtime.task_name}")
            print(f"事业部: {task_runtime.business_department}")
            print(f"章节数量: {task_runtime.chapter_count}")

            print("\n章节详情:")
            for chapter in task_runtime.chapters:
                print(f"\n  章节 {chapter.chapter_id}: {chapter.chapter_name}")
                print(f"    - 类型: {chapter.chapter_type}")
                print(f"    - 有工具: {chapter.has_tools}")
                if chapter.has_tools and chapter.tool_configs:
                    print(f"    - 工具数量: {len(chapter.tool_configs)}")
                    for i, tc in enumerate(chapter.tool_configs):
                        print(f"      工具{i+1}: {tc.get('tools_config', {}).get('tool_name', 'unknown')}")
                if chapter.summarize_chapters:
                    print(f"    - 汇总章节: {chapter.summarize_chapters}")

            return task_runtime

        except FileNotFoundError as e:
            print(f"任务配置不存在: {e}")
            print("请确保任务配置目录存在: report_tasks/{task_id}/config_files/")
            return None

    async def test_single_chapter_generation(self, task_id: str = "mashangzhu"):
        """测试3: 单章节生成测试"""
        print_separator("测试3: 单章节生成测试")

        from report_generator.generic_chapter_generator import GenericChapterGenerator

        # 加载任务
        task_runtime = TaskRuntimeLoader.load_task(task_id)

        # 获取第一个带工具的章节
        chapter_with_tools = None
        for chapter in task_runtime.chapters:
            if chapter.has_tools:
                chapter_with_tools = chapter
                break

        if not chapter_with_tools:
            print("未找到带工具的章节，使用第一个章节测试")
            chapter_with_tools = task_runtime.chapters[0]

        print(f"测试章节: {chapter_with_tools.chapter_name}")
        print(f"章节类型: {chapter_with_tools.chapter_type}")

        # 准备测试数据
        test_data = self._get_test_data(chapter_with_tools.chapter_id)

        # 设置补丁以捕获工具调用
        self.setup_patches()

        try:
            # 创建章节生成器
            generator = GenericChapterGenerator(
                llm=qwen_model,
                chapter_config=chapter_with_tools,
                data=test_data,
                sale_id=self.test_sale_config["job_id"],
                sale_name=self.test_sale_config["sale_name"],
                progress_report_dir=Path("./test_output")
            )

            print(f"\n开始生成章节...")

            # 运行生成
            result = await generator.run_async()

            # 打印章节结果
            print_chapter_result(
                chapter_id=result.chapter_id,
                chapter_name=result.chapter_name,
                content=result.content,
                success=result.success
            )

            if not result.success:
                print(f"错误信息: {result.error_message}")

            # 打印工具调用统计
            self._print_tool_stats()

            return result

        finally:
            # 恢复补丁
            self.restore_patches()

    async def test_full_report_generation(self, task_id: str = "mashangzhu"):
        """测试4: 完整报告生成流程"""
        print_separator("测试4: 完整报告生成流程")

        # 设置补丁以捕获工具调用
        self.setup_patches()
        self.tool_calls_log = []
        self.tool_results_log = []

        try:
            # 创建报告生成器
            generator = DynamicReportGenerator(
                task_id=task_id,
                llm=qwen_model,
                time="202601",
                report_time="2026年1月",
                sale_config=self.test_sale_config
            )

            print(f"任务: {generator.task_runtime.task_name}")
            print(f"报告目录: {generator.report_dir}")
            print(f"进度目录: {generator.progress_report_dir}")

            print("\n开始生成报告...")

            # 运行完整流程
            html_path = await generator.run_async()

            print(f"\n报告生成完成!")
            print(f"HTML路径: {html_path}")

            # 打印所有章节结果
            print("\n" + "=" * 60)
            print(" 所有章节生成结果汇总")
            print("=" * 60)

            for chapter_id, result in generator.chapter_results.items():
                print_chapter_result(
                    chapter_id=result.chapter_id,
                    chapter_name=result.chapter_name,
                    content=result.content,
                    success=result.success
                )

            # 打印工具调用统计
            self._print_tool_stats()

            return html_path

        except Exception as e:
            import traceback
            print(f"\n报告生成失败: {e}")
            traceback.print_exc()
            raise

        finally:
            # 恢复补丁
            self.restore_patches()

    async def test_with_mock_data(self, task_id: str = "mashangzhu"):
        """测试5: 使用模拟数据的快速测试"""
        print_separator("测试5: 使用模拟数据的快速测试")

        from report_generator.generic_chapter_generator import GenericChapterGenerator

        # 加载任务
        task_runtime = TaskRuntimeLoader.load_task(task_id)

        # 获取第一个章节
        chapter = task_runtime.chapters[0]

        # 模拟数据
        mock_data = {
            "绩效得分": 85.5,
            "排名": 15,
            "销售额": 1000000,
            "销售目标": 800000,
            "完成率": 1.25,
            "items": [
                {"name": "销售额", "score": 90, "target": 100},
                {"name": "客户开发", "score": 80, "target": 100}
            ]
        }

        print(f"测试章节: {chapter.chapter_name}")
        print(f"模拟数据: {json.dumps(mock_data, ensure_ascii=False, indent=2)}")

        # 创建生成器
        generator = GenericChapterGenerator(
            llm=qwen_model,
            chapter_config=chapter,
            data=mock_data,
            sale_id="MOCK001",
            sale_name="模拟销售员"
        )

        # 运行生成
        result = await generator.run_async()

        print_chapter_result(
            chapter_id=result.chapter_id,
            chapter_name=result.chapter_name,
            content=result.content,
            success=result.success
        )

        return result

    def _get_test_data(self, chapter_id: int) -> Dict[str, Any]:
        """获取测试数据"""
        # 根据章节返回不同的测试数据
        test_data_map = {
            1: {  # 薪资绩效
                "绩效得分": 85.5,
                "排名": 15,
                "薪资": 15000,
                "绩效奖金": 5000
            },
            2: {  # 销售势头
                "销售额": 1000000,
                "销售目标": 800000,
                "同期销售额": 900000,
                "环比增长": 0.11,
                "同比增长": 0.05
            },
            3: {  # 毛利与产品结构
                "毛利": 200000,
                "毛利率": 0.2,
                "高值品收入": 600000,
                "非高值品收入": 400000
            },
            4: {  # 费用与应收
                "费用": 50000,
                "费用率": 0.05,
                "应收账款": 200000,
                "逾期应收": 50000
            },
            5: {  # 销售行为
                "拜访次数": 50,
                "成交单数": 20,
                "客户开发数": 10
            }
        }
        return test_data_map.get(chapter_id, {})

    async def test_load_sales_list(self, task_id: str = "mashangzhu"):
        """测试6: 加载销售名单"""
        print_separator("测试6: 加载销售名单")

        # 检查销售名单是否存在
        if not TaskRuntimeLoader.sales_list_exists(task_id):
            print(f"任务 {task_id} 没有销售名单配置")
            return []

        # 加载销售名单
        sales_list = load_sales_list(task_id)

        print(f"销售人数: {len(sales_list)}")
        print("\n销售名单:")
        for i, sale in enumerate(sales_list[:10]):  # 只显示前10个
            print(f"  [{i+1}] {sale.get('sale_name')} ({sale.get('job_id')}) - {sale.get('province')}")
        if len(sales_list) > 10:
            print(f"  ... 还有 {len(sales_list) - 10} 个销售")

        return sales_list

    async def test_with_real_sale(
        self,
        task_id: str = "mashangzhu",
        job_id: str = "00165",
        time: str = "202601"
    ):
        """测试7: 使用真实销售数据生成报告"""
        print_separator("测试7: 使用真实销售数据生成报告")

        # 1. 获取销售配置
        sale_config = get_sale_config(task_id, job_id)
        if not sale_config:
            print(f"未找到工号为 {job_id} 的销售")
            # 尝试加载第一个销售
            sales_list = load_sales_list(task_id)
            if sales_list:
                sale_config = sales_list[0]
                print(f"使用第一个销售: {sale_config.get('sale_name')} ({sale_config.get('job_id')})")
            else:
                print("没有可用的销售数据")
                return None

        print(f"销售信息:")
        print(f"  工号: {sale_config.get('job_id')}")
        print(f"  姓名: {sale_config.get('sale_name')}")
        print(f"  省区: {sale_config.get('province')}")
        print(f"  大区: {sale_config.get('region')}")
        print(f"  岗位: {sale_config.get('sale_class')}")

        # 2. 设置补丁以捕获工具调用
        self.setup_patches()
        self.tool_calls_log = []
        self.tool_results_log = []

        try:
            # 3. 创建报告生成器
            generator = DynamicReportGenerator(
                task_id=task_id,
                llm=qwen_model,
                time=time,
                report_time=f"{time[:4]}年{time[4:]}月",
                sale_config=sale_config
            )

            print(f"\n任务: {generator.task_runtime.task_name}")
            print(f"报告目录: {generator.report_dir}")

            print("\n开始生成报告...")

            # 4. 运行完整流程
            html_path = await generator.run_async()

            print(f"\n报告生成完成!")
            print(f"HTML路径: {html_path}")

            # 5. 打印所有章节结果
            print("\n" + "=" * 60)
            print(" 所有章节生成结果汇总")
            print("=" * 60)

            for chapter_id, result in generator.chapter_results.items():
                print_chapter_result(
                    chapter_id=result.chapter_id,
                    chapter_name=result.chapter_name,
                    content=result.content,
                    success=result.success
                )

            # 6. 打印工具调用统计
            self._print_tool_stats()

            return html_path

        except Exception as e:
            import traceback
            print(f"\n报告生成失败: {e}")
            traceback.print_exc()
            raise

        finally:
            # 恢复补丁
            self.restore_patches()

    async def test_batch_with_real_sales(
        self,
        task_id: str = "mashangzhu",
        job_ids: Optional[List[str]] = None,
        time: str = "202601",
        max_count: int = 3
    ):
        """测试8: 批量使用真实销售数据生成报告"""
        print_separator("测试8: 批量真实销售数据测试")

        # 1. 加载销售名单
        sales_list = load_sales_list(task_id)
        if not sales_list:
            print(f"任务 {task_id} 没有销售名单配置")
            return

        # 2. 筛选要测试的销售
        if job_ids:
            test_sales = [s for s in sales_list if s.get('job_id') in job_ids]
        else:
            test_sales = sales_list[:max_count]

        print(f"待测试销售数量: {len(test_sales)}")
        for i, sale in enumerate(test_sales):
            print(f"  [{i+1}] {sale.get('sale_name')} ({sale.get('job_id')})")

        # 3. 设置补丁
        self.setup_patches()

        results = []
        try:
            for i, sale_config in enumerate(test_sales):
                print(f"\n{'='*60}")
                print(f" [{i+1}/{len(test_sales)}] 开始生成 {sale_config.get('sale_name')} 的报告")
                print(f"{'='*60}")

                self.tool_calls_log = []
                self.tool_results_log = []

                try:
                    generator = DynamicReportGenerator(
                        task_id=task_id,
                        llm=qwen_model,
                        time=time,
                        report_time=f"{time[:4]}年{time[4:]}月",
                        sale_config=sale_config
                    )

                    html_path = await generator.run_async()

                    results.append({
                        "sale_name": sale_config.get('sale_name'),
                        "job_id": sale_config.get('job_id'),
                        "success": True,
                        "html_path": str(html_path),
                        "tool_calls": len(self.tool_calls_log)
                    })

                    print(f"\n完成! HTML路径: {html_path}")

                except Exception as e:
                    results.append({
                        "sale_name": sale_config.get('sale_name'),
                        "job_id": sale_config.get('job_id'),
                        "success": False,
                        "error": str(e)
                    })
                    print(f"\n失败: {e}")

        finally:
            self.restore_patches()

        # 4. 打印汇总结果
        print("\n" + "=" * 60)
        print(" 批量测试结果汇总")
        print("=" * 60)

        success_count = sum(1 for r in results if r['success'])
        print(f"成功: {success_count}/{len(results)}")

        for r in results:
            status = "✓" if r['success'] else "✗"
            print(f"  [{status}] {r['sale_name']} ({r['job_id']})")
            if r['success']:
                print(f"       工具调用: {r['tool_calls']} 次")
            else:
                print(f"       错误: {r.get('error', 'unknown')}")

        return results

    async def test_single_chapter_with_logging(
        self,
        task_id: str = "mashangzhu",
        chapter_id: int = 2,
        job_id: str = "00165",
        time: str = "202601"
    ):
        """
        测试单章节生成（带详细日志记录）

        记录内容：
        1. 输入数据
        2. 工具函数调用
        3. 工具函数返回结果
        4. 模型分析输出

        日志保存到: test/report_generator/log/
        """
        print_separator(f"测试: 第二章生成测试（带日志记录）")

        # 创建日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = LOG_DIR / f"chapter{chapter_id}_{job_id}_{timestamp}.log"

        # 设置日志记录器
        logger = logging.getLogger(f"chapter{chapter_id}_test")
        logger.setLevel(logging.DEBUG)

        # 清除已有的处理器
        logger.handlers = []

        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(console_handler)

        logger.info(f"=" * 60)
        logger.info(f"第二章生成测试 - 日志文件: {log_file}")
        logger.info(f"=" * 60)

        # ========== 1. 获取销售配置 ==========
        logger.info(f"\n[步骤1] 获取销售配置")
        sale_config = get_sale_config(task_id, job_id)
        if not sale_config:
            sales_list = load_sales_list(task_id)
            if sales_list:
                sale_config = sales_list[0]
                logger.info(f"未找到工号 {job_id}，使用第一个销售: {sale_config.get('sale_name')}")
            else:
                logger.error("没有可用的销售数据")
                return None

        logger.info(f"销售工号: {sale_config.get('job_id')}")
        logger.info(f"销售姓名: {sale_config.get('sale_name')}")
        logger.info(f"省区: {sale_config.get('province')}")
        logger.info(f"大区: {sale_config.get('region')}")

        # ========== 2. 加载任务配置 ==========
        logger.info(f"\n[步骤2] 加载任务配置")
        task_runtime = TaskRuntimeLoader.load_task(task_id)
        chapter_config = task_runtime.get_chapter(chapter_id)

        if not chapter_config:
            logger.error(f"章节 {chapter_id} 不存在")
            return None

        logger.info(f"章节ID: {chapter_config.chapter_id}")
        logger.info(f"章节名称: {chapter_config.chapter_name}")
        logger.info(f"章节类型: {chapter_config.chapter_type}")
        logger.info(f"是否有工具: {chapter_config.has_tools}")

        if chapter_config.has_tools:
            logger.info(f"工具数量: {len(chapter_config.tool_configs)}")
            for i, tc in enumerate(chapter_config.tool_configs):
                tool_name = tc.get('tools_config', {}).get('tool_name', 'unknown')
                attr_type = tc.get('attr_type', 'unknown')
                logger.info(f"  工具{i+1}: {tool_name} (类型: {attr_type})")

        # ========== 3. 获取真实数据 ==========
        logger.info(f"\n[步骤3] 获取章节数据")
        logger.info(f"请求参数: job_id={job_id}, time={time}, module={chapter_id}")

        raw_data = await fetch_raw_data(
            job_id=job_id,
            time=time,
            module=chapter_id
        )

        # 记录输入数据
        logger.info(f"\n" + "=" * 60)
        logger.info(f"[输入数据] 原始数据")
        logger.info(f"=" * 60)
        logger.debug(f"数据类型: {type(raw_data)}")

        if isinstance(raw_data, dict):
            if "error" in raw_data:
                logger.error(f"数据获取失败: {raw_data}")
                return None

            # 记录数据结构
            logger.info(f"数据键: {list(raw_data.keys())}")

            # 记录完整数据到日志（DEBUG级别）
            logger.debug(f"\n完整数据:\n{json.dumps(raw_data, ensure_ascii=False, indent=2)}")

            # 记录数据摘要
            data_summary = {}
            for key, value in raw_data.items():
                if isinstance(value, list):
                    data_summary[key] = f"列表({len(value)}项)"
                elif isinstance(value, dict):
                    data_summary[key] = f"字典({len(value)}键)"
                else:
                    data_summary[key] = str(value)[:50]
            logger.info(f"数据摘要: {json.dumps(data_summary, ensure_ascii=False)}")
        else:
            logger.info(f"数据: {raw_data}")

        # ========== 4. 设置工具调用捕获 ==========
        logger.info(f"\n[步骤4] 设置工具调用捕获")

        # 保存原始方法
        original_execute_tool_call = ToolNodeAgent._execute_tool_call
        tool_call_records = []

        def patched_execute_tool_call(self, tool_call: dict):
            """补丁：捕获并记录工具调用"""
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 记录工具调用
            record = {
                "timestamp": datetime.now().isoformat(),
                "tool_name": tool_name,
                "tool_args": tool_args
            }

            logger.info(f"\n" + "-" * 50)
            logger.info(f"[工具调用] {tool_name}")
            logger.info(f"-" * 50)
            logger.info(f"参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}")

            # 调用原始方法
            nl_output, raw_output = original_execute_tool_call(self, tool_call)

            # 记录返回结果
            record["nl_output"] = nl_output
            record["raw_output_type"] = type(raw_output).__name__ if raw_output else None

            logger.info(f"\n[工具返回] {tool_name}")
            logger.info(f"自然语言输出:\n{nl_output}")
            if raw_output:
                logger.debug(f"原始输出: {raw_output}")

            tool_call_records.append(record)
            return nl_output, raw_output

        # 应用补丁
        ToolNodeAgent._execute_tool_call = patched_execute_tool_call

        try:
            # ========== 5. 生成章节内容 ==========
            logger.info(f"\n[步骤5] 生成章节内容")

            generator = GenericChapterGenerator(
                llm=qwen_model,
                chapter_config=chapter_config,
                data=raw_data,
                sale_id=sale_config.get("job_id"),
                sale_name=sale_config.get("sale_name"),
                progress_report_dir=LOG_DIR
            )

            logger.info("开始生成...")
            result = await generator.run_async()

            # ========== 6. 记录分析输出 ==========
            logger.info(f"\n" + "=" * 60)
            logger.info(f"[模型分析输出]")
            logger.info(f"=" * 60)
            logger.info(f"章节ID: {result.chapter_id}")
            logger.info(f"章节名称: {result.chapter_name}")
            logger.info(f"生成状态: {'成功' if result.success else '失败'}")

            if result.success:
                logger.info(f"内容长度: {len(result.content)} 字符")
                logger.info(f"\n完整内容:\n{result.content}")
            else:
                logger.error(f"错误信息: {result.error_message}")

            # ========== 7. 打印工具调用汇总 ==========
            logger.info(f"\n" + "=" * 60)
            logger.info(f"[工具调用汇总]")
            logger.info(f"=" * 60)
            logger.info(f"总调用次数: {len(tool_call_records)}")

            for i, record in enumerate(tool_call_records, 1):
                logger.info(f"\n[{i}] {record['tool_name']}")
                logger.info(f"    调用时间: {record['timestamp']}")
                logger.info(f"    输出长度: {len(record['nl_output'])} 字符")

            # ========== 8. 保存结果摘要 ==========
            summary = {
                "test_info": {
                    "task_id": task_id,
                    "chapter_id": chapter_id,
                    "job_id": job_id,
                    "time": time,
                    "sale_name": sale_config.get("sale_name"),
                    "test_time": timestamp
                },
                "input_data_summary": data_summary if isinstance(raw_data, dict) else str(raw_data)[:200],
                "tool_calls": [
                    {
                        "tool_name": r["tool_name"],
                        "timestamp": r["timestamp"],
                        "output_length": len(r["nl_output"])
                    }
                    for r in tool_call_records
                ],
                "result": {
                    "success": result.success,
                    "content_length": len(result.content) if result.content else 0,
                    "error_message": result.error_message
                }
            }

            summary_file = LOG_DIR / f"chapter{chapter_id}_{job_id}_{timestamp}_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)

            logger.info(f"\n日志文件: {log_file}")
            logger.info(f"摘要文件: {summary_file}")

            print(f"\n测试完成！")
            print(f"日志文件: {log_file}")
            print(f"摘要文件: {summary_file}")

            return result

        finally:
            # 恢复原始方法
            ToolNodeAgent._execute_tool_call = original_execute_tool_call

            # 关闭日志处理器
            for handler in logger.handlers:
                handler.close()
            logger.handlers = []

    def _print_tool_stats(self):
        """打印工具调用统计"""
        print("\n" + "=" * 60)
        print(" 工具调用统计")
        print("=" * 60)

        if not self.tool_calls_log:
            print("  无工具调用记录")
            return

        print(f"  总调用次数: {len(self.tool_calls_log)}")

        # 统计每个工具的调用次数
        tool_counts = {}
        for call in self.tool_calls_log:
            name = call["tool_name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1

        print("\n  各工具调用次数:")
        for name, count in tool_counts.items():
            print(f"    - {name}: {count} 次")

        # 打印详细日志
        if self.tool_results_log:
            print("\n  工具返回结果摘要:")
            for i, result in enumerate(self.tool_results_log):
                print(f"\n  [{i+1}] {result['tool_name']}")
                output = result['nl_output']
                if len(output) > 200:
                    print(f"      输出预览: {output[:200]}...")
                else:
                    print(f"      输出: {output}")


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "#" * 70)
    print("# DynamicReportGenerator 单元测试")
    print("#" * 70)

    tester = TestDynamicReportGenerator()

    # 测试1: 列出可用任务
    await tester.test_task_list()

    # 测试2: 加载任务配置
    await tester.test_task_loading()

    # 测试6: 加载销售名单
    await tester.test_load_sales_list()

    # 测试5: 使用模拟数据的快速测试
    await tester.test_with_mock_data()

    print("\n" + "#" * 70)
    print("# 所有测试完成!")
    print("#" * 70)


async def run_full_test():
    """运行完整报告生成测试"""
    print("\n" + "#" * 70)
    print("# DynamicReportGenerator 完整报告生成测试")
    print("#" * 70)

    tester = TestDynamicReportGenerator()

    # 运行完整测试（使用模拟数据）
    await tester.test_full_report_generation()

    print("\n" + "#" * 70)
    print("# 测试完成!")
    print("#" * 70)


async def run_real_sale_test(job_id: str = "00165", time: str = "202601"):
    """运行真实销售数据测试"""
    print("\n" + "#" * 70)
    print("# DynamicReportGenerator 真实销售数据测试")
    print("#" * 70)

    tester = TestDynamicReportGenerator()

    # 使用真实销售数据测试
    await tester.test_with_real_sale(job_id=job_id, time=time)

    print("\n" + "#" * 70)
    print("# 测试完成!")
    print("#" * 70)


async def run_batch_real_test(job_ids: List[str] = None, time: str = "202601", max_count: int = 3):
    """运行批量真实销售数据测试"""
    print("\n" + "#" * 70)
    print("# DynamicReportGenerator 批量真实销售数据测试")
    print("#" * 70)

    tester = TestDynamicReportGenerator()

    # 批量测试
    await tester.test_batch_with_real_sales(job_ids=job_ids, time=time, max_count=max_count)

    print("\n" + "#" * 70)
    print("# 测试完成!")
    print("#" * 70)


async def run_chapter_test(
    chapter_id: int = 2,
    job_id: str = "00165",
    time: str = "202601"
):
    """
    运行单章节测试（带详细日志记录）

    Args:
        chapter_id: 章节ID，默认为2
        job_id: 销售工号
        time: 数据时间（格式：YYYYMM）
    """
    print("\n" + "#" * 70)
    print(f"# 第二章生成测试（带详细日志记录）")
    print(f"# 章节: {chapter_id}, 工号: {job_id}, 时间: {time}")
    print("#" * 70)

    tester = TestDynamicReportGenerator()

    # 运行单章节测试
    result = await tester.test_single_chapter_with_logging(
        chapter_id=chapter_id,
        job_id=job_id,
        time=time
    )

    print("\n" + "#" * 70)
    print("# 测试完成!")
    print("#" * 70)

    return result


if __name__ == "__main__":
    import sys

    def print_usage():
        print("用法:")
        print("  python test_dynamic_report_generator.py              # 运行基础测试")
        print("  python test_dynamic_report_generator.py --full       # 运行完整报告生成测试（模拟数据）")
        print("  python test_dynamic_report_generator.py --real       # 运行真实销售数据测试")
        print("  python test_dynamic_report_generator.py --real 00165 # 指定销售工号测试")
        print("  python test_dynamic_report_generator.py --batch      # 批量真实销售数据测试")
        print("  python test_dynamic_report_generator.py --batch 00165,00812 # 批量指定销售工号测试")
        print("")
        print("  # 单章节测试（带详细日志记录）")
        print("  python test_dynamic_report_generator.py --chapter    # 测试第二章（默认工号00165）")
        print("  python test_dynamic_report_generator.py --chapter 2 00165  # 指定章节和工号")
        print("  python test_dynamic_report_generator.py --chapter 2 00165 202601  # 指定章节、工号、时间")

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--full":
            asyncio.run(run_full_test())

        elif arg == "--real":
            job_id = sys.argv[2] if len(sys.argv) > 2 else "00165"
            time = sys.argv[3] if len(sys.argv) > 3 else "202601"
            asyncio.run(run_real_sale_test(job_id=job_id, time=time))

        elif arg == "--batch":
            job_ids = None
            if len(sys.argv) > 2:
                job_ids = sys.argv[2].split(",")
            asyncio.run(run_batch_real_test(job_ids=job_ids))

        elif arg == "--chapter":
            chapter_id = int(sys.argv[2]) if len(sys.argv) > 2 else 2
            job_id = sys.argv[3] if len(sys.argv) > 3 else "00165"
            time = sys.argv[4] if len(sys.argv) > 4 else "202601"
            asyncio.run(run_chapter_test(chapter_id=chapter_id, job_id=job_id, time=time))

        elif arg == "--help" or arg == "-h":
            print_usage()

        else:
            print(f"未知参数: {arg}")
            print_usage()

    else:
        # 运行所有测试（默认）
        asyncio.run(run_all_tests())