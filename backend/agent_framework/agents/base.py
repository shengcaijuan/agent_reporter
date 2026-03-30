"""
Base agent module - Abstract base class for agents.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, List
from pathlib import Path

from ..models import BaseModel
from ..tools import BaseTool


class BaseAgent(ABC):
    """
    Abstract base class for agents.

    All agent implementations should inherit from this class
    and implement both sync and async run methods.
    """

    def __init__(
        self,
        llm: BaseModel,
        tools: List[BaseTool],
        sale_id: Optional[str] = None,
        sale_name: Optional[str] = None,
        progress_report_dir: Optional[Path] = None
    ):
        """
        Initialize the agent.

        Args:
            llm: The chat model to use
            tools: List of tools available to the agent
            sale_id: Optional sales ID for logging
            sale_name: Optional sales name for logging
            progress_report_dir: Optional directory for progress reports
        """
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        self.tool_list = tools
        self.sale_id = sale_id
        self.sale_name = sale_name
        self.progress_report_dir = progress_report_dir

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """
        Synchronously run the agent.

        Returns:
            Agent execution result
        """
        pass

    @abstractmethod
    async def arun(self, *args, **kwargs) -> Any:
        """
        Asynchronously run the agent.

        Returns:
            Agent execution result
        """
        pass