"""
Base tool module - Base class for tools and utility functions.
"""
from typing import Any, Callable, Type, Dict, Optional
from pydantic import BaseModel, ConfigDict


class BaseTool(BaseModel):
    """
    Base class for all tools.

    Tools are functions that can be called by LLMs with structured parameters.
    Each tool has a name, description, argument schema, and the function to execute.

    Example:
        class AddArgs(BaseModel):
            a: int
            b: int

        def add_func(a: int, b: int) -> int:
            return a + b

        tool = BaseTool(
            name="add",
            description="Add two numbers",
            args_schema=AddArgs,
            func=add_func
        )

        # Or use from_function:
        tool = BaseTool.from_function(
            func=add_func,
            name="add",
            description="Add two numbers",
            args_schema=AddArgs
        )
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    args_schema: Type[BaseModel]
    func: Callable[..., Any]

    def run(self, **kwargs) -> Any:
        """
        Execute the tool with the given arguments.

        Args:
            **kwargs: Arguments matching the args_schema

        Returns:
            Tool execution result
        """
        return self.func(**kwargs)

    def invoke(self, input: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        """
        Invoke the tool (langchain-compatible API).

        Args:
            input: Dict of arguments (langchain style)
            **kwargs: Direct keyword arguments

        Returns:
            Tool execution result
        """
        if input is not None:
            return self.func(**input)
        return self.run(**kwargs)

    def to_openai_schema(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function calling schema.

        Returns:
            Dict with OpenAI-compatible tool definition
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema()
            }
        }

    @classmethod
    def from_function(
        cls,
        func: Callable[..., Any],
        name: str,
        description: str,
        args_schema: Type[BaseModel]
    ) -> "BaseTool":
        """
        Create a BaseTool from a function.

        This is the preferred way to create tools from existing functions,
        especially when wrapping attribution analysis functions.

        Args:
            func: The function to wrap
            name: Tool name (used by LLM to identify the tool)
            description: Tool description (helps LLM understand when to use)
            args_schema: Pydantic model defining the arguments schema

        Returns:
            BaseTool instance

        Example:
            def analyze_sales(region: str, period: str) -> dict:
                return {"region": region, "period": period}

            class SalesArgs(BaseModel):
                region: str
                period: str

            tool = BaseTool.from_function(
                func=analyze_sales,
                name="sales_analyzer",
                description="Analyze sales data for a region and period",
                args_schema=SalesArgs
            )
        """
        return cls(
            name=name,
            description=description,
            args_schema=args_schema,
            func=func
        )


# StructuredTool 是 BaseTool 的别名，兼容 langchain 的命名
StructuredTool = BaseTool

