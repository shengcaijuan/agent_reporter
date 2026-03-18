"""
API 路由汇总
"""
from fastapi import APIRouter

from app.api.endpoints import health, auth, tasks, reports, model_config, templates

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(tasks.router)
api_router.include_router(reports.router)
api_router.include_router(model_config.router)
api_router.include_router(templates.router)