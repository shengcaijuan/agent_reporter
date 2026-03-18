"""
报告生成 API
"""
import os
import re
import json
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.db.models import User
from app.schemas.report import (
    ReportGenerateRequest,
    SingleReportRequest,
    BatchGenerateRequest,
    ReportJobResponse,
    BatchJobResponse,
    BatchJobDetail,
    ReportContent,
    GeneratedReportItem,
    GeneratedReportListResponse,
    GenerationStatusResponse,
    OrganizationResponse
)
from app.schemas.common import DataResponse, ListResponse
from app.services.report_service import ReportService

# 导入真正的报告生成服务
from report_service.report_service import BatchReportService as RealBatchReportService
from model import qwen_model

router = APIRouter(prefix="/reports", tags=["报告生成"])

# 报告存储根目录 (backend/report_tasks)
# reports.py 位于 backend/app/api/endpoints/reports.py
# 需要往上 4 级才能到达 backend 目录
REPORT_BASE_DIR = Path(__file__).parent.parent.parent.parent / "report_tasks"

# 全局任务状态存储（简单实现，生产环境应使用 Redis）
_task_status = {
    "status": "idle",
    "task_id": None,
    "task_name": None,  # 新增：任务名称
    "batch_id": None,
    "report_time": None,
    "total": 0,
    "completed": 0,
    "failed": 0,
    "in_progress": 0,
    "paused": 0,  # 新增：暂停的任务数
    "start_time": None,
    "is_paused": False,
    "max_concurrent": 3,  # 新增：并发上限设置
    # 新增：正在处理的销售列表
    "processing_sales": [],
    # 新增：等待处理的销售列表
    "pending_sales": []
}

# 全局后台任务引用（用于取消）
_background_task = None
# 全局运行中的子任务集合（用于强制取消）
_running_tasks = set()
# 任务到销售配置的映射
_task_sales_map = {}


@router.post("/generate", response_model=DataResponse)
async def generate_reports(
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    启动报告生成（支持批量）

    根据筛选条件生成报告，支持：
    - 全部销售人员
    - 按筛选条件（大区/省区/岗位）
    - 指定销售人员列表
    """
    global _task_status

    # 打印请求参数用于调试
    print(f"[DEBUG] 收到生成请求: task_id={request.task_id}, time={request.time}, max_concurrent={request.max_concurrent}")
    print(f"[DEBUG] sale_filter: {request.sale_filter}")

    # 检查是否有正在运行的任务
    if _task_status["status"] == "running":
        raise HTTPException(status_code=400, detail="已有任务正在运行，请等待完成或暂停")

    # 获取销售人员列表
    sales = await _get_filtered_sales(
        request.task_id,
        request.sale_filter
    )

    if not sales:
        raise HTTPException(status_code=400, detail="没有找到符合条件的销售人员")

    total_count = len(sales)

    # 获取任务名称
    task_name = request.task_id  # 默认使用 task_id
    task_config_file = REPORT_BASE_DIR / request.task_id / "config_files" / "task_config.json"
    if task_config_file.exists():
        try:
            with open(task_config_file, "r", encoding="utf-8") as f:
                task_config = json.load(f)
                task_name = task_config.get("task_name", request.task_id)
        except Exception:
            pass

    # 初始化任务状态
    batch_id = f"batch_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    _task_status = {
        "status": "running",
        "task_id": request.task_id,
        "task_name": task_name,  # 新增
        "batch_id": batch_id,
        "report_time": request.time,
        "total": total_count,
        "completed": 0,
        "failed": 0,
        "in_progress": 0,
        "paused": 0,  # 新增：暂停的任务数
        "start_time": datetime.now().isoformat(),
        "is_paused": False,
        "max_concurrent": request.max_concurrent,  # 保存并发上限设置
        # 初始化销售列表
        "processing_sales": [],
        "pending_sales": [
            {
                "job_id": s.get("job_id", ""),
                "sale_name": s.get("sale_name", ""),
                "province": s.get("province", ""),
                "region": s.get("region", ""),
                "stage": "等待中"
            }
            for s in sales
        ]
    }

    # 后台执行生成任务 - 使用 asyncio.create_task 确保异步函数正确执行
    # 注意：BackgroundTasks.add_task 对 async 函数的支持有问题
    print(f"[INFO] 创建后台任务: batch_id={batch_id}", flush=True)
    global _background_task
    _background_task = asyncio.create_task(
        _run_batch_generation(
            request.task_id,
            request.time,
            sales,
            request.max_concurrent,
            batch_id,
            current_user.id
        )
    )
    print(f"[INFO] 后台任务已创建: {_background_task}", flush=True)

    return DataResponse(
        success=True,
        message="报告生成任务已启动",
        data={
            "batch_id": batch_id,
            "task_id": request.task_id,
            "task_name": task_name,
            "report_time": request.time,
            "total_count": total_count,
            "status": "running"
        }
    )


async def _get_filtered_sales(task_id: str, sale_filter) -> List[dict]:
    """根据筛选条件获取销售人员列表"""
    sales_file = REPORT_BASE_DIR / task_id / "config_files" / "sales" / "sales.json"

    if not sales_file.exists():
        return []

    with open(sales_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "sales" in data:
        sales_list = data["sales"]
    elif isinstance(data, list):
        sales_list = data
    else:
        return []

    # 如果没有筛选条件或类型为 all，返回全部
    if not sale_filter or sale_filter.type == "all":
        return sales_list

    filtered = []
    for sale in sales_list:
        # 指定销售人员
        if sale_filter.type == "specific" and sale_filter.job_ids:
            if sale.get("job_id") in sale_filter.job_ids:
                filtered.append(sale)
        # 使用筛选条件
        elif sale_filter.type == "filter":
            match = True
            if sale_filter.region and sale.get("region") != sale_filter.region:
                match = False
            if sale_filter.province and sale.get("province") != sale_filter.province:
                match = False
            if sale_filter.sale_class and sale.get("sale_class") != sale_filter.sale_class:
                match = False
            if match:
                filtered.append(sale)

    return filtered


async def _run_batch_generation(
    task_id: str,
    report_time: str,
    sales: List[dict],
    max_concurrent: int,
    batch_id: str,
    user_id: int
):
    """后台批量生成任务 - 支持强制暂停和恢复"""
    global _task_status, _running_tasks, _task_sales_map

    # 添加启动日志
    print(f"[INFO] 后台任务启动: task_id={task_id}, sales_count={len(sales)}, batch_id={batch_id}", flush=True)
    print(f"[INFO] 第一个销售: {sales[0] if sales else 'None'}", flush=True)

    async def generate_single_with_tracking(sale_config: dict):
        """生成单个报告并跟踪状态"""
        global _task_status

        sale_name = sale_config.get("sale_name", "")
        job_id = sale_config.get("job_id", "")
        print(f"[INFO] 开始生成报告: {sale_name} ({job_id})", flush=True)

        # 先从等待队列移除
        _task_status["pending_sales"] = [
            s for s in _task_status["pending_sales"]
            if s.get("job_id") != job_id
        ]

        sale_info = {
            "job_id": job_id,
            "sale_name": sale_name,
            "province": sale_config.get("province", ""),
            "region": sale_config.get("region", ""),
            "stage": "生成中"
        }

        # 添加到正在处理列表
        _task_status["processing_sales"].append(sale_info)
        _task_status["in_progress"] = len(_task_status["processing_sales"])

        try:
            # 创建报告服务实例
            print(f"[INFO] 创建 ReportService: {sale_name}", flush=True)
            from report_service.report_service import ReportService as SingleReportService
            service = SingleReportService(
                task_id=task_id,
                time=report_time,
                sale_config=sale_config
            )
            print(f"[INFO] ReportService 创建成功，开始生成: {sale_name}", flush=True)
            result = await service.generate_report()
            print(f"[INFO] 报告生成完成: {sale_name}, success={result.get('success')}", flush=True)

            # 从正在处理列表中移除
            _task_status["processing_sales"] = [
                s for s in _task_status["processing_sales"]
                if s["job_id"] != sale_info["job_id"]
            ]
            _task_status["in_progress"] = len(_task_status["processing_sales"])

            if result.get("success"):
                _task_status["completed"] += 1
            else:
                _task_status["failed"] += 1

            return result

        except asyncio.CancelledError:
            # 任务被取消，将销售重新加入待处理队列
            print(f"[INFO] 任务被取消: {sale_name}", flush=True)
            _task_status["processing_sales"] = [
                s for s in _task_status["processing_sales"]
                if s["job_id"] != sale_info["job_id"]
            ]
            _task_status["in_progress"] = len(_task_status["processing_sales"])
            # 重新加入 pending_sales
            already_pending = any(
                s.get("job_id") == job_id
                for s in _task_status["pending_sales"]
            )
            if not already_pending:
                _task_status["pending_sales"].append({
                    "job_id": job_id,
                    "sale_name": sale_name,
                    "province": sale_config.get("province", ""),
                    "region": sale_config.get("region", ""),
                    "stage": "等待中"
                })
            raise  # 重新抛出 CancelledError

        except Exception as e:
            import traceback
            print(f"[ERROR] 报告生成失败: {sale_name}, 错误: {e}", flush=True)
            print(f"[ERROR] 错误堆栈:\n{traceback.format_exc()}", flush=True)
            # 出错时也要从正在处理列表中移除
            _task_status["processing_sales"] = [
                s for s in _task_status["processing_sales"]
                if s["job_id"] != sale_info["job_id"]
            ]
            _task_status["in_progress"] = len(_task_status["processing_sales"])
            _task_status["failed"] += 1
            return {"success": False, "error": str(e)}

    try:
        print(f"[INFO] 开始创建 BatchReportService: task_id={task_id}", flush=True)
        # 创建真正的批量报告服务
        batch_service = RealBatchReportService(
            task_id=task_id,
            time=report_time,
            model=qwen_model
        )
        print(f"[INFO] BatchReportService 创建成功", flush=True)

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)
        print(f"[INFO] 开始创建报告生成任务，并发限制: {max_concurrent}", flush=True)

        async def process_with_semaphore(sale_config: dict):
            async with semaphore:
                # 检查是否已暂停 - 如果暂停则跳过，保留在 pending 中
                if _task_status["is_paused"]:
                    print(f"[INFO] 任务已暂停，跳过: {sale_config.get('sale_name')}", flush=True)
                    return {"success": False, "reason": "paused", "skipped": True}
                return await generate_single_with_tracking(sale_config)

        # 清空全局任务集合
        _running_tasks.clear()
        _task_sales_map.clear()

        # 创建任务迭代器
        pending_iter = iter(sales)

        # 初始启动 max_concurrent 个任务
        for _ in range(min(max_concurrent, len(sales))):
            try:
                sale = next(pending_iter)
                task = asyncio.create_task(process_with_semaphore(sale))
                _running_tasks.add(task)
                _task_sales_map[task] = sale
            except StopIteration:
                break

        print(f"[INFO] 初始启动 {len(_running_tasks)} 个任务", flush=True)

        # 持续处理任务，直到全部完成或暂停
        while _running_tasks:
            # 等待任意一个任务完成
            done, _running_tasks = await asyncio.wait(
                _running_tasks,
                return_when=asyncio.FIRST_COMPLETED
            )

            # 处理完成的任务
            for task in done:
                sale_config = _task_sales_map.pop(task, {})
                try:
                    result = task.result()
                    # 如果是因为暂停而跳过的任务，需要重新加入 pending
                    if result and result.get("skipped"):
                        job_id = sale_config.get("job_id", "")
                        # 确保这个销售还在 pending_sales 中
                        already_pending = any(
                            s.get("job_id") == job_id
                            for s in _task_status["pending_sales"]
                        )
                        if not already_pending:
                            _task_status["pending_sales"].append({
                                "job_id": job_id,
                                "sale_name": sale_config.get("sale_name", ""),
                                "province": sale_config.get("province", ""),
                                "region": sale_config.get("region", ""),
                                "stage": "等待中"
                            })
                except asyncio.CancelledError:
                    # 任务被取消，已在 generate_single_with_tracking 中处理
                    print(f"[INFO] 任务已被取消: {sale_config.get('sale_name')}", flush=True)
                except Exception as e:
                    print(f"[ERROR] 任务执行异常: {e}", flush=True)

            # 检查是否暂停
            if _task_status["is_paused"]:
                print(f"[INFO] 检测到暂停信号，停止启动新任务", flush=True)
                break

            # 启动新任务填补空位
            while len(_running_tasks) < max_concurrent:
                # 再次检查暂停（防止在填充过程中被暂停）
                if _task_status["is_paused"]:
                    break
                try:
                    sale = next(pending_iter)
                    task = asyncio.create_task(process_with_semaphore(sale))
                    _running_tasks.add(task)
                    _task_sales_map[task] = sale
                except StopIteration:
                    # 没有更多销售需要处理
                    break

        # 最终状态更新
        if not _task_status["is_paused"]:
            # 正常完成
            _task_status["status"] = "completed"
            _task_status["processing_sales"] = []
            _task_status["pending_sales"] = []
            _task_status["in_progress"] = 0
            print(f"[INFO] 所有任务已完成", flush=True)
        else:
            # 暂停完成
            _task_status["status"] = "paused"
            _task_status["in_progress"] = 0
            print(f"[INFO] 任务已暂停，剩余 {len(_task_status['pending_sales'])} 个销售待处理", flush=True)

    except asyncio.CancelledError:
        # 整个批量任务被取消
        print(f"[INFO] 批量任务被取消", flush=True)
        _task_status["status"] = "paused"
        _task_status["in_progress"] = 0
        # 确保所有正在处理的销售都回到 pending
        for sale_info in _task_status["processing_sales"]:
            already_pending = any(
                s.get("job_id") == sale_info.get("job_id")
                for s in _task_status["pending_sales"]
            )
            if not already_pending:
                _task_status["pending_sales"].append({
                    **sale_info,
                    "stage": "等待中"
                })
        _task_status["processing_sales"] = []
        print(f"[INFO] 任务已强制暂停，剩余 {len(_task_status['pending_sales'])} 个销售待处理", flush=True)

    except Exception as e:
        # 发生错误时更新状态
        import traceback
        _task_status["status"] = "failed"
        _task_status["failed"] = _task_status["total"] - _task_status["completed"]
        _task_status["processing_sales"] = []
        _task_status["in_progress"] = 0
        print(f"[ERROR] 批量生成失败: {e}", flush=True)
        print(f"[ERROR] 错误堆栈:\n{traceback.format_exc()}", flush=True)


@router.post("/resume", response_model=DataResponse)
async def resume_generation(
    current_user: User = Depends(get_current_active_user)
):
    """从中断处恢复生成 - 从 pending_sales 继续"""
    global _task_status, _background_task

    if _task_status["status"] != "paused":
        raise HTTPException(status_code=400, detail="没有已暂停的任务")

    # 获取待处理的销售
    pending_sales = _task_status.get("pending_sales", [])
    if not pending_sales:
        # 没有待处理的销售，直接标记完成
        _task_status["status"] = "completed"
        return DataResponse(
            success=True,
            message="没有待处理的任务",
            data={
                "batch_id": _task_status["batch_id"],
                "task_id": _task_status["task_id"],
                "total_count": _task_status["total"],
                "completed": _task_status["completed"]
            }
        )

    # 转换 pending_sales 格式（从 dict 转回 sale_config 格式）
    sales_to_process = []
    for s in pending_sales:
        sales_to_process.append({
            "job_id": s.get("job_id", ""),
            "sale_name": s.get("sale_name", ""),
            "province": s.get("province", ""),
            "region": s.get("region", "")
        })

    # 更新状态
    _task_status["status"] = "running"
    _task_status["is_paused"] = False
    _task_status["in_progress"] = 0
    _task_status["paused"] = 0  # 重置暂停数量
    _task_status["processing_sales"] = []  # 清空暂停中的销售

    # 重新计算 total（剩余待处理 + 已完成 + 失败）
    remaining_count = len(sales_to_process)

    print(f"[INFO] 恢复任务: batch_id={_task_status['batch_id']}, 剩余 {remaining_count} 个销售待处理", flush=True)

    # 获取保存的并发上限设置
    max_concurrent = _task_status.get("max_concurrent", 3)
    print(f"[INFO] 使用并发上限: {max_concurrent}", flush=True)

    # 启动后台任务继续处理
    _background_task = asyncio.create_task(
        _run_batch_generation(
            _task_status["task_id"],
            _task_status["report_time"],
            sales_to_process,
            max_concurrent,  # 使用保存的并发上限
            _task_status["batch_id"],
            current_user.id
        )
    )

    return DataResponse(
        success=True,
        message=f"任务已恢复，剩余 {remaining_count} 个销售待处理",
        data={
            "batch_id": _task_status["batch_id"],
            "task_id": _task_status["task_id"],
            "total_count": _task_status["total"],
            "completed": _task_status["completed"],
            "remaining": remaining_count
        }
    )


@router.post("/clear", response_model=DataResponse)
async def clear_generation_status(
    current_user: User = Depends(get_current_active_user)
):
    """清除当前任务状态"""
    global _task_status, _running_tasks, _background_task

    # 如果有正在运行的任务，不允许清除
    if _task_status["status"] == "running":
        raise HTTPException(status_code=400, detail="有任务正在运行，请先暂停或等待完成")

    # 取消后台任务（如果有）
    if _background_task and not _background_task.done():
        _background_task.cancel()

    # 清空运行中的任务集合
    _running_tasks.clear()

    # 重置状态
    _task_status = {
        "status": "idle",
        "task_id": None,
        "task_name": None,
        "batch_id": None,
        "report_time": None,
        "total": 0,
        "completed": 0,
        "failed": 0,
        "in_progress": 0,
        "paused": 0,
        "start_time": None,
        "is_paused": False,
        "max_concurrent": 3,
        "processing_sales": [],
        "pending_sales": []
    }

    return DataResponse(
        success=True,
        message="任务状态已清除"
    )


@router.post("/pause", response_model=DataResponse)
async def pause_generation(
    current_user: User = Depends(get_current_active_user)
):
    """暂停当前任务 - 强制取消所有运行中的任务"""
    global _task_status, _running_tasks, _background_task

    if _task_status["status"] != "running":
        raise HTTPException(status_code=400, detail="没有正在运行的任务")

    # 获取当前正在处理的数量
    in_progress = _task_status.get("in_progress", 0)

    # 设置暂停标志
    _task_status["is_paused"] = True

    # 强制取消所有运行中的任务
    cancelled_count = 0
    for task in list(_running_tasks):
        if not task.done():
            task.cancel()
            cancelled_count += 1

    print(f"[INFO] 已取消 {cancelled_count} 个运行中的任务", flush=True)

    # 更新暂停数量和销售状态
    _task_status["paused"] = in_progress
    _task_status["in_progress"] = 0

    # 将正在处理的销售状态改为"暂停中"
    for sale in _task_status["processing_sales"]:
        sale["stage"] = "暂停中"

    return DataResponse(
        success=True,
        message=f"已强制暂停任务，取消了 {cancelled_count} 个正在进行的任务",
        data={
            "batch_id": _task_status["batch_id"],
            "completed": _task_status["completed"],
            "total": _task_status["total"],
            "cancelled": cancelled_count,
            "paused": _task_status["paused"],
            "pending": len(_task_status.get("pending_sales", []))
        }
    )


@router.get("/status", response_model=DataResponse[GenerationStatusResponse])
async def get_generation_status(
    current_user: User = Depends(get_current_active_user)
):
    """获取当前生成任务状态"""
    global _task_status

    from app.schemas.report import SaleProgressItem

    # 转换销售列表
    processing_sales = [
        SaleProgressItem(**s) for s in _task_status.get("processing_sales", [])
    ]
    pending_sales = [
        SaleProgressItem(**s) for s in _task_status.get("pending_sales", [])
    ]

    return DataResponse(
        success=True,
        data=GenerationStatusResponse(
            batch_id=_task_status.get("batch_id"),
            task_id=_task_status.get("task_id") or "",
            task_name=_task_status.get("task_name"),
            status=_task_status.get("status", "idle"),
            total=_task_status.get("total", 0),
            completed=_task_status.get("completed", 0),
            failed=_task_status.get("failed", 0),
            in_progress=_task_status.get("in_progress", 0),
            paused=_task_status.get("paused", 0),
            start_time=_task_status.get("start_time"),
            report_time=_task_status.get("report_time"),
            processing_sales=processing_sales,
            pending_sales=pending_sales
        )
    )


@router.get("/sales", response_model=DataResponse)
async def get_sales_list(
    task_id: str = Query(..., description="任务 ID"),
    region: Optional[str] = Query(None, description="大区筛选"),
    province: Optional[str] = Query(None, description="省区筛选"),
    sale_class: Optional[str] = Query(None, description="岗位筛选"),
    search: Optional[str] = Query(None, description="搜索关键字"),
    current_user: User = Depends(get_current_active_user)
):
    """获取销售人员列表"""
    sales_file = REPORT_BASE_DIR / task_id / "config_files" / "sales" / "sales.json"

    if not sales_file.exists():
        raise HTTPException(status_code=404, detail="销售人员数据不存在")

    with open(sales_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "sales" in data:
        sales_list = data["sales"]
    elif isinstance(data, list):
        sales_list = data
    else:
        sales_list = []

    # 应用筛选
    filtered = []
    for sale in sales_list:
        if region and sale.get("region") != region:
            continue
        if province and sale.get("province") != province:
            continue
        if sale_class and sale.get("sale_class") != sale_class:
            continue
        if search:
            search_lower = search.lower()
            if (search_lower not in sale.get("sale_name", "").lower() and
                search_lower not in sale.get("job_id", "").lower()):
                continue
        filtered.append(sale)

    # 提取筛选选项
    regions = sorted(list(set(s.get("region", "") for s in sales_list if s.get("region"))))
    provinces = sorted(list(set(s.get("province", "") for s in sales_list if s.get("province"))))
    sale_classes = sorted(list(set(s.get("sale_class", "") for s in sales_list if s.get("sale_class"))))

    return DataResponse(
        success=True,
        data={
            "total": len(sales_list),
            "filtered_count": len(filtered),
            "filters": {
                "regions": regions,
                "provinces": provinces,
                "sale_classes": sale_classes
            },
            "sales": filtered
        }
    )


@router.get("/organization", response_model=DataResponse[OrganizationResponse])
async def get_organization(
    task_id: str = Query(..., description="任务 ID"),
    current_user: User = Depends(get_current_active_user)
):
    """获取组织架构"""
    sales_file = REPORT_BASE_DIR / task_id / "config_files" / "sales" / "sales.json"

    if not sales_file.exists():
        raise HTTPException(status_code=404, detail="销售人员数据不存在")

    with open(sales_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "sales" in data:
        sales_list = data["sales"]
    elif isinstance(data, list):
        sales_list = data
    else:
        sales_list = []

    # 提取组织架构信息
    regions = sorted(list(set(s.get("region", "") for s in sales_list if s.get("region"))))
    provinces = sorted(list(set(s.get("province", "") for s in sales_list if s.get("province"))))
    sale_classes = sorted(list(set(s.get("sale_class", "") for s in sales_list if s.get("sale_class"))))

    return DataResponse(
        success=True,
        data=OrganizationResponse(
            regions=regions,
            provinces=provinces,
            sale_classes=sale_classes
        )
    )


@router.post("/batch", response_model=DataResponse[BatchJobResponse])
async def generate_batch_reports(
    request: BatchGenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """批量生成报告"""
    service = ReportService(db)

    try:
        batch = await service.generate_batch_reports(request, user_id=current_user.id)
        return DataResponse(
            success=True,
            message="批量报告生成任务已创建",
            data=BatchJobResponse.model_validate(batch)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}/status", response_model=DataResponse[ReportJobResponse])
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """查询报告生成任务状态"""
    service = ReportService(db)
    job = service.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    return DataResponse(
        success=True,
        data=ReportJobResponse.model_validate(job)
    )


@router.get("/batch/{batch_id}/status", response_model=DataResponse[BatchJobDetail])
async def get_batch_status(
    batch_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """查询批量任务状态"""
    service = ReportService(db)
    batch = service.get_batch_status(batch_id)

    if not batch:
        raise HTTPException(status_code=404, detail="批量任务不存在")

    # 获取关联的报告任务
    from app.db import crud
    jobs = db.query(crud.ReportJob).filter(crud.ReportJob.batch_id == batch_id).all()

    batch_detail = BatchJobDetail(
        batch_id=batch.batch_id,
        task_id=batch.task_id,
        report_time=batch.report_time,
        total_count=batch.total_count,
        completed_count=batch.completed_count,
        failed_count=batch.failed_count,
        status=batch.status,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        jobs=[ReportJobResponse.model_validate(job) for job in jobs]
    )

    return DataResponse(
        success=True,
        data=batch_detail
    )


@router.get("/available-times", response_model=DataResponse)
async def get_available_report_times(
    task_id: str = Query("mashangzhu", description="报告任务 ID"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取可用的报告月份列表

    从 report_tasks/{task_id}/reports/ 目录读取所有子文件夹名称作为可选月份

    Args:
        task_id: 报告任务 ID，如 mashangzhu

    Returns:
        可用月份列表，如 ["202601", "202512", "202511"]
    """
    # 构建报告根目录
    reports_dir = REPORT_BASE_DIR / task_id / "reports"

    if not reports_dir.exists():
        return DataResponse(
            success=True,
            data={"times": []}
        )

    # 获取所有子目录，过滤出符合月份格式的目录名
    times = []
    for item in reports_dir.iterdir():
        if item.is_dir():
            # 检查目录名是否符合 YYYYMM 格式
            dir_name = item.name
            if re.match(r'^\d{6}$', dir_name):
                times.append(dir_name)

    # 按时间倒序排列（最新的在前）
    times.sort(reverse=True)

    return DataResponse(
        success=True,
        data={"times": times}
    )


@router.get("/logs")
async def get_report_logs(
    file_path: str = Query(..., description="报告文件路径（用于定位销售文件夹）"),
    task_id: str = Query("mashangzhu", description="报告任务 ID"),
    report_time: str = Query(..., description="报告月份，如 202601"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取报告生成的日志文件内容

    根据 file_path 定位销售文件夹，查找日志文件：
    - 如果存在 progress_report 目录，读取其中所有 .log 文件（最多7个窗口）
    - 否则读取销售文件夹根目录下的 function_calling.log（单个窗口）

    Args:
        file_path: 报告 HTML 文件的完整路径
        task_id: 报告任务 ID
        report_time: 报告月份

    Returns:
        logs: 日志文件列表，每个包含 {name, content}
    """
    # 构建报告根目录
    report_dir = REPORT_BASE_DIR / task_id / "reports" / report_time
    report_dir_resolved = report_dir.resolve()

    # 解析目标路径
    try:
        target_path = Path(file_path).resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的文件路径")

    # 安全检查：确保文件在报告目录内
    if not str(target_path).startswith(str(report_dir_resolved)):
        raise HTTPException(status_code=403, detail="非法文件路径")

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")

    # 找到销售文件夹（HTML 文件的父目录）
    sale_folder = target_path.parent
    sale_name = sale_folder.name

    logs = []

    # 检查是否存在 progress_report 目录
    progress_report_dir = sale_folder / "progress_report"

    if progress_report_dir.exists() and progress_report_dir.is_dir():
        # 有 progress_report 目录，读取所有 .log 文件
        log_files = sorted(progress_report_dir.glob("*.log"))

        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    content = f.read()
                logs.append({
                    "name": log_file.name,
                    "content": content
                })
            except Exception as e:
                logs.append({
                    "name": log_file.name,
                    "content": f"读取日志失败: {str(e)}"
                })
    else:
        # 没有 progress_report 目录，读取 function_calling.log
        function_calling_log = sale_folder / "function_calling.log"

        if function_calling_log.exists():
            try:
                with open(function_calling_log, "r", encoding="utf-8") as f:
                    content = f.read()
                logs.append({
                    "name": "function_calling.log",
                    "content": content
                })
            except Exception as e:
                logs.append({
                    "name": "function_calling.log",
                    "content": f"读取日志失败: {str(e)}"
                })
        else:
            logs.append({
                "name": "无日志文件",
                "content": "未找到任何日志文件"
            })

    return {
        "success": True,
        "data": {
            "sale_name": sale_name,
            "logs": logs
        }
    }


@router.get("/{job_id}", response_model=DataResponse[ReportContent])
async def get_report_content(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取生成的报告内容"""
    service = ReportService(db)
    job = service.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="报告不存在")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="报告尚未生成完成")

    if not job.report_path or not os.path.exists(job.report_path):
        raise HTTPException(status_code=404, detail="报告文件不存在")

    # 读取报告内容
    with open(job.report_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 尝试读取 HTML 版本
    html_content = None
    html_path = job.report_path.replace(".md", ".html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

    report_content = ReportContent(
        job_id=job.job_id,
        sale_id=job.sale_id,
        sale_name=job.sale_name,
        report_time=job.report_time,
        content=content,
        html_content=html_content,
        created_at=job.created_at
    )

    return DataResponse(
        success=True,
        data=report_content
    )


@router.get("", response_model=ListResponse[ReportJobResponse])
async def list_reports(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取已生成的报告列表"""
    service = ReportService(db)
    jobs = service.list_user_reports(current_user.id, skip, limit)

    return ListResponse(
        success=True,
        data=[ReportJobResponse.model_validate(job) for job in jobs],
        total=len(jobs)
    )


@router.get("/generated/list", response_model=DataResponse[GeneratedReportListResponse])
async def list_generated_reports(
    task_id: str = Query("mashangzhu", description="报告任务 ID"),
    report_time: str = Query(None, description="报告月份，如 202512"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取已生成的HTML报告列表（从文件系统读取）

    目录结构:
    report_tasks/{task_id}/reports/{time}/{region}/{province}/{city_operation_department}/{sale_name}/*.html

    Args:
        task_id: 报告任务 ID，如 mashangzhu
        report_time: 报告月份，如 202512
    """
    # 默认使用 202512
    if not report_time:
        report_time = "202512"

    # 构建报告目录路径
    report_dir = REPORT_BASE_DIR / task_id / "reports" / report_time

    if not report_dir.exists():
        return DataResponse(
            success=True,
            data=GeneratedReportListResponse(reports=[], total=0)
        )

    # 加载销售人员数据用于匹配工号
    sales_data = _load_sales_data(task_id)

    # 遍历目录获取所有 HTML 报告
    reports = []
    for html_file in report_dir.rglob("*.html"):
        # 从路径中提取组织架构信息
        # 实际路径格式: .../{time}/{business_department}/{region}/{province}/{city_operation_department}/{sale_name}/{filename}.html
        relative_path = html_file.relative_to(report_dir)
        parts = relative_path.parts

        if len(parts) >= 6:
            # 标准深层目录结构
            business_department = parts[0]  # 事业部
            region = parts[1]  # 大区
            province = parts[2]  # 省区
            city_operation_department = parts[3]  # 城市经营部/分部
            sale_name = parts[4]  # 销售姓名
        elif len(parts) == 2:
            # 扁平结构（旧格式）：{sale_name}/{filename}.html
            business_department = _get_business_department_name(task_id)
            region = None
            province = None
            city_operation_department = None
            sale_name = parts[0]
        else:
            # 单层结构：{filename}.html
            business_department = _get_business_department_name(task_id)
            region = None
            province = None
            city_operation_department = None
            # 从文件名解析销售姓名
            sale_name = _extract_sale_name_from_filename(html_file.name)

        # 匹配工号
        job_id = None
        if sale_name and sale_name in sales_data:
            job_id = sales_data[sale_name].get("job_id")

        reports.append(GeneratedReportItem(
            filename=html_file.name,
            sale_name=sale_name or "",
            job_id=job_id,
            report_time=report_time,
            business_department=business_department,
            region=region,
            province=province,
            city_operation_department=city_operation_department,
            file_path=str(html_file.resolve())  # 返回绝对路径
        ))

    # 按销售姓名排序
    reports.sort(key=lambda x: x.sale_name)

    return DataResponse(
        success=True,
        data=GeneratedReportListResponse(reports=reports, total=len(reports))
    )


def _load_sales_data(task_id: str) -> dict:
    """加载销售人员数据，返回 {sale_name: sale_info} 映射"""
    sales_file = REPORT_BASE_DIR / task_id / "config_files" / "sales" / "sales.json"

    if not sales_file.exists():
        return {}

    try:
        with open(sales_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "sales" in data:
            sales_list = data["sales"]
        elif isinstance(data, list):
            sales_list = data
        else:
            return {}

        # 构建 name -> info 映射
        return {sale.get("sale_name"): sale for sale in sales_list if sale.get("sale_name")}
    except Exception:
        return {}


def _extract_sale_name_from_filename(filename: str) -> str:
    """从文件名中提取销售姓名
    文件名格式：{sale_name}_{timestamp}.html，如：郭雷_20260131_150704.html
    """
    import re
    match = re.match(r'^(.+?)_\d{8}_\d{6}\.html$', filename)
    if match:
        return match.group(1)
    # 如果不匹配，尝试去掉扩展名
    return filename.replace('.html', '')


def _get_business_department_name(task_id: str) -> str:
    """根据 task_id 获取事业部名称"""
    # 可以从配置文件读取，这里先硬编码
    department_map = {
        "mashangzhu": "马上住焕新事业部"
    }
    return department_map.get(task_id, task_id)


@router.get("/generated/content")
async def get_generated_report_content(
    filename: str = Query(None, description="文件名（用于扁平目录）"),
    file_path: str = Query(None, description="完整文件路径（用于深层目录）"),
    task_id: str = Query("mashangzhu", description="报告任务 ID"),
    report_time: str = Query(None, description="报告月份，如 202512"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取已生成的HTML报告内容

    Args:
        filename: 文件名（用于扁平目录结构）
        file_path: 完整文件路径（用于深层目录结构）
        task_id: 报告任务 ID
        report_time: 报告月份，如 202512
    """
    # 默认使用 202512
    if not report_time:
        report_time = "202512"

    # 构建报告根目录
    report_dir = REPORT_BASE_DIR / task_id / "reports" / report_time

    # 确定文件路径
    if file_path:
        # 使用完整路径（前端传递）
        target_path = Path(file_path)
    elif filename:
        # 使用文件名，在报告目录中搜索
        target_path = None
        for html_file in report_dir.rglob(filename):
            target_path = html_file
            break
        if not target_path:
            raise HTTPException(status_code=404, detail="报告文件不存在")
    else:
        raise HTTPException(status_code=400, detail="需要提供 filename 或 file_path 参数")

    # 安全检查：确保文件在报告目录内
    try:
        target_path = target_path.resolve()
        report_dir_resolved = report_dir.resolve()
        if not str(target_path).startswith(str(report_dir_resolved)):
            raise HTTPException(status_code=403, detail="非法文件路径")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="无效的文件路径")

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")

    # 读取HTML内容
    with open(target_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return {
        "success": True,
        "data": {
            "filename": target_path.name,
            "html_content": html_content
        }
    }


@router.delete("/generated/delete")
async def delete_generated_report(
    file_path: str = Query(..., description="要删除的报告文件夹路径"),
    task_id: str = Query("mashangzhu", description="报告任务 ID"),
    report_time: str = Query(..., description="报告月份，如 202512"),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除指定的报告（包括整个销售文件夹）

    根据传入的 file_path，删除对应的销售文件夹（{sale_name}/ 目录）

    Args:
        file_path: 报告文件的完整路径，用于定位销售文件夹
        task_id: 报告任务 ID
        report_time: 报告月份

    Returns:
        删除结果
    """
    import shutil

    # 构建报告根目录
    report_dir = REPORT_BASE_DIR / task_id / "reports" / report_time

    # 解析目标路径
    try:
        target_path = Path(file_path).resolve()
        report_dir_resolved = report_dir.resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的文件路径")

    # 安全检查：确保文件在报告目录内
    if not str(target_path).startswith(str(report_dir_resolved)):
        raise HTTPException(status_code=403, detail="非法文件路径")

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")

    # 找到销售文件夹（{sale_name}/ 目录）
    # 路径格式: .../{report_time}/{business_department}/{region}/{province}/{city_operation_department}/{sale_name}/{filename}.html
    # 或扁平格式: .../{report_time}/{sale_name}/{filename}.html
    relative_path = target_path.relative_to(report_dir_resolved)
    parts = relative_path.parts

    # 确定销售文件夹路径
    if len(parts) >= 2:
        # 有层级结构，销售文件夹是倒数第二层（HTML文件的父目录）
        sale_folder = target_path.parent
    else:
        # 只有文件，无法确定销售文件夹，直接删除文件
        sale_folder = target_path

    # 获取销售姓名（用于返回信息）
    sale_name = sale_folder.name

    # 检查是否是销售文件夹（包含 HTML 文件的目录）
    if sale_folder.is_dir():
        # 删除整个销售文件夹
        shutil.rmtree(sale_folder)
        deleted_type = "folder"
    else:
        # 删除单个文件
        sale_folder.unlink()
        deleted_type = "file"

    return {
        "success": True,
        "message": f"已删除销售【{sale_name}】的报告",
        "data": {
            "deleted_path": str(sale_folder),
            "deleted_type": deleted_type,
            "sale_name": sale_name
        }
    }


@router.post("/generated/batch-delete")
async def batch_delete_generated_reports(
    request: dict,
    current_user: User = Depends(get_current_active_user)
):
    """
    批量删除报告（包括整个销售文件夹）

    请求体:
        {
            "file_paths": ["path1", "path2", ...],
            "task_id": "mashangzhu",
            "report_time": "202601"
        }

    Returns:
        删除结果，包含成功和失败的列表
    """
    import shutil

    file_paths = request.get("file_paths", [])
    task_id = request.get("task_id", "mashangzhu")
    report_time = request.get("report_time")

    if not file_paths:
        raise HTTPException(status_code=400, detail="未提供要删除的文件路径")

    if not report_time:
        raise HTTPException(status_code=400, detail="未提供报告月份")

    # 构建报告根目录
    report_dir = REPORT_BASE_DIR / task_id / "reports" / report_time
    report_dir_resolved = report_dir.resolve()

    deleted_sales = []
    failed_items = []

    for file_path in file_paths:
        try:
            target_path = Path(file_path).resolve()

            # 安全检查：确保文件在报告目录内
            if not str(target_path).startswith(str(report_dir_resolved)):
                failed_items.append({
                    "file_path": file_path,
                    "reason": "非法文件路径"
                })
                continue

            if not target_path.exists():
                failed_items.append({
                    "file_path": file_path,
                    "reason": "文件不存在"
                })
                continue

            # 确定销售文件夹路径
            relative_path = target_path.relative_to(report_dir_resolved)
            parts = relative_path.parts

            if len(parts) >= 2:
                sale_folder = target_path.parent
            else:
                sale_folder = target_path

            sale_name = sale_folder.name

            # 删除文件夹或文件
            if sale_folder.is_dir():
                shutil.rmtree(sale_folder)
            else:
                sale_folder.unlink()

            deleted_sales.append(sale_name)

        except Exception as e:
            failed_items.append({
                "file_path": file_path,
                "reason": str(e)
            })

    # 构建返回消息
    if deleted_sales and not failed_items:
        message = f"成功删除 {len(deleted_sales)} 份报告"
    elif deleted_sales and failed_items:
        message = f"成功删除 {len(deleted_sales)} 份报告，{len(failed_items)} 份删除失败"
    else:
        message = "删除失败"

    return {
        "success": len(deleted_sales) > 0,
        "message": message,
        "data": {
            "deleted_count": len(deleted_sales),
            "deleted_sales": deleted_sales,
            "failed_count": len(failed_items),
            "failed_items": failed_items
        }
    }