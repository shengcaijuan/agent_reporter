"""
数据源配置 API
支持全局数据源管理和任务级数据源配置
"""
import os
import json
import time
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from aiohttp import ClientSession, ClientTimeout

from app.core.security import get_current_active_user
from app.db.models import User
from app.schemas.common import DataResponse
from app.schemas.data_source import (
    DataSource, DataSourceConfig, DataSourceTestRequest,
    AuthType
)

router = APIRouter(prefix="/data-sources", tags=["数据源管理"])


def get_tasks_base_path() -> str:
    """获取任务根目录"""
    return os.path.join(os.path.dirname(__file__), "..", "..", "..", "report_tasks")


def get_task_config_path(task_id: str) -> str:
    """获取任务配置文件路径"""
    return os.path.join(get_tasks_base_path(), task_id, "config_files", "task_config.json")


def get_global_data_sources_path() -> str:
    """获取全局数据源配置文件路径"""
    return os.path.join(os.path.dirname(__file__), "..", "..", "..", "config_files", "data_sources.json")


def load_global_data_sources() -> List[Dict[str, Any]]:
    """加载全局数据源列表"""
    path = get_global_data_sources_path()
    if not os.path.exists(path):
        # 确保目录存在
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # 创建默认数据源
        default_sources = [
            {
                "id": "default",
                "name": "默认数据源",
                "description": "演示BI数据接口",
                "config": {
                    "base_url": os.getenv("DATA_API_BASE_URL", "https://api.example.com/data"),
                    "auth_type": "url_param",
                    "auth_key_name": "apikey",
                    "api_key": os.getenv("DATA_API_KEY", ""),
                    "timeout": 15,
                    "ssl_verify": False
                },
                "request_params": {
                    "job_id_field": "ZEMPLOYEE",
                    "time_field": "CALMONTH",
                    "module_field": "MOUDLE"
                },
                "is_default": True,
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        save_global_data_sources(default_sources)
        return default_sources

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_global_data_sources(sources: List[Dict[str, Any]]):
    """保存全局数据源列表"""
    path = get_global_data_sources_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)


# 默认数据源配置
DEFAULT_DATA_SOURCE = {
    "type": "api",
    "name": "默认数据源",
    "config": {
        "base_url": os.getenv("DATA_API_BASE_URL", "https://api.example.com/data"),
        "auth_type": "url_param",
        "auth_key_name": "apikey",
        "api_key": os.getenv("DATA_API_KEY", ""),
        "timeout": 15,
        "ssl_verify": False
    },
    "request_params": {
        "job_id_field": "ZEMPLOYEE",
        "time_field": "CALMONTH",
        "module_field": "MOUDLE"
    },
    "is_default": True,
    "is_active": True
}


# ==================== 全局数据源管理 API ====================

@router.get("", response_model=DataResponse)
async def list_global_data_sources(
    current_user: User = Depends(get_current_active_user)
):
    """获取全局数据源列表"""
    sources = load_global_data_sources()
    return DataResponse(
        success=True,
        data=sources
    )


@router.post("", response_model=DataResponse)
async def create_global_data_source(
    data_source: DataSource,
    current_user: User = Depends(get_current_active_user)
):
    """创建新的全局数据源"""
    sources = load_global_data_sources()

    # 生成唯一ID
    new_source = data_source.model_dump()
    new_source["id"] = str(uuid.uuid4())[:8]
    new_source["created_at"] = datetime.now().isoformat()
    new_source["updated_at"] = datetime.now().isoformat()

    sources.append(new_source)
    save_global_data_sources(sources)

    return DataResponse(
        success=True,
        message="数据源创建成功",
        data=new_source
    )


@router.get("/{source_id}", response_model=DataResponse)
async def get_global_data_source(
    source_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取指定数据源详情"""
    sources = load_global_data_sources()

    for source in sources:
        if source.get("id") == source_id:
            return DataResponse(success=True, data=source)

    raise HTTPException(status_code=404, detail="数据源不存在")


@router.put("/{source_id}", response_model=DataResponse)
async def update_global_data_source(
    source_id: str,
    data_source: DataSource,
    current_user: User = Depends(get_current_active_user)
):
    """更新数据源配置"""
    sources = load_global_data_sources()

    for i, source in enumerate(sources):
        if source.get("id") == source_id:
            updated = data_source.model_dump()
            updated["id"] = source_id
            updated["created_at"] = source.get("created_at")
            updated["updated_at"] = datetime.now().isoformat()
            sources[i] = updated
            save_global_data_sources(sources)
            return DataResponse(
                success=True,
                message="数据源更新成功",
                data=updated
            )

    raise HTTPException(status_code=404, detail="数据源不存在")


@router.delete("/{source_id}", response_model=DataResponse)
async def delete_global_data_source(
    source_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """删除数据源"""
    sources = load_global_data_sources()

    for i, source in enumerate(sources):
        if source.get("id") == source_id:
            if source.get("is_default"):
                raise HTTPException(status_code=400, detail="不能删除默认数据源")
            sources.pop(i)
            save_global_data_sources(sources)
            return DataResponse(
                success=True,
                message="数据源删除成功"
            )

    raise HTTPException(status_code=404, detail="数据源不存在")


# ==================== 测试连接 API ====================

@router.post("/test", response_model=DataResponse)
async def test_data_source(
    request: DataSourceTestRequest,
    current_user: User = Depends(get_current_active_user)
):
    """测试数据源连接"""
    start_time = time.time()

    try:
        # 构建请求URL
        if request.auth_type == AuthType.URL_PARAM:
            full_url = f"{request.base_url}?{request.auth_key_name}={request.api_key}"
        else:
            full_url = request.base_url

        # 构建测试请求体
        request_body = {
            "ZEMPLOYEE": request.test_job_id or "00165",
            "CALMONTH": request.test_time or "202601",
            "MOUDLE": "1"
        }

        headers = {"Content-Type": "application/json"}
        if request.auth_type == AuthType.HEADER:
            headers[request.auth_key_name] = request.api_key
        elif request.auth_type == AuthType.BEARER:
            headers["Authorization"] = f"Bearer {request.api_key}"

        async with ClientSession() as session:
            async with session.post(
                url=full_url,
                json=request_body,
                headers=headers,
                timeout=ClientTimeout(total=15),
                ssl=False
            ) as response:
                response_time_ms = int((time.time() - start_time) * 1000)

                if response.status == 200:
                    data = await response.json()
                    return DataResponse(
                        success=True,
                        message=f"连接成功，响应时间: {response_time_ms}ms",
                        data={
                            "response_time_ms": response_time_ms,
                            "data_keys": list(data.keys()) if isinstance(data, dict) else [],
                            "data_preview": str(data)[:500]
                        }
                    )
                else:
                    error_text = await response.text()
                    return DataResponse(
                        success=False,
                        message=f"连接失败: HTTP {response.status} - {error_text[:200]}",
                        data={"response_time_ms": response_time_ms}
                    )

    except asyncio.TimeoutError:
        return DataResponse(
            success=False,
            message="连接超时，请检查URL是否正确",
            data={"response_time_ms": int((time.time() - start_time) * 1000)}
        )
    except Exception as e:
        return DataResponse(
            success=False,
            message=f"连接失败: {str(e)}",
            data={"response_time_ms": int((time.time() - start_time) * 1000)}
        )


# ==================== 任务级数据源配置 API ====================

@router.get("/tasks/{task_id}", response_model=DataResponse)
async def get_task_data_source(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取任务的数据源配置"""
    config_path = get_task_config_path(task_id)

    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="任务配置不存在")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 获取任务关联的数据源ID
    data_source_id = config.get("data_source_id")

    # 如果有关联的数据源ID，从全局数据源中获取
    if data_source_id:
        sources = load_global_data_sources()
        for source in sources:
            if source.get("id") == data_source_id:
                return DataResponse(success=True, data=source)
        # 如果找不到，返回默认
        return DataResponse(success=True, data={"id": data_source_id, "error": "数据源已被删除"})

    # 兼容旧配置：如果任务有自定义数据源配置
    data_source = config.get("data_source", {})
    if data_source and data_source.get("config"):
        return DataResponse(success=True, data=data_source)

    # 返回默认数据源
    sources = load_global_data_sources()
    for source in sources:
        if source.get("is_default"):
            return DataResponse(success=True, data=source)

    return DataResponse(success=True, data=DEFAULT_DATA_SOURCE)


@router.put("/tasks/{task_id}", response_model=DataResponse)
async def update_task_data_source(
    task_id: str,
    data_source_id: str = None,
    current_user: User = Depends(get_current_active_user)
):
    """更新任务的数据源配置（关联到全局数据源）"""
    config_path = get_task_config_path(task_id)

    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="任务配置不存在")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 更新任务关联的数据源ID
    config["data_source_id"] = data_source_id
    config["updated_at"] = datetime.now().isoformat()

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return DataResponse(
        success=True,
        message="数据源配置更新成功"
    )