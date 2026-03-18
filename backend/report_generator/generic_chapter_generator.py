"""
通用章节生成器 - 配置驱动的章节生成

支持三种章节类型：
- simple: 简单章节，直接LLM生成
- with_tools: 带工具章节，先执行工具再LLM生成
- summary: 总结章节，需要前面的章节内容作为输入
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from runtime.config import ChapterRuntime
from model import AnaModel
from tools.agent import ToolFunctionAgent, create_tool_agents
from logger import get_sales_logger
from agent_framework.messages import HumanMessage

class ChapterResult(BaseModel):
    """章节生成结果"""
    chapter_id: int = Field(default=None, description="章节id")
    chapter_name: str = Field(default=None, description="章节名")
    content: str = Field(default=None, description="markdown 格式分析内容")
    tool_output: Optional[str] = Field(default=None, description="工具函数输出")
    success: bool = Field(default=None, description="是否生成成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class GenericChapterGenerator:
    """
    通用章节生成器 - 支持配置驱动的章节生成

    核心功能：
    1. 根据章节类型选择生成策略
    2. 支持动态工具配置执行
    3. 支持总结章节（依赖前面章节内容）
    """

    def __init__(
        self,
        llm: AnaModel,
        chapter_config: ChapterRuntime,
        data: Optional[Dict[str, Any]] = None,
        sale_id: str = "",
        sale_name: str = "",
        progress_report_dir: Optional[Path] = None,
        previous_chapters: Optional[Dict[int, str]] = None
    ):
        self.llm = llm
        self.chapter_config = chapter_config
        self.data = data or {}
        self.sale_id = sale_id
        self.sale_name = sale_name
        self.progress_report_dir = progress_report_dir
        self.previous_chapters = previous_chapters or {}

        # 初始化日志
        self.logger = get_sales_logger(
            sale_id=sale_id,
            progress_report_dir=progress_report_dir or Path("."),
            log_file_name=f"chapter{chapter_config.chapter_id}_generation.log"
        )

        # 初始化工具代理（如果需要）
        self.tool_agents: List[ToolFunctionAgent] = []
        if chapter_config.has_tools and chapter_config.tool_configs:
            self.tool_agents = create_tool_agents(
                tool_agent_config=chapter_config.tool_configs,
                sale_id=sale_id,
                sale_name=sale_name,
                progress_report_dir=progress_report_dir
            )

    async def run_async(self) -> ChapterResult:
        """
        执行章节生成

        Returns:
            ChapterResult: 章节生成结果
        """
        try:
            self.logger.info(f"开始生成章节 {self.chapter_config.chapter_id}: {self.chapter_config.chapter_name}")

            # 根据章节类型选择生成策略
            if self.chapter_config.chapter_type == "summary":
                content = await self._generate_summary_chapter()
            elif self.chapter_config.chapter_type == "with_tools":
                content = await self._generate_with_tools_chapter()
            else:  # simple
                content = await self._generate_simple_chapter()

            self.logger.info(f"章节 {self.chapter_config.chapter_id} 生成完成，内容长度: {len(content)}")

            # 记录章节生成的 md 内容
            self.logger.info(f"\n{'='*60}\n"
                           f"章节 {self.chapter_config.chapter_id} [{self.chapter_config.chapter_name}] MD内容:\n"
                           f"{'='*60}\n"
                           f"{content}\n"
                           f"{'='*60}\n")

            return ChapterResult(
                chapter_id=self.chapter_config.chapter_id,
                chapter_name=self.chapter_config.chapter_name,
                content=content,
                success=True
            )

        except Exception as e:
            self.logger.error(f"章节 {self.chapter_config.chapter_id} 生成失败: {str(e)}")
            return ChapterResult(
                chapter_id=self.chapter_config.chapter_id,
                chapter_name=self.chapter_config.chapter_name,
                content="",
                success=False,
                error_message=str(e)
            )

    async def _generate_simple_chapter(self) -> str:
        """生成简单章节（无工具）"""
        prompt = self._build_prompt()
        messages = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages)
        return response.content

    async def _generate_with_tools_chapter(self) -> str:
        """生成带工具的章节"""
        # 1. 执行工具链
        tool_outputs = await self._execute_tools()

        # 2. 组装工具输出
        combined_tool_output = "\n\n".join(tool_outputs)

        # 3. 基于工具输出生成章节内容
        prompt = self._build_prompt_with_tools(combined_tool_output)
        messages = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages)

        return response.content

    async def _generate_summary_chapter(self) -> str:
        """生成总结章节"""
        # 获取需要汇总的章节内容
        summarize_contents = []
        for ch_id in self.chapter_config.summarize_chapters:
            if ch_id in self.previous_chapters:
                summarize_contents.append(
                    f"## 第{ch_id}章\n\n{self.previous_chapters[ch_id]}"
                )

        previous_content = "\n\n---\n\n".join(summarize_contents)

        # 构建提示词
        prompt = self._build_summary_prompt(previous_content)
        messages = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages)

        return response.content

    async def _execute_tools(self) -> List[str]:
        """执行所有工具并返回输出列表"""
        outputs = []

        if not self.tool_agents:
            self.logger.warning("没有工具代理可执行")
            return outputs

        self.logger.info(f"开始执行 {len(self.tool_agents)} 个工具")

        # 并发执行所有工具
        results = await asyncio.gather(
            *[agent.run_async(json.dumps(self.data, ensure_ascii=False)) for agent in self.tool_agents],
            return_exceptions=True
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"工具 {i+1} 执行失败: {str(result)}")
                outputs.append(f"工具执行出错: {str(result)}")
            else:
                nl_output, _ = result
                outputs.append(nl_output)
                self.logger.info(f"工具 {i+1} 执行完成，输出长度: {len(nl_output)}")

        return outputs

    def _build_prompt(self) -> str:
        """构建基础提示词"""

        guideline = self.chapter_config.guideline

        prompt = f"""
        你是一位专业的销售数据分析专家。

        # 分析任务
        请根据以下数据完成【{self.chapter_config.chapter_name}】的分析。

        # 数据
        ```json
        {self._format_data()}
        ```

        # 分析要求
        {guideline}

        # 输出要求
        请输出完整的分析报告，使用Markdown格式。
        """

        return prompt

    def _build_prompt_with_tools(self, tool_output: str) -> str:
        """构建包含工具输出的提示词"""
        guideline = self.chapter_config.guideline

        prompt = f"""
        你是一位专业的销售数据分析专家。

        # 分析任务
        请根据以下工具分析结果和数据完成【{self.chapter_config.chapter_name}】的分析。

        # 工具分析结果
        {tool_output}

        # 原始数据
        ```json
        {self._format_data()}
        ```

        # 分析要求
        {guideline}

        # 输出要求
        请输出完整的分析报告，使用Markdown格式。工具分析结果已经提供了关键的量化分析，请在报告中充分引用这些分析结论。
        """

        return prompt

    def _build_summary_prompt(self, previous_content: str) -> str:
        """构建总结章节提示词"""
        guideline = self.chapter_config.guideline

        prompt = f"""
        你是一位专业的销售数据分析专家。

        # 分析任务
        请基于前面章节的分析内容，完成【{self.chapter_config.chapter_name}】的综合分析。

        # 前面章节内容:
        {previous_content}

        # 分析要求:
        {guideline}
        """

        return prompt

    def _format_data(self) -> str:
        """格式化数据为字符串"""
        try:
            return json.dumps(self.data, ensure_ascii=False, indent=2)
        except Exception:
            return str(self.data)


if __name__ == "__main__":
    # 测试用例
    from runtime.task_runtime import load_task_runtime
    from model import create_model

    async def test_generator():
        # 1. 加载任务配置
        print("=" * 50)
        print("加载任务配置...")
        runtime = load_task_runtime("mashangzhu")
        print(f"任务名称: {runtime.task_name}")
        print(f"章节数量: {runtime.chapter_count}")

        # 2. 创建模型实例
        print("\n" + "=" * 50)
        print("创建模型实例...")
        llm = create_model(model_type="cloud")

        # 3. 准备测试数据
        test_data = {
            "sales_person": {
                "name": "测试销售员",
                "id": "TEST001"
            },
            "performance": {
                "total_score": 85,
                "rank": 15,
                "items": [
                    {"name": "销售额", "score": 90, "target": 100},
                    {"name": "客户开发", "score": 80, "target": 100}
                ]
            }
        }

        # 4. 测试简单章节生成 (第一章)
        print("\n" + "=" * 50)
        print("测试第一章 (simple 类型)...")
        chapter1 = runtime.get_chapter(1)
        print(f"章节名称: {chapter1.chapter_name}")
        print(f"章节类型: {chapter1.chapter_type}")

        generator1 = GenericChapterGenerator(
            llm=llm,
            chapter_config=chapter1,
            data=test_data,
            sale_id="TEST001",
            sale_name="测试销售员"
        )

        result1 = await generator1.run_async()
        print(f"\n生成结果:")
        print(f"  成功: {result1.success}")
        if result1.success:
            print(f"  内容长度: {len(result1.content)} 字符")
            print(f"  内容预览:\n{result1.content[:500]}...")
        else:
            print(f"  错误: {result1.error_message}")

        # 5. 测试带工具章节生成 (第二章)
        print("\n" + "=" * 50)
        print("测试第二章 (with_tools 类型)...")
        chapter2 = runtime.get_chapter(2)
        print(f"章节名称: {chapter2.chapter_name}")
        print(f"章节类型: {chapter2.chapter_type}")
        print(f"工具配置数量: {len(chapter2.tool_configs)}")

        # 6. 测试总结章节生成 (第六章)
        print("\n" + "=" * 50)
        print("测试第六章 (summary 类型)...")
        chapter6 = runtime.get_chapter(6)
        print(f"章节名称: {chapter6.chapter_name}")
        print(f"章节类型: {chapter6.chapter_type}")
        print(f"汇总章节: {chapter6.summarize_chapters}")

        # 模拟前面章节的内容
        previous_chapters = {
            1: "## 第一章 薪资绩效分析\n\n测试内容...",
            2: "## 第二章 销售势头分析\n\n测试内容...",
            3: "## 第三章 毛利与产品结构分析\n\n测试内容...",
            4: "## 第四章 费用与应收账款风险分析\n\n测试内容...",
            5: "## 第五章 销售行为分析\n\n测试内容..."
        }

        generator6 = GenericChapterGenerator(
            llm=llm,
            chapter_config=chapter6,
            data=test_data,
            sale_id="TEST001",
            sale_name="测试销售员",
            previous_chapters=previous_chapters
        )

        result6 = await generator6.run_async()
        print(f"\n生成结果:")
        print(f"  成功: {result6.success}")
        if result6.success:
            print(f"  内容长度: {len(result6.content)} 字符")
            print(f"  内容预览:\n{result6.content[:500]}...")
        else:
            print(f"  错误: {result6.error_message}")

        print("\n" + "=" * 50)
        print("测试完成!")

    asyncio.run(test_generator())