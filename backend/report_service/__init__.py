# report_service/__init__.py
"""
报告服务模块

提供统一的报告生成接口
"""

from .report_service import (
    ReportService,
    generate_report_for_sale
)

__all__ = [
    "ReportService",
    "generate_report_for_sale"
]