"""
模型配置 API
"""
import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi import Depends
from typing import Optional

from app.core.security import get_current_active_user
from app.schemas.common import ResponseBase, DataResponse
from app.schemas.model_config import ModelConfigResponse, ModelInfoUpdate
from app.core.logger import app_logger

router = APIRouter(prefix="/model-config", tags=["模型配置"])

# 模型配置文件路径
# model_config.py 位于 backend/app/api/endpoints/model_config.py
# 需要往上 4 级才能到达 backend 目录
MODEL_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config_files" / "model" / "model_config.json"


def load_model_config() -> dict:
    """加载模型配置"""
    if not MODEL_CONFIG_PATH.exists():
        raise FileNotFoundError(f"模型配置文件不存在: {MODEL_CONFIG_PATH}")

    with open(MODEL_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_model_config(config: dict) -> None:
    """保存模型配置"""
    # 确保目录存在
    MODEL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 更新最后修改时间
    config["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(MODEL_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


@router.get("", response_model=DataResponse[ModelConfigResponse])
async def get_model_config(current_user=Depends(get_current_active_user)):
    """获取模型配置"""
    try:
        config = load_model_config()
        return DataResponse(
            success=True,
            message="获取模型配置成功",
            data=config
        )
    except FileNotFoundError as e:
        app_logger.error(f"模型配置文件不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型配置文件不存在"
        )
    except Exception as e:
        app_logger.error(f"获取模型配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型配置失败: {str(e)}"
        )


@router.put("", response_model=ResponseBase)
async def update_model_config(
    update_data: dict,
    current_user=Depends(get_current_active_user)
):
    """更新模型配置（完整更新）"""
    try:
        config = load_model_config()

        # 更新配置
        if "default_model_type" in update_data:
            config["default_model_type"] = update_data["default_model_type"]

        if "models" in update_data:
            # 合并模型配置，保留未提供的字段
            for model_type, model_info in update_data["models"].items():
                if model_type in config["models"]:
                    config["models"][model_type].update(model_info)
                else:
                    config["models"][model_type] = model_info

        save_model_config(config)

        return ResponseBase(
            success=True,
            message="模型配置更新成功"
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型配置文件不存在"
        )
    except Exception as e:
        app_logger.error(f"更新模型配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新模型配置失败: {str(e)}"
        )


@router.patch("/model", response_model=ResponseBase)
async def update_single_model(
    update_data: ModelInfoUpdate,
    current_user=Depends(get_current_active_user)
):
    """更新单个模型配置"""
    try:
        config = load_model_config()
        model_type = update_data.model_type

        if model_type not in config["models"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的模型类型: {model_type}"
            )

        # 更新模型配置
        update_dict = update_data.model_dump(exclude_unset=True, exclude={"model_type"})
        for key, value in update_dict.items():
            if value is not None:
                config["models"][model_type][key] = value

        # 如果切换了默认模型类型
        if model_type and config["default_model_type"] != model_type:
            # 可选：自动更新默认模型类型
            pass

        save_model_config(config)

        return ResponseBase(
            success=True,
            message=f"{model_type} 模型配置更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"更新模型配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新模型配置失败: {str(e)}"
        )


@router.put("/default-type", response_model=ResponseBase)
async def set_default_model_type(
    model_type: str,
    current_user=Depends(get_current_active_user)
):
    """设置默认模型类型"""
    try:
        config = load_model_config()

        if model_type not in config["models"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的模型类型: {model_type}"
            )

        config["default_model_type"] = model_type
        save_model_config(config)

        return ResponseBase(
            success=True,
            message=f"默认模型类型已设置为: {model_type}"
        )
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"设置默认模型类型失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"设置默认模型类型失败: {str(e)}"
        )