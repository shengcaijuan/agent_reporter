"""
任务管理 API
"""
import os
import json
import hashlib
import re
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.db.models import User
from app.schemas.task import TaskListItem, TaskDetail, ChapterInfo, SaleInfo
from app.schemas.common import DataResponse, ListResponse

router = APIRouter(prefix="/tasks", tags=["任务管理"])


# 创建任务请求模型
class CreateTaskRequest(BaseModel):
    task_name: str
    business_department: str
    description: Optional[str] = None


def get_tasks_base_path() -> str:
    """获取任务根目录"""
    # 配置文件存储在 backend/report_tasks 目录下
    # tasks.py 位于 backend/app/api/endpoints/tasks.py
    # 需要往上 3 级才能到达 backend 目录
    return os.path.join(os.path.dirname(__file__), "..", "..", "..", "report_tasks")


def get_task_index_path() -> str:
    """获取 task_index.json 文件路径"""
    return os.path.join(get_tasks_base_path(), "task_index.json")


def sync_task_index():
    """
    同步 task_index.json 与实际任务目录

    扫描 report_tasks 目录，将所有任务同步到 task_index.json
    """
    tasks_base = get_tasks_base_path()
    index_path = get_task_index_path()

    # 确保目录存在
    os.makedirs(tasks_base, exist_ok=True)

    # 扫描实际存在的任务目录
    existing_tasks = {}
    if os.path.exists(tasks_base):
        for task_id in os.listdir(tasks_base):
            task_path = os.path.join(tasks_base, task_id)
            if os.path.isdir(task_path):
                config_file = os.path.join(task_path, "config_files", "task_config.json")
                if os.path.exists(config_file):
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            config = json.load(f)

                        # 统计章节数量
                        chapters_file = os.path.join(task_path, "config_files", "chapters.json")
                        chapter_count = 0
                        if os.path.exists(chapters_file):
                            with open(chapters_file, "r", encoding="utf-8") as f:
                                chapters_data = json.load(f)
                                chapter_count = len(chapters_data.get("chapters", []))

                        existing_tasks[task_id] = {
                            "task_id": task_id,
                            "task_name": config.get("task_name", task_id),
                            "business_department": config.get("business_department", ""),
                            "description": config.get("description", ""),
                            "chapter_count": chapter_count,
                            "created_at": config.get("created_at", ""),
                            "updated_at": config.get("updated_at", ""),
                            "status": "active"
                        }
                    except Exception:
                        pass

    # 读取现有的 task_index.json
    current_index = {"tasks": []}
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                current_index = json.load(f)
        except Exception:
            pass

    # 合并数据：保留现有数据中的额外信息，添加新任务
    merged_tasks = []
    existing_task_ids = set(existing_tasks.keys())

    # 处理已存在的任务（保留原有顺序和额外信息）
    for task in current_index.get("tasks", []):
        task_id = task.get("task_id")
        if task_id in existing_task_ids:
            # 更新现有任务的信息
            merged_task = {**task, **existing_tasks[task_id]}
            merged_tasks.append(merged_task)
            existing_task_ids.remove(task_id)

    # 添加新发现的任务
    for task_id, task_info in existing_tasks.items():
        if task_id not in [t.get("task_id") for t in merged_tasks]:
            merged_tasks.append(task_info)

    # 保存更新后的索引
    current_index["tasks"] = merged_tasks
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(current_index, f, ensure_ascii=False, indent=2)

    return merged_tasks


def update_task_index(task_id: str, action: str, task_info: dict = None):
    """
    更新 task_index.json

    Args:
        task_id: 任务ID
        action: 操作类型 ('add', 'delete', 'update')
        task_info: 任务信息（add/update时使用）
    """
    index_path = get_task_index_path()

    # 读取现有索引
    current_index = {"tasks": []}
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                current_index = json.load(f)
        except Exception:
            pass

    if action == "add" and task_info:
        # 添加新任务
        current_index["tasks"].append(task_info)
    elif action == "delete":
        # 删除任务
        current_index["tasks"] = [
            t for t in current_index.get("tasks", [])
            if t.get("task_id") != task_id
        ]
    elif action == "update" and task_info:
        # 更新任务信息
        for i, t in enumerate(current_index.get("tasks", [])):
            if t.get("task_id") == task_id:
                current_index["tasks"][i] = {**t, **task_info}
                break

    # 保存
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(current_index, f, ensure_ascii=False, indent=2)


def generate_task_id(task_name: str) -> str:
    """
    根据任务名称生成唯一的 task_id

    规则：
    1. 尝试提取名称中的关键词（如"马上住"->"mashangzhu"）
    2. 加上时间戳和随机数确保唯一性
    """
    import random

    # 名称映射表（常用词汇）
    name_mapping = {
        "马上住": "mashangzhu",
        "焕新": "huanxin",
        "事业部": "business",
        "销售": "sales",
        "报告": "report",
        "工程漆": "gongchengqi",
        "家装": "jiazhuang",
        "零售": "lingshou",
        "综合": "zonghe",
    }

    # 尝试匹配关键词
    matched_parts = []
    remaining = task_name

    for cn, en in sorted(name_mapping.items(), key=lambda x: -len(x[0])):
        if cn in remaining:
            matched_parts.append(en)
            remaining = remaining.replace(cn, "")

    # 如果匹配到关键词，用关键词组合
    if matched_parts:
        base_id = "_".join(matched_parts[:2])  # 最多取前两个关键词
    else:
        # 否则用名称哈希
        hash_val = hashlib.md5(task_name.encode()).hexdigest()[:8]
        base_id = f"task_{hash_val}"

    # 添加时间戳（精确到毫秒）和随机数确保唯一性
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]  # 精确到毫秒
    random_suffix = random.randint(100, 999)
    task_id = f"{base_id}_{timestamp}_{random_suffix}"

    return task_id


def create_task_directories(tasks_base: str, task_id: str):
    """创建任务所需的目录结构"""
    task_path = os.path.join(tasks_base, task_id)

    # 创建主目录
    os.makedirs(task_path, exist_ok=True)

    # 创建子目录
    subdirs = [
        "config_files",
        "config_files/guidelines",
        "config_files/guidelines/guidelines_md",
        "config_files/tool_agent_configs",
        "config_files/sales",
        "config_files/wrapping",
        "reports"
    ]

    for subdir in subdirs:
        os.makedirs(os.path.join(task_path, subdir), exist_ok=True)

    return task_path


def create_default_config_files(task_path: str, task_id: str, task_name: str,
                                 business_department: str, description: str = None):
    """创建默认配置文件"""
    config_path = os.path.join(task_path, "config_files")

    # 1. 创建 task_config.json
    task_config = {
        "task_id": task_id,
        "task_name": task_name,
        "business_department": business_department,
        "description": description or f"{task_name}销售人员业绩分析报告",
        "data_source": {
            "type": "api",
            "endpoint": "",
            "filter_param": {
                "field": "",
                "value": business_department
            }
        },
        "report_structure": {
            "output_format": "html",
            "include_toc": True,
            "include_summary": True
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    with open(os.path.join(config_path, "task_config.json"), "w", encoding="utf-8") as f:
        json.dump(task_config, f, ensure_ascii=False, indent=2)

    # 2. 创建 chapters.json (默认1章结构)
    chapters_config = {
        "chapters": [
            {"chapter_id": 1, "chapter_name": "第一章", "chapter_type": "simple", "has_tools": False, "description": ""}
        ]
    }

    with open(os.path.join(config_path, "chapters.json"), "w", encoding="utf-8") as f:
        json.dump(chapters_config, f, ensure_ascii=False, indent=2)

    # 3. 创建空的 sales.json
    sales_data = {
        "task_id": task_id,
        "task_name": task_name,
        "description": f"{task_name}销售人员名单",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "province_sales_count": {},
        "sales": []
    }

    with open(os.path.join(config_path, "sales", "sales.json"), "w", encoding="utf-8") as f:
        json.dump(sales_data, f, ensure_ascii=False, indent=2)

    # 4. 创建默认的第一章 guideline 配置
    guideline = {
        "chapter_id": 1,
        "chapter_name": "第一章",
        "structure_intro": "",
        "sections": [],
        "style_requirements": [],
        "output_example": ""
    }
    with open(os.path.join(config_path, "guidelines", "chapter1.json"), "w", encoding="utf-8") as f:
        json.dump(guideline, f, ensure_ascii=False, indent=2)

    # 创建空的 md 文件
    with open(os.path.join(config_path, "guidelines", "guidelines_md", "chapter1.md"), "w", encoding="utf-8") as f:
        f.write("# 第一章\n\n待配置\n")

    # 5. 不再预创建工具配置文件，按需在章节配置时创建

    # 6. 创建空的 wrapping 配置
    wrapping_config = {
        "template": "template.html",
        "output_format": "html"
    }
    with open(os.path.join(config_path, "wrapping", "wrapping.json"), "w", encoding="utf-8") as f:
        json.dump(wrapping_config, f, ensure_ascii=False, indent=2)

    # 创建简单的模板文件
    template_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{title}}</title>
</head>
<body>
    <h1>{{title}}</h1>
    {{content}}
</body>
</html>"""
    with open(os.path.join(config_path, "wrapping", "template.html"), "w", encoding="utf-8") as f:
        f.write(template_html)

    with open(os.path.join(config_path, "wrapping", "lay_out_requirements.md"), "w", encoding="utf-8") as f:
        f.write("# 排版要求\n\n待配置\n")


@router.get("", response_model=ListResponse[TaskListItem])
async def list_tasks(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取所有可用任务列表"""
    tasks_base = get_tasks_base_path()
    tasks = []

    if os.path.exists(tasks_base):
        for task_id in os.listdir(tasks_base):
            task_path = os.path.join(tasks_base, task_id)
            if os.path.isdir(task_path):
                # 读取任务配置
                config_path = os.path.join(task_path, "config_files", "task_config.json")
                task_name = task_id
                business_department = None
                description = None
                created_at = None

                if os.path.exists(config_path):
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            task_name = config.get("task_name", task_id)
                            # 兼容两种字段名
                            business_department = config.get("business_department") or config.get("business_unit")
                            description = config.get("description")
                            created_at = config.get("created_at")
                    except Exception:
                        pass

                # 读取章节配置，获取章节数量
                chapters_count = 0
                chapters_file = os.path.join(task_path, "config_files", "chapters.json")
                if os.path.exists(chapters_file):
                    try:
                        with open(chapters_file, "r", encoding="utf-8") as f:
                            chapters_data = json.load(f)
                            chapters_count = len(chapters_data.get("chapters", []))
                    except Exception:
                        pass

                # 统计报告数量
                reports_path = os.path.join(task_path, "reports")
                report_count = 0
                if os.path.exists(reports_path):
                    for root, dirs, files in os.walk(reports_path):
                        report_count += len([f for f in files if f.endswith(".html") or f.endswith(".md")])

                tasks.append(TaskListItem(
                    task_id=task_id,
                    task_name=task_name,
                    business_department=business_department,
                    description=description,
                    chapters=chapters_count,
                    status="active",
                    created_at=created_at,
                    report_count=report_count
                ))

    return ListResponse(
        success=True,
        data=tasks,
        total=len(tasks)
    )


@router.get("/{task_id}", response_model=DataResponse[TaskDetail])
async def get_task_detail(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取任务详情"""
    tasks_base = get_tasks_base_path()
    task_path = os.path.join(tasks_base, task_id)

    if not os.path.exists(task_path):
        raise HTTPException(status_code=404, detail="任务不存在")

    config_path = os.path.join(task_path, "config_files")

    # 读取任务配置
    task_config = {}
    task_config_file = os.path.join(config_path, "task_config.json")
    if os.path.exists(task_config_file):
        with open(task_config_file, "r", encoding="utf-8") as f:
            task_config = json.load(f)

    # 读取章节配置
    chapters = []
    chapters_file = os.path.join(config_path, "chapters.json")
    if os.path.exists(chapters_file):
        with open(chapters_file, "r", encoding="utf-8") as f:
            chapters_data = json.load(f)
            for ch in chapters_data.get("chapters", []):
                chapters.append(ChapterInfo(
                    chapter_id=ch.get("chapter_id"),
                    chapter_name=ch.get("chapter_name", ""),
                    chapter_type=ch.get("chapter_type", "simple"),
                    has_tools=ch.get("has_tools", False)
                ))

    # 读取销售名单
    sales = []
    sales_file = os.path.join(config_path, "sales", "sales.json")
    if os.path.exists(sales_file):
        with open(sales_file, "r", encoding="utf-8") as f:
            sales_data = json.load(f)
            # sales.json 可能是对象格式，包含 sales 数组
            if isinstance(sales_data, dict) and "sales" in sales_data:
                sales_list = sales_data["sales"]
            elif isinstance(sales_data, list):
                sales_list = sales_data
            else:
                sales_list = []
            for sale in sales_list:
                sales.append(SaleInfo(
                    sale_id=sale.get("job_id", ""),
                    sale_name=sale.get("sale_name", ""),
                    department=sale.get("business_department")
                ))

    task_detail = TaskDetail(
        task_id=task_id,
        task_name=task_config.get("task_name", task_id),
        business_department=task_config.get("business_department") or task_config.get("business_unit"),
        description=task_config.get("description"),
        chapters=chapters,
        sales=sales
    )

    return DataResponse(
        success=True,
        data=task_detail
    )


@router.get("/{task_id}/sales", response_model=DataResponse)
async def get_task_sales(
    task_id: str,
    region: Optional[str] = Query(None, description="按大区筛选"),
    province: Optional[str] = Query(None, description="按省区筛选"),
    sale_class: Optional[str] = Query(None, description="按岗位筛选"),
    search: Optional[str] = Query(None, description="搜索关键字"),
    current_user: User = Depends(get_current_active_user)
):
    """获取任务的销售人员列表"""
    tasks_base = get_tasks_base_path()
    sales_file = os.path.join(tasks_base, task_id, "config_files", "sales", "sales.json")

    if not os.path.exists(sales_file):
        raise HTTPException(status_code=404, detail="销售人员数据不存在")

    with open(sales_file, "r", encoding="utf-8") as f:
        sales_data = json.load(f)

    # sales.json 可能是对象格式，包含 sales 数组
    if isinstance(sales_data, dict) and "sales" in sales_data:
        sales_list = sales_data["sales"]
        # 提取元数据
        province_sales_count = sales_data.get("province_sales_count", {})
    elif isinstance(sales_data, list):
        sales_list = sales_data
        province_sales_count = {}
    else:
        sales_list = []
        province_sales_count = {}

    # 应用筛选条件
    filtered_sales = []
    for sale in sales_list:
        # 按大区筛选
        if region and sale.get("region") != region:
            continue
        # 按省区筛选
        if province and sale.get("province") != province:
            continue
        # 按岗位筛选
        if sale_class and sale.get("sale_class") != sale_class:
            continue
        # 搜索关键字
        if search:
            search_lower = search.lower()
            if (search_lower not in sale.get("sale_name", "").lower() and
                search_lower not in sale.get("job_id", "").lower()):
                continue

        filtered_sales.append({
            "job_id": sale.get("job_id", ""),
            "sale_name": sale.get("sale_name", ""),
            "sale_class": sale.get("sale_class"),
            "city_operation_department": sale.get("city_operation_department", ""),
            "province": sale.get("province", ""),
            "region": sale.get("region", ""),
            "business_department": sale.get("business_department", "")
        })

    # 获取唯一的大区、省区、岗位列表（用于筛选）
    regions = sorted(list(set(s.get("region", "") for s in sales_list if s.get("region"))))
    provinces = sorted(list(set(s.get("province", "") for s in sales_list if s.get("province"))))
    sale_classes = sorted(list(set(s.get("sale_class", "") for s in sales_list if s.get("sale_class"))))

    return DataResponse(
        success=True,
        data={
            "total": len(sales_list),
            "filtered_count": len(filtered_sales),
            "province_sales_count": province_sales_count,
            "filters": {
                "regions": regions,
                "provinces": provinces,
                "sale_classes": sale_classes
            },
            "sales": filtered_sales
        }
    )


@router.post("", response_model=DataResponse)
async def create_task(
    request: CreateTaskRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    创建新的报告任务

    - 自动生成唯一的 task_id
    - 创建任务目录结构
    - 初始化配置文件
    """
    tasks_base = get_tasks_base_path()

    # 确保任务根目录存在
    os.makedirs(tasks_base, exist_ok=True)

    # 生成唯一的 task_id
    task_id = generate_task_id(request.task_name)

    # 检查是否已存在
    task_path = os.path.join(tasks_base, task_id)
    if os.path.exists(task_path):
        raise HTTPException(status_code=400, detail="任务ID已存在，请重试")

    try:
        # 创建目录结构
        create_task_directories(tasks_base, task_id)

        # 创建配置文件
        create_default_config_files(
            task_path=task_path,
            task_id=task_id,
            task_name=request.task_name,
            business_department=request.business_department,
            description=request.description
        )

        # 更新 task_index.json
        task_info = {
            "task_id": task_id,
            "task_name": request.task_name,
            "business_department": request.business_department,
            "description": request.description or f"{request.task_name}销售人员业绩分析报告",
            "chapter_count": 1,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "active"
        }
        update_task_index(task_id, "add", task_info)

        return DataResponse(
            success=True,
            message="任务创建成功",
            data={
                "task_id": task_id,
                "task_name": request.task_name,
                "business_department": request.business_department,
                "description": request.description,
                "created_at": datetime.now().isoformat()
            }
        )

    except Exception as e:
        # 如果创建失败，清理已创建的目录
        if os.path.exists(task_path):
            import shutil
            shutil.rmtree(task_path)
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.put("/{task_id}", response_model=DataResponse)
async def update_task(
    task_id: str,
    request: CreateTaskRequest,
    current_user: User = Depends(get_current_active_user)
):
    """更新任务配置"""
    tasks_base = get_tasks_base_path()
    task_path = os.path.join(tasks_base, task_id)

    if not os.path.exists(task_path):
        raise HTTPException(status_code=404, detail="任务不存在")

    config_file = os.path.join(task_path, "config_files", "task_config.json")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 更新配置
        config["task_name"] = request.task_name
        config["business_department"] = request.business_department
        config["description"] = request.description or config.get("description", "")
        config["updated_at"] = datetime.now().isoformat()

        # 如果更新了事业部，也更新数据源筛选参数
        if "data_source" in config and "filter_param" in config["data_source"]:
            config["data_source"]["filter_param"]["value"] = request.business_department

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return DataResponse(
            success=True,
            message="任务更新成功",
            data={
                "task_id": task_id,
                "task_name": request.task_name,
                "business_department": request.business_department,
                "updated_at": config["updated_at"]
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新任务失败: {str(e)}")


@router.delete("/{task_id}", response_model=DataResponse)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """删除任务"""
    tasks_base = get_tasks_base_path()
    task_path = os.path.join(tasks_base, task_id)

    if not os.path.exists(task_path):
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        import shutil
        shutil.rmtree(task_path)

        # 更新 task_index.json
        update_task_index(task_id, "delete")

        return DataResponse(
            success=True,
            message="任务删除成功"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


# ==================== 章节配置相关 API ====================

@router.get("/{task_id}/chapters", response_model=DataResponse)
async def get_chapters(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取任务的章节列表"""
    tasks_base = get_tasks_base_path()
    chapters_file = os.path.join(tasks_base, task_id, "config_files", "chapters.json")

    if not os.path.exists(chapters_file):
        raise HTTPException(status_code=404, detail="章节配置不存在")

    with open(chapters_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return DataResponse(
        success=True,
        data=data.get("chapters", [])
    )


@router.get("/{task_id}/chapters/{chapter_id}", response_model=DataResponse)
async def get_chapter_config(
    task_id: str,
    chapter_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """获取章节配置详情"""
    tasks_base = get_tasks_base_path()
    guideline_file = os.path.join(tasks_base, task_id, "config_files", "guidelines", f"chapter{chapter_id}.json")

    if not os.path.exists(guideline_file):
        raise HTTPException(status_code=404, detail="章节配置不存在")

    with open(guideline_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return DataResponse(
        success=True,
        data=data
    )


@router.put("/{task_id}/chapters/{chapter_id}", response_model=DataResponse)
async def update_chapter_config(
    task_id: str,
    chapter_id: int,
    config: dict,
    current_user: User = Depends(get_current_active_user)
):
    """更新章节配置"""
    tasks_base = get_tasks_base_path()
    guideline_file = os.path.join(tasks_base, task_id, "config_files", "guidelines", f"chapter{chapter_id}.json")

    if not os.path.exists(guideline_file):
        raise HTTPException(status_code=404, detail="章节配置不存在")

    try:
        # 读取现有配置
        with open(guideline_file, "r", encoding="utf-8") as f:
            existing = json.load(f)

        # 合并更新
        existing.update(config)
        existing["chapter_id"] = chapter_id
        existing["updated_at"] = datetime.now().isoformat()

        # 保存
        with open(guideline_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        # 同时更新 chapters.json 中的章节名称
        if "chapter_name" in config:
            chapters_file = os.path.join(tasks_base, task_id, "config_files", "chapters.json")
            if os.path.exists(chapters_file):
                with open(chapters_file, "r", encoding="utf-8") as f:
                    chapters_data = json.load(f)

                for ch in chapters_data.get("chapters", []):
                    if ch.get("chapter_id") == chapter_id:
                        ch["chapter_name"] = config["chapter_name"]
                        break

                with open(chapters_file, "w", encoding="utf-8") as f:
                    json.dump(chapters_data, f, ensure_ascii=False, indent=2)

        return DataResponse(
            success=True,
            message="章节配置更新成功",
            data=existing
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新章节配置失败: {str(e)}")


# ==================== 工具配置相关 API ====================

@router.get("/{task_id}/tools/{chapter_id}", response_model=DataResponse)
async def get_tool_configs(
    task_id: str,
    chapter_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """获取章节的工具配置列表"""
    tasks_base = get_tasks_base_path()
    tool_file = os.path.join(tasks_base, task_id, "config_files", "tool_agent_configs", f"chapter{chapter_id}.json")

    if not os.path.exists(tool_file):
        # 返回空配置
        return DataResponse(
            success=True,
            data={
                "chapter_id": chapter_id,
                "tools": []
            }
        )

    with open(tool_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 如果数据是列表格式，转换为对象格式
    if isinstance(data, list):
        return DataResponse(
            success=True,
            data={
                "chapter_id": chapter_id,
                "tools": data
            }
        )

    return DataResponse(
        success=True,
        data=data
    )


@router.put("/{task_id}/tools/{chapter_id}", response_model=DataResponse)
async def update_all_tool_configs(
    task_id: str,
    chapter_id: int,
    config: dict,
    current_user: User = Depends(get_current_active_user)
):
    """批量更新章节的工具配置"""
    tasks_base = get_tasks_base_path()
    tool_file = os.path.join(tasks_base, task_id, "config_files", "tool_agent_configs", f"chapter{chapter_id}.json")

    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(tool_file), exist_ok=True)

        # 保存配置
        config["updated_at"] = datetime.now().isoformat()
        with open(tool_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return DataResponse(
            success=True,
            message="工具配置更新成功",
            data=config
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新工具配置失败: {str(e)}")


@router.post("/{task_id}/tools/{chapter_id}", response_model=DataResponse)
async def create_tool_config(
    task_id: str,
    chapter_id: int,
    config: dict,
    current_user: User = Depends(get_current_active_user)
):
    """创建工具配置"""
    tasks_base = get_tasks_base_path()
    tool_file = os.path.join(tasks_base, task_id, "config_files", "tool_agent_configs", f"chapter{chapter_id}.json")

    try:
        # 读取现有配置
        if os.path.exists(tool_file):
            with open(tool_file, "r", encoding="utf-8") as f:
                tools = json.load(f)
        else:
            tools = []

        # 生成工具ID
        import uuid
        config["tool_id"] = str(uuid.uuid4())[:8]
        config["created_at"] = datetime.now().isoformat()

        tools.append(config)

        with open(tool_file, "w", encoding="utf-8") as f:
            json.dump(tools, f, ensure_ascii=False, indent=2)

        return DataResponse(
            success=True,
            message="工具配置创建成功",
            data=config
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建工具配置失败: {str(e)}")


@router.put("/{task_id}/tools/{chapter_id}/{tool_id}", response_model=DataResponse)
async def update_tool_config(
    task_id: str,
    chapter_id: int,
    tool_id: str,
    config: dict,
    current_user: User = Depends(get_current_active_user)
):
    """更新工具配置"""
    tasks_base = get_tasks_base_path()
    tool_file = os.path.join(tasks_base, task_id, "config_files", "tool_agent_configs", f"chapter{chapter_id}.json")

    if not os.path.exists(tool_file):
        raise HTTPException(status_code=404, detail="工具配置不存在")

    try:
        with open(tool_file, "r", encoding="utf-8") as f:
            tools = json.load(f)

        # 查找并更新
        found = False
        for i, tool in enumerate(tools):
            if tool.get("tool_id") == tool_id:
                config["tool_id"] = tool_id
                config["updated_at"] = datetime.now().isoformat()
                tools[i] = config
                found = True
                break

        if not found:
            raise HTTPException(status_code=404, detail="工具配置不存在")

        with open(tool_file, "w", encoding="utf-8") as f:
            json.dump(tools, f, ensure_ascii=False, indent=2)

        return DataResponse(
            success=True,
            message="工具配置更新成功",
            data=config
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新工具配置失败: {str(e)}")


@router.delete("/{task_id}/tools/{chapter_id}/{tool_id}", response_model=DataResponse)
async def delete_tool_config(
    task_id: str,
    chapter_id: int,
    tool_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """删除工具配置"""
    tasks_base = get_tasks_base_path()
    tool_file = os.path.join(tasks_base, task_id, "config_files", "tool_agent_configs", f"chapter{chapter_id}.json")

    if not os.path.exists(tool_file):
        raise HTTPException(status_code=404, detail="工具配置不存在")

    try:
        with open(tool_file, "r", encoding="utf-8") as f:
            tools = json.load(f)

        # 过滤删除
        new_tools = [t for t in tools if t.get("tool_id") != tool_id]

        if len(new_tools) == len(tools):
            raise HTTPException(status_code=404, detail="工具配置不存在")

        with open(tool_file, "w", encoding="utf-8") as f:
            json.dump(new_tools, f, ensure_ascii=False, indent=2)

        return DataResponse(
            success=True,
            message="工具配置删除成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除工具配置失败: {str(e)}")


# ==================== 章节管理 API（新增/删除）====================

@router.post("/{task_id}/chapters", response_model=DataResponse)
async def add_chapter(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """添加新章节"""
    tasks_base = get_tasks_base_path()
    task_path = os.path.join(tasks_base, task_id)

    if not os.path.exists(task_path):
        raise HTTPException(status_code=404, detail="任务不存在")

    config_path = os.path.join(task_path, "config_files")
    chapters_file = os.path.join(config_path, "chapters.json")

    try:
        # 读取现有章节配置
        with open(chapters_file, "r", encoding="utf-8") as f:
            chapters_data = json.load(f)

        chapters = chapters_data.get("chapters", [])

        # 确定新章节ID
        max_id = max([ch.get("chapter_id", 0) for ch in chapters], default=0)
        new_chapter_id = max_id + 1

        # 创建新章节
        new_chapter = {
            "chapter_id": new_chapter_id,
            "chapter_name": f"第{new_chapter_id}章",
            "chapter_type": "simple",
            "has_tools": False,
            "description": ""
        }

        chapters.append(new_chapter)
        chapters_data["chapters"] = chapters

        # 保存章节列表
        with open(chapters_file, "w", encoding="utf-8") as f:
            json.dump(chapters_data, f, ensure_ascii=False, indent=2)

        # 创建章节guideline配置文件
        guideline_file = os.path.join(config_path, "guidelines", f"chapter{new_chapter_id}.json")
        guideline = {
            "chapter_id": new_chapter_id,
            "chapter_name": f"第{new_chapter_id}章",
            "structure_intro": "",
            "sections": [],
            "style_requirements": [],
            "output_example": ""
        }
        with open(guideline_file, "w", encoding="utf-8") as f:
            json.dump(guideline, f, ensure_ascii=False, indent=2)

        # 创建空的md文件
        md_file = os.path.join(config_path, "guidelines", "guidelines_md", f"chapter{new_chapter_id}.md")
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# 第{new_chapter_id}章\n\n待配置\n")

        return DataResponse(
            success=True,
            message="章节添加成功",
            data=new_chapter
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加章节失败: {str(e)}")


@router.delete("/{task_id}/chapters/{chapter_id}", response_model=DataResponse)
async def delete_chapter(
    task_id: str,
    chapter_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """删除章节"""
    tasks_base = get_tasks_base_path()
    task_path = os.path.join(tasks_base, task_id)

    if not os.path.exists(task_path):
        raise HTTPException(status_code=404, detail="任务不存在")

    config_path = os.path.join(task_path, "config_files")
    chapters_file = os.path.join(config_path, "chapters.json")

    try:
        # 读取现有章节配置
        with open(chapters_file, "r", encoding="utf-8") as f:
            chapters_data = json.load(f)

        chapters = chapters_data.get("chapters", [])

        # 检查章节是否存在
        chapter_exists = any(ch.get("chapter_id") == chapter_id for ch in chapters)
        if not chapter_exists:
            raise HTTPException(status_code=404, detail="章节不存在")

        # 至少保留一个章节
        if len(chapters) <= 1:
            raise HTTPException(status_code=400, detail="至少需要保留一个章节")

        # 移除章节
        chapters_data["chapters"] = [ch for ch in chapters if ch.get("chapter_id") != chapter_id]

        # 保存章节列表
        with open(chapters_file, "w", encoding="utf-8") as f:
            json.dump(chapters_data, f, ensure_ascii=False, indent=2)

        # 删除相关配置文件
        guideline_file = os.path.join(config_path, "guidelines", f"chapter{chapter_id}.json")
        if os.path.exists(guideline_file):
            os.remove(guideline_file)

        md_file = os.path.join(config_path, "guidelines", "guidelines_md", f"chapter{chapter_id}.md")
        if os.path.exists(md_file):
            os.remove(md_file)

        tool_file = os.path.join(config_path, "tool_agent_configs", f"chapter{chapter_id}.json")
        if os.path.exists(tool_file):
            os.remove(tool_file)

        return DataResponse(
            success=True,
            message="章节删除成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除章节失败: {str(e)}")


# ==================== 报告样式配置 API ====================

@router.get("/{task_id}/wrapping", response_model=DataResponse)
async def get_wrapping_config(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取报告样式配置"""
    tasks_base = get_tasks_base_path()
    wrapping_file = os.path.join(tasks_base, task_id, "config_files", "wrapping", "wrapping.json")

    if not os.path.exists(wrapping_file):
        # 返回默认配置
        return DataResponse(
            success=True,
            data={
                "task_id": task_id,
                "lay_out_requirements": []
            }
        )

    with open(wrapping_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return DataResponse(
        success=True,
        data=data
    )


@router.put("/{task_id}/wrapping", response_model=DataResponse)
async def update_wrapping_config(
    task_id: str,
    config: dict,
    current_user: User = Depends(get_current_active_user)
):
    """更新报告样式配置"""
    tasks_base = get_tasks_base_path()
    task_path = os.path.join(tasks_base, task_id)

    if not os.path.exists(task_path):
        raise HTTPException(status_code=404, detail="任务不存在")

    wrapping_file = os.path.join(task_path, "config_files", "wrapping", "wrapping.json")

    try:
        config["task_id"] = task_id
        config["updated_at"] = datetime.now().isoformat()

        with open(wrapping_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return DataResponse(
            success=True,
            message="报告样式配置更新成功",
            data=config
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新报告样式配置失败: {str(e)}")


# ==================== 统计数据 API ====================

@router.get("/stats/dashboard", response_model=DataResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取仪表盘统计数据

    返回:
    - report_count: 报告总数（统计所有HTML文件）
    - task_count: 任务数量（从 task_index.json 获取）
    - in_progress: 正在进行的任务数量
    - template_count: 报告模板数量（统计 config_files/templates 中 HTML 文件）
    """
    tasks_base = get_tasks_base_path()
    index_path = get_task_index_path()

    # 1. 统计报告数量（所有HTML文件）
    report_count = 0
    if os.path.exists(tasks_base):
        for task_id in os.listdir(tasks_base):
            task_path = os.path.join(tasks_base, task_id)
            if os.path.isdir(task_path):
                reports_path = os.path.join(task_path, "reports")
                if os.path.exists(reports_path):
                    for root, dirs, files in os.walk(reports_path):
                        report_count += len([f for f in files if f.endswith(".html")])

    # 2. 统计任务数量（从 task_index.json）
    task_count = 0
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
                task_count = len(index_data.get("tasks", []))
        except Exception:
            # 如果读取失败，扫描目录获取任务数量
            if os.path.exists(tasks_base):
                for task_id in os.listdir(tasks_base):
                    task_path = os.path.join(tasks_base, task_id)
                    config_file = os.path.join(task_path, "config_files", "task_config.json")
                    if os.path.isdir(task_path) and os.path.exists(config_file):
                        task_count += 1

    # 3. 正在进行的任务数量（从报告生成状态获取）
    in_progress = 0
    try:
        from app.api.endpoints.reports import _task_status
        if _task_status.get("status") == "running":
            in_progress = 1
    except Exception:
        pass

    # 4. 统计报告模板数量（config_files/templates 目录下的 HTML 文件）
    template_count = 0
    templates_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config_files", "templates")
    if os.path.exists(templates_path):
        for root, dirs, files in os.walk(templates_path):
            template_count += len([f for f in files if f.endswith(".html")])

    return DataResponse(
        success=True,
        data={
            "report_count": report_count,
            "task_count": task_count,
            "in_progress": in_progress,
            "template_count": template_count
        }
    )


@router.post("/sync-index", response_model=DataResponse)
async def sync_task_index_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    """
    手动同步 task_index.json

    扫描 report_tasks 目录，将所有任务同步到 task_index.json
    """
    try:
        tasks = sync_task_index()
        return DataResponse(
            success=True,
            message=f"同步完成，共 {len(tasks)} 个任务",
            data={"tasks": tasks, "count": len(tasks)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")