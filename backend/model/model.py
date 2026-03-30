"""
模型配置模块 - 使用 agent_framework
配置通过 .env 文件管理
"""

# 从 agent_framework 导入
from agent_framework.models import (
    QwenModel, create_model, AnaModel,
    qwen_model
)

# 导出类型和实例
__all__ = [
    "QwenModel",
    "create_model",
    "AnaModel",
    "qwen_model"
]


if __name__ == "__main__":
    print("=" * 50)
    print(f"Qwen_model类型: {type(qwen_model).__name__}")
    print(f"Qwen_model配置: {qwen_model}")
    response = qwen_model.invoke([{"role": "user", "content": "你好,你是谁"}])
    print(response.content)
