"""
健康检查 API
"""
from datetime import datetime
from fastapi import APIRouter

from app.schemas.common import ResponseBase

router = APIRouter(tags=["健康检查"])


@router.get("/health", response_model=ResponseBase)
async def health_check():
    """健康检查"""
    return ResponseBase(
        success=True,
        message="服务正常运行",
        data={
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    )