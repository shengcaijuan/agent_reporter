# ToolNodeLLM.py
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

# 使用 agent_framework 替换 langchain
from agent_framework.messages import SystemMessage, HumanMessage
from agent_framework.tools import StructuredTool
from agent_framework.models import QwenModel

from tools.attribution.formatter import format_attr_output
from logger import get_sales_logger
from model import qwen_model


def format_attribution_output(raw_function_output) -> str:
    """
    将AttrOutput转换为自然语言描述

    :param raw_function_output: 归因分析输出
    :return: 自然语言描述字符串
    """
    return format_attr_output(raw_function_output)


class ToolNodeAgent:
    def __init__(
            self,
            llm: QwenModel,
            tools: List[StructuredTool],
            data: str,
            sale_id: Optional[str] = None,
            sale_name: Optional[str] = None,
            progress_report_dir: Optional[Path] = None
    ):
        """
        初始化数据分析Agent

        :param llm: 模型
        :param tools: 工具函数列表
        :param data: 分析的数据
        :param sale_id: 销售工号（可选，用于创建专属日志）
        :param sale_name: 销售姓名（可选，用于日志记录）
        :param progress_report_dir: 报告目录（可选，用于存放专属日志）
        """
        self.llm = llm.bind_tools(tools)
        self.tools = {tool.name: tool for tool in tools}
        self.data = data
        self.user_input = f"需要分析的数据为: \n{self.data}"

        # 销售标识信息
        self.sale_id = sale_id
        self.sale_name = sale_name
        self.progress_report_dir = progress_report_dir

        # 创建专属logger（使用共享函数）
        self.logger_fc = get_sales_logger(
            sale_id=sale_id or "unknown",
            progress_report_dir=progress_report_dir or Path(".")
        )

    def _execute_tool_call(self, tool_call: dict) -> tuple[str, BaseModel]:
        """
        执行工具调用

        :param tool_call: 工具调用信息
        :return: (自然语言输出, 原始输出)
        """
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        tool = self.tools.get(tool_name)
        if tool is None:
            error_msg = f"未找到名称为 '{tool_name}' 的工具函数。请检查工具定义或LLM返回的工具名称。"
            self.logger_fc.error(error_msg)
            return error_msg, None

        try:
            # 记录 TOOL_CALL
            log_data = {
                "sale_id": self.sale_id,
                "sale_name": self.sale_name,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "timestamp": datetime.now().isoformat()
            }
            self.logger_fc.info(f"[TOOL_CALL] {json.dumps(log_data, ensure_ascii=False)}")

            # 执行工具
            raw_function_output: BaseModel = tool.invoke(tool_args)
            nl_analysis_output = format_attribution_output(raw_function_output)

            # 记录 RAW_OUTPUT（完整记录）
            raw_output_log = {
                "sale_id": self.sale_id,
                "sale_name": self.sale_name,
                "tool_name": tool_name,
                "raw_output": str(raw_function_output),
                "timestamp": datetime.now().isoformat()
            }
            self.logger_fc.info(f"[RAW_OUTPUT] {json.dumps(raw_output_log, ensure_ascii=False)}")

            # 记录 NL_OUTPUT
            nl_output_log = {
                "sale_id": self.sale_id,
                "sale_name": self.sale_name,
                "tool_name": tool_name,
                "nl_output": nl_analysis_output,
                "timestamp": datetime.now().isoformat()
            }
            self.logger_fc.info(f"[NL_OUTPUT] {json.dumps(nl_output_log, ensure_ascii=False)}")

            return nl_analysis_output, raw_function_output

        except Exception as e:
            error_msg = f"Tool execution error: {str(e)}"
            self.logger_fc.error(error_msg)
            return error_msg, None

    def run(self) -> tuple[str, BaseModel | None]:
        """
        运行数据分析助手（同步）

        :return:
            - nl_analysis_output: 自然语言分析输出
            - raw_function_output: 原始工具函数输出
        """
        system_prompt = """
        你是负责调用工具函数的数据参数解析器。
        请根据用户提供的数据输入，严格按照工具函数的参数规范，从输入中提取调用参数。
        注：必须调用工具函数。
        数据指标口径对齐：同期数即为上期值，实际值为当期值。
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=self.user_input)
        ]

        response = self.llm.invoke(messages)
        # 使用 tool_calls_lc 获取兼容格式的工具调用
        tool_calls = response.tool_calls_lc

        self.logger_fc.info(
            f"Tool Function LLM Response:\n{response}\n"
            f"tool_calls:\n{tool_calls}\n"
        )

        if not tool_calls:
            error_msg = "LLM 未能生成有效的工具调用，请检查输入数据或工具定义。"
            self.logger_fc.error(error_msg)
            return error_msg, None

        return self._execute_tool_call(tool_calls[0].model_dump())

    async def async_run(self) -> tuple[str, BaseModel | None]:
        """
        异步运行数据分析助手

        使用线程池执行同步的 LLM 调用和工具调用

        :return:
            - nl_analysis_output: 自然语言分析输出
            - raw_function_output: 原始工具函数输出
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run)


class ToolFunctionLLM:
    def __init__(
            self,
            data: str,
            tools: List[StructuredTool],
            sale_id: Optional[str] = None,
            sale_name: Optional[str] = None,
            progress_report_dir: Optional[Path] = None
    ):
        """
        初始化工具函数LLM

        :param data: 分析数据
        :param tools: 工具列表
        :param sale_id: 销售工号（可选，用于创建专属日志）
        :param sale_name: 销售姓名（可选，用于日志记录）
        :param progress_report_dir: 报告目录（可选，用于存放专属日志）
        """
        self.model = qwen_model
        self.tools = tools
        self.agent = ToolNodeAgent(
            llm=self.model,
            tools=self.tools,
            data=data,
            sale_id=sale_id,
            sale_name=sale_name,
            progress_report_dir=progress_report_dir
        )

    def analysis(self) -> tuple[str, BaseModel | None]:
        """
        同步分析方法

        :return: 自然语言输出和原始分析输出
        """
        return self.agent.run()

    async def async_analysis(self) -> tuple[str, BaseModel | None]:
        """
        异步分析方法

        :return: 自然语言输出和原始分析输出
        """
        return await self.agent.async_run()