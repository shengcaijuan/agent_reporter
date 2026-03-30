"""
Tool decorator module - Decorator for creating tools from functions.
"""
from typing import get_type_hints
from pydantic import Field, create_model
from .base import BaseTool


def tool(name: str, description: str):
    """
    Decorator to convert a function into a BaseTool.

    Automatically creates a Pydantic model from the function's type hints
    and wraps the function as a tool that can be called by LLMs.

    Args:
        name: The name of the tool (used by LLM to identify the tool)
        description: A description of what the tool does (helps LLM understand when to use)

    Returns:
        A decorator that converts the function to a BaseTool

    Example:
        @tool(name="add", description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b

        # The decorated function is now a BaseTool instance
        result = add.run(a=1, b=2)  # Returns 3
    """
    def decorator(func):
        # Extract type hints from the function signature
        # e.g., def add(a: int, b: int) -> class AddArgs(BaseModel): a: int, b: int
        type_hints = get_type_hints(func)

        # Build fields for the Pydantic model
        fields = {
            k: (v, Field(..., description=f"Parameter {k}"))
            for k, v in type_hints.items()
            if k != "return"
        }

        # Dynamically create the argument schema model
        ArgSchema = create_model(f"{name}Args", **fields)

        # Return the constructed BaseTool instance
        return BaseTool(
            name=name,
            description=description,
            args_schema=ArgSchema,
            func=func
        )

    return decorator