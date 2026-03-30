"""
Tool agent module - Agent that executes tool function calls.
"""
import json
from typing import Tuple, Optional, Any, List
from pathlib import Path
from pydantic import BaseModel as PydanticModel

from .base import BaseAgent
from ..models import BaseModel
from ..tools import BaseTool
from ..messages import SystemMessage, UserMessage


class ToolAgent(BaseAgent):
    """
    Tool calling agent.

    Executes the tool call loop: LLM -> Tool Call -> Tool Execution -> Output

    This agent:
    1. Sends data to LLM with available tools
    2. LLM decides which tool to call with what arguments
    3. Agent executes the tool
    4. Returns natural language output and raw result
    """

    def __init__(
        self,
        llm: BaseModel,
        tools: List[BaseTool],
        data: str,
        system_prompt: Optional[str] = None,
        sale_id: Optional[str] = None,
        sale_name: Optional[str] = None,
        progress_report_dir: Optional[Path] = None
    ):
        """
        Initialize the tool agent.

        Args:
            llm: The chat model to use
            tools: List of tools available to the agent
            data: Input data to analyze (will be passed to LLM)
            system_prompt: Optional custom system prompt
            sale_id: Optional sales ID for logging
            sale_name: Optional sales name for logging
            progress_report_dir: Optional directory for progress reports
        """
        super().__init__(
            llm=llm,
            tools=tools,
            sale_id=sale_id,
            sale_name=sale_name,
            progress_report_dir=progress_report_dir
        )
        self.data = data
        self.system_prompt = system_prompt or self._default_system_prompt()
    
    def _default_system_prompt(self) -> str:
        """Return the default system prompt."""

        sys_prompt = """
        你是负责调用工具函数的数据参数解析器。
        请根据用户提供的数据输入，严格按照工具函数的参数规范，从输入中提取调用参数。
        
        注：必须调用工具函数。
        数据指标口径对齐：同期数即为上期值，实际值为当期值。
        """

        return sys_prompt

    def _execute_tool_call(
        self,
        tool_call
    ) -> Tuple[str, Optional[PydanticModel]]:
        """
        Execute a tool call.

        Args:
            tool_call: ToolCall object from LLM response

        Returns:
            Tuple of (natural_language_output, raw_output)
        """
        tool_name = tool_call.function_name
        tool_args = json.loads(tool_call.arguments)

        tool = self.tools.get(tool_name)
        if tool is None:
            error_msg = f"未找到名称为 '{tool_name}' 的工具函数"
            self._log_error(error_msg)
            return error_msg, None

        try:
            self._log_tool_call(tool_name, tool_args)
            raw_output = tool.run(**tool_args)
            nl_output = self._format_output(raw_output)
            self._log_output(tool_name, raw_output, nl_output)
            return nl_output, raw_output
        except Exception as e:
            error_msg = f"工具执行错误: {str(e)}"
            self._log_error(error_msg)
            return error_msg, None

    def _format_output(self, output: Any) -> str:
        """
        Format the tool output to natural language.

        Args:
            output: Raw output from tool execution

        Returns:
            Natural language description
        """
        if isinstance(output, PydanticModel):
            # If output has a to_natural_language method, use it
            if hasattr(output, 'to_natural_language'):
                return output.to_natural_language()
            # Otherwise, convert to string
            return str(output)
        return str(output)

    def _log_tool_call(self, tool_name: str, tool_args: dict):
        """Log tool call information."""
        # Placeholder for logging - can be overridden
        pass

    def _log_output(self, tool_name: str, raw_output: Any, nl_output: str):
        """Log tool output information."""
        # Placeholder for logging - can be overridden
        pass

    def _log_error(self, error_msg: str):
        """Log error information."""
        # Placeholder for logging - can be overridden
        pass

    def run(self) -> Tuple[str, Optional[PydanticModel]]:
        """
        Synchronously run the tool agent.

        Returns:
            Tuple of (natural_language_output, raw_output)
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            UserMessage(content=f"需要分析的数据为:\n{self.data}")
        ]

        bound_model = self.llm.bind_tools(self.tool_list)
        response = bound_model.invoke(messages)

        if not response.tool_calls:
            return "LLM未能生成有效的工具调用", None

        return self._execute_tool_call(response.tool_calls[0])

    async def arun(self) -> Tuple[str, Optional[PydanticModel]]:
        """
        Asynchronously run the tool agent.

        Returns:
            Tuple of (natural_language_output, raw_output)
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            UserMessage(content=f"需要分析的数据为:\n{self.data}")
        ]

        bound_model = self.llm.bind_tools(self.tool_list)
        response = await bound_model.ainvoke(messages)

        if not response.tool_calls:
            return "LLM未能生成有效的工具调用", None

        return self._execute_tool_call(response.tool_calls[0])