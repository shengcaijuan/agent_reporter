"""
后端日志配置模块

提供统一的日志配置，支持：
- 应用日志（API 请求、错误等）
- 业务日志（报告生成、任务执行等）
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)


class LoggerConfig:
    """日志配置"""

    # 日志格式
    DEFAULT_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s"
    SIMPLE_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    # 日志级别
    DEFAULT_LEVEL = logging.INFO

    @classmethod
    def get_formatter(cls, fmt: str = None) -> logging.Formatter:
        """获取日志格式化器"""
        return logging.Formatter(
            fmt or cls.DEFAULT_FORMAT,
            datefmt=cls.DATE_FORMAT
        )


def setup_logger(
    name: str,
    level: int = None,
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    设置并返回 logger

    Args:
        name: logger 名称
        level: 日志级别
        log_file: 日志文件名（相对于 log 目录）
        console: 是否输出到控制台

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level or LoggerConfig.DEFAULT_LEVEL)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 控制台输出
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level or LoggerConfig.DEFAULT_LEVEL)
        console_handler.setFormatter(LoggerConfig.get_formatter(LoggerConfig.SIMPLE_FORMAT))
        logger.addHandler(console_handler)

    # 文件输出
    if log_file:
        file_path = LOG_DIR / log_file
        file_handler = logging.FileHandler(
            file_path,
            mode="a",
            encoding="utf-8"
        )
        file_handler.setLevel(level or LoggerConfig.DEFAULT_LEVEL)
        file_handler.setFormatter(LoggerConfig.get_formatter())
        logger.addHandler(file_handler)

    return logger


def get_app_logger() -> logging.Logger:
    """获取应用日志记录器"""
    return setup_logger(
        "app",
        log_file="app.log",
        console=True
    )


def get_api_logger() -> logging.Logger:
    """获取 API 日志记录器"""
    return setup_logger(
        "api",
        log_file="api.log",
        console=True
    )


def get_report_logger() -> logging.Logger:
    """获取报告生成日志记录器"""
    return setup_logger(
        "report",
        log_file="report.log",
        console=True
    )


def get_task_logger() -> logging.Logger:
    """获取任务执行日志记录器"""
    return setup_logger(
        "task",
        log_file="task.log",
        console=True
    )


# 预创建常用 logger
app_logger = get_app_logger()
api_logger = get_api_logger()
report_logger = get_report_logger()
task_logger = get_task_logger()


class RequestLoggerMiddleware:
    """请求日志中间件（用于 FastAPI）"""

    def __init__(self, app):
        self.app = app
        self.logger = get_api_logger()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            method = scope.get("method", "")
            path = scope.get("path", "")
            client = scope.get("client", ("", 0))[0]

            # 记录请求
            self.logger.info(f"Request: {method} {path} from {client}")

            # 包装 send 以记录响应
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    status = message.get("status", 0)
                    self.logger.info(f"Response: {method} {path} - {status}")
                await send(message)

            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)