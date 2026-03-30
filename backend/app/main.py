"""
FastAPI 应用入口
"""
import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from typing import List

from app.core.config import settings
from app.core.logger import app_logger, RequestLoggerMiddleware
from app.api.router import api_router
from app.db.database import init_db


# WebSocket 连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()
    app_logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功")

    # 启动进度推送任务
    asyncio.create_task(progress_broadcaster())

    yield
    # 关闭时的清理工作
    app_logger.info("👋 应用正在关闭...")


async def progress_broadcaster():
    """定时广播进度状态"""
    from app.api.endpoints.reports import _task_status
    while True:
        if _task_status["status"] == "running":
            await manager.broadcast({
                "type": "progress",
                "data": {
                    "task_id": _task_status.get("task_id"),
                    "task_name": _task_status.get("task_name"),
                    "batch_id": _task_status.get("batch_id"),
                    "report_time": _task_status.get("report_time"),
                    "total": _task_status.get("total", 0),
                    "completed": _task_status.get("completed", 0),
                    "failed": _task_status.get("failed", 0),
                    "in_progress": _task_status.get("in_progress", 0),
                    "status": _task_status.get("status"),
                    # 新增：正在处理的销售列表
                    "processing_sales": _task_status.get("processing_sales", []),
                    # 新增：等待处理的销售列表
                    "pending_sales": _task_status.get("pending_sales", [])
                }
            })
        await asyncio.sleep(1)


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="基于 LLM 的销售业绩报告自动生成系统",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加请求日志中间件
    app.add_middleware(RequestLoggerMiddleware)

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        app_logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "服务器内部错误", "detail": str(exc)}
        )

    # 注册路由
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # WebSocket 端点
    @app.websocket("/ws/progress")
    async def websocket_progress(websocket: WebSocket):
        """WebSocket 进度推送端点"""
        await manager.connect(websocket)
        try:
            while True:
                # 等待客户端消息（心跳等）
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)