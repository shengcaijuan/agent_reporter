"""销售专属日志记录模块

提供统一的销售专属 logger 创建接口，用于记录：
- function_calling.log: 工具调用日志
- fetch_data.log: 数据抓取日志
- 其他销售专属日志

所有销售相关日志都通过此模块创建，确保代码复用和统一管理。
"""
import logging
import warnings
from pathlib import Path
import json
from datetime import datetime


def get_sales_logger(
    sale_id: str,
    progress_report_dir: Path,
    log_file_name: str = "function_calling.log"
) -> logging.Logger:
    """
    获取销售专属的 logger

    相同的 sale_id 会返回同一个 logger 实例（Python logging 单例特性）

    Args:
        sale_id: 销售工号
        progress_report_dir: 报告目录（用于存放日志文件）
        log_file_name: 日志文件名，默认 "function_calling.log"

    Returns:
        Logger 实例

    Example:
        >>> logger = get_sales_logger("04490", Path("Reports/.../progress_report"))
        >>> logger.info("日志内容")
    """
    if not progress_report_dir or not sale_id:
        # 如果缺少参数，返回临时 logger
        temp_logger = logging.getLogger(f"temp_sales_{id(progress_report_dir)}")
        temp_logger.setLevel(logging.INFO)
        if not temp_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
            temp_logger.addHandler(handler)
        return temp_logger

    try:
        # 确保目录存在
        progress_report_dir.mkdir(parents=True, exist_ok=True)

        # 创建 logger（相同 sale_id 返回同一实例）
        logger_name = f"sales_fc_{sale_id}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        # 避免重复添加 handler
        if not logger.handlers:
            log_file = progress_report_dir / log_file_name
            handler = logging.FileHandler(
                log_file,
                mode="a",
                encoding="utf-8"
            )
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    except Exception as e:
        warnings.warn(
            f"创建销售专属 logger 失败: {e}, 使用临时 logger",
            RuntimeWarning
        )
        # 降级：创建临时 logger
        temp_logger = logging.getLogger(f"temp_sales_{sale_id}_{id(e)}")
        temp_logger.setLevel(logging.INFO)
        if not temp_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
            temp_logger.addHandler(handler)
        return temp_logger


def log_raw_data(
    sale_id: str,
    sale_name: str,
    progress_report_dir: Path,
    chapter: int,
    data: str
) -> None:
    """
    记录原始数据抓取日志
    """
    logger = get_sales_logger(sale_id, progress_report_dir, "function_calling.log")

    log_data = {
        "timestamp": datetime.now().isoformat(),
        "sale_id": sale_id,
        "sale_name": sale_name,
        "event_type": "FETCH_RAW_DATA",
        "chapter": chapter,
        "data": data
    }
    logger.info(f"[FETCH_RAW_DATA] {json.dumps(log_data, ensure_ascii=False)}")


def log_processed_data(
    sale_id: str,
    sale_name: str,
    progress_report_dir: Path,
    chapter: int,
    data: str
) -> None:
    """
    记录处理后的数据日志

    Args:
        sale_id: 销售工号
        sale_name: 销售姓名
        progress_report_dir: 报告目录
        chapter: 章节号
        data: 处理后的数据
    """
    logger = get_sales_logger(sale_id, progress_report_dir, "function_calling.log")

    log_data = {
        "timestamp": datetime.now().isoformat(),
        "sale_id": sale_id,
        "sale_name": sale_name,
        "event_type": "PROCESSED_DATA",
        "chapter": chapter,
        "data": data
    }

    logger.info(f"[PROCESSED_DATA] {json.dumps(log_data, ensure_ascii=False)}")
