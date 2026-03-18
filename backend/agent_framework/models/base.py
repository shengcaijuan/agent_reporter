"""
Base model module - Abstract base class for chat models
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence
from ..messages import AIMessage, BaseMessage
from ..tools import BaseTool


class BoundModel:
    """
    Bound model that has tools pre-attached.
    Allows calling invoke/ainvoke without passing tools each time.
    """

    def __init__(self, model: "BaseModel", tools: List[BaseTool]):
        self._model = model
        self._tools = tools

    def invoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        """Sync invoke with bound tools"""
        return self._model.invoke(messages, tools=self._tools)

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        """Async invoke with bound tools"""
        return await self._model.ainvoke(messages, tools=self._tools)


class BaseModel(ABC):
    """
    Abstract base class for LLM models.

    All LLM implementations should inherit from this class
    and implement both sync and async invoke methods.
    """

    @abstractmethod
    def invoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
    ) -> AIMessage:
        """
        Synchronously invoke the model.

        Args:
            messages: List of messages in the conversation
            tools: Optional list of tools the model can call

        Returns:
            AIMessage with the model's response
        """
        pass

    @abstractmethod
    async def ainvoke(
        self,
        messages: Sequence[BaseMessage],
        tools: Optional[List[BaseTool]] = None,
    ) -> AIMessage:
        """
        Asynchronously invoke the model.

        Args:
            messages: List of messages in the conversation
            tools: Optional list of tools the model can call

        Returns:
            AIMessage with the model's response
        """
        pass

    def bind_tools(self, tools: List[BaseTool]) -> BoundModel:
        """
        Bind tools to the model, returning a BoundModel.

        The BoundModel can be used to invoke without passing tools each time.

        Args:
            tools: List of tools to bind

        Returns:
            BoundModel with tools pre-attached
        """
        return BoundModel(model=self, tools=tools)