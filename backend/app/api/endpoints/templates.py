"""
模板管理 API
"""
import os
import json
import shutil
import hashlib
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse

from app.core.security import get_current_active_user
from app.db.models import User
from app.schemas.template import (
    TemplateCreate, TemplateUpdate, TemplateListItem,
    TemplateDetail, ApplyTemplateRequest
)
from app.schemas.common import DataResponse, ListResponse

router = APIRouter(prefix="/templates", tags=["模板管理"])


def get_templates_base_path() -> str:
    """获取模板根目录"""
    return os.path.join(os.path.dirname(__file__), "..", "..", "..", "config_files", "templates")


def get_tasks_base_path() -> str:
    """获取任务根目录"""
    return os.path.join(os.path.dirname(__file__), "..", "..", "..", "report_tasks")


def generate_template_id(template_name: str) -> str:
    """生成唯一的模板ID"""
    name_hash = hashlib.md5(template_name.encode()).hexdigest()[:8]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"tpl_{name_hash}_{timestamp}"


def get_template_metadata_path(template_id: str) -> str:
    """获取模板元数据文件路径"""
    return os.path.join(get_templates_base_path(), f"{template_id}.json")


def get_template_html_path(template_id: str) -> str:
    """获取模板HTML文件路径"""
    return os.path.join(get_templates_base_path(), f"{template_id}.html")


def load_template_metadata(template_id: str) -> dict:
    """加载模板元数据"""
    meta_path = get_template_metadata_path(template_id)
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_template_metadata(template_id: str, metadata: dict):
    """保存模板元数据"""
    meta_path = get_template_metadata_path(template_id)
    os.makedirs(os.path.dirname(meta_path), exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


@router.get("", response_model=ListResponse[TemplateListItem])
async def list_templates(
    current_user: User = Depends(get_current_active_user)
):
    """获取模板列表"""
    templates_base = get_templates_base_path()
    os.makedirs(templates_base, exist_ok=True)

    templates = []
    if os.path.exists(templates_base):
        for filename in os.listdir(templates_base):
            if filename.endswith(".html"):
                template_id = filename[:-5]  # 去掉 .html 后缀
                html_path = os.path.join(templates_base, filename)
                meta = load_template_metadata(template_id)

                file_size = os.path.getsize(html_path) if os.path.exists(html_path) else 0

                templates.append(TemplateListItem(
                    template_id=template_id,
                    template_name=meta.get("template_name", template_id),
                    description=meta.get("description"),
                    is_default=meta.get("is_default", False),
                    created_at=meta.get("created_at"),
                    updated_at=meta.get("updated_at"),
                    file_size=file_size
                ))

    # 按是否为默认模板排序，默认模板排前面
    templates.sort(key=lambda x: (not x.is_default, x.template_name))

    return ListResponse(
        success=True,
        data=templates,
        total=len(templates)
    )


@router.get("/{template_id}", response_model=DataResponse[TemplateDetail])
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取模板详情"""
    html_path = get_template_html_path(template_id)

    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="模板不存在")

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    meta = load_template_metadata(template_id)

    return DataResponse(
        success=True,
        data=TemplateDetail(
            template_id=template_id,
            template_name=meta.get("template_name", template_id),
            description=meta.get("description"),
            content=content,
            is_default=meta.get("is_default", False),
            created_at=meta.get("created_at"),
            updated_at=meta.get("updated_at")
        )
    )


@router.post("", response_model=DataResponse)
async def create_template(
    request: TemplateCreate,
    current_user: User = Depends(get_current_active_user)
):
    """创建新模板"""
    templates_base = get_templates_base_path()
    os.makedirs(templates_base, exist_ok=True)

    # 生成唯一ID
    template_id = generate_template_id(request.template_name)

    # 保存HTML文件
    html_path = get_template_html_path(template_id)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(request.content)

    # 保存元数据
    now = datetime.now().isoformat()
    metadata = {
        "template_id": template_id,
        "template_name": request.template_name,
        "description": request.description,
        "is_default": False,
        "created_at": now,
        "updated_at": now
    }
    save_template_metadata(template_id, metadata)

    return DataResponse(
        success=True,
        message="模板创建成功",
        data={
            "template_id": template_id,
            "template_name": request.template_name
        }
    )


@router.put("/{template_id}", response_model=DataResponse)
async def update_template(
    template_id: str,
    request: TemplateUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """更新模板"""
    html_path = get_template_html_path(template_id)

    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="模板不存在")

    meta = load_template_metadata(template_id)

    # 更新HTML内容
    if request.content:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(request.content)

    # 更新元数据
    if request.template_name:
        meta["template_name"] = request.template_name
    if request.description is not None:
        meta["description"] = request.description
    meta["updated_at"] = datetime.now().isoformat()

    save_template_metadata(template_id, meta)

    return DataResponse(
        success=True,
        message="模板更新成功",
        data={
            "template_id": template_id,
            "template_name": meta.get("template_name")
        }
    )


@router.delete("/{template_id}", response_model=DataResponse)
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """删除模板"""
    meta = load_template_metadata(template_id)

    # 不允许删除默认模板
    if meta.get("is_default", False):
        raise HTTPException(status_code=400, detail="不能删除默认模板")

    html_path = get_template_html_path(template_id)
    meta_path = get_template_metadata_path(template_id)

    try:
        if os.path.exists(html_path):
            os.remove(html_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)

        return DataResponse(
            success=True,
            message="模板删除成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除模板失败: {str(e)}")


@router.post("/{template_id}/apply", response_model=DataResponse)
async def apply_template(
    template_id: str,
    request: ApplyTemplateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    应用模板到指定任务

    将模板HTML复制到任务的wrapping目录
    """
    tasks_base = get_tasks_base_path()
    task_path = os.path.join(tasks_base, request.task_id)

    if not os.path.exists(task_path):
        raise HTTPException(status_code=404, detail="任务不存在")

    # 源模板路径
    src_html = get_template_html_path(template_id)
    if not os.path.exists(src_html):
        raise HTTPException(status_code=404, detail="模板不存在")

    # 目标路径
    dst_html = os.path.join(task_path, "config_files", "wrapping", "template.html")
    dst_wrapping = os.path.join(task_path, "config_files", "wrapping", "wrapping.json")

    # 确保目标目录存在
    os.makedirs(os.path.dirname(dst_html), exist_ok=True)

    try:
        # 复制模板文件
        shutil.copy2(src_html, dst_html)

        # 获取模板元数据
        meta = load_template_metadata(template_id)

        # 更新 wrapping.json
        wrapping_data = {}
        if os.path.exists(dst_wrapping):
            with open(dst_wrapping, "r", encoding="utf-8") as f:
                wrapping_data = json.load(f)

        wrapping_data["selected_template"] = template_id
        wrapping_data["selected_template_name"] = meta.get("template_name", template_id)
        wrapping_data["template_applied_at"] = datetime.now().isoformat()

        with open(dst_wrapping, "w", encoding="utf-8") as f:
            json.dump(wrapping_data, f, ensure_ascii=False, indent=2)

        return DataResponse(
            success=True,
            message=f"模板已应用到任务 {request.task_id}",
            data={
                "template_id": template_id,
                "template_name": meta.get("template_name"),
                "task_id": request.task_id
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"应用模板失败: {str(e)}")


@router.post("/upload", response_model=DataResponse)
async def upload_template(
    file: UploadFile = File(...),
    template_name: Optional[str] = None,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    上传模板文件

    支持 .html 文件上传
    """
    if not file.filename.endswith(".html"):
        raise HTTPException(status_code=400, detail="只支持 .html 文件")

    # 读取文件内容
    content = await file.read()
    try:
        content_str = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content_str = content.decode("gbk")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="文件编码不支持，请使用 UTF-8 编码")

    # 生成模板名称
    name = template_name or os.path.splitext(file.filename)[0]

    templates_base = get_templates_base_path()
    os.makedirs(templates_base, exist_ok=True)

    # 生成唯一ID
    template_id = generate_template_id(name)

    # 保存HTML文件
    html_path = get_template_html_path(template_id)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content_str)

    # 保存元数据
    now = datetime.now().isoformat()
    metadata = {
        "template_id": template_id,
        "template_name": name,
        "description": description or f"从文件 {file.filename} 上传",
        "is_default": False,
        "created_at": now,
        "updated_at": now
    }
    save_template_metadata(template_id, metadata)

    return DataResponse(
        success=True,
        message="模板上传成功",
        data={
            "template_id": template_id,
            "template_name": name
        }
    )


@router.get("/{template_id}/preview", response_class=HTMLResponse)
async def preview_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取模板预览HTML"""
    html_path = get_template_html_path(template_id)

    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="模板不存在")

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    return HTMLResponse(content=content)