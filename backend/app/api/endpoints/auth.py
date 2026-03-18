"""
认证 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.core.security import get_current_active_user
from app.schemas.user import UserCreate, UserResponse, Token
from app.schemas.common import ResponseBase, DataResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=DataResponse[UserResponse])
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册"""
    try:
        user = AuthService.register(db, user_data)
        return DataResponse(
            success=True,
            message="注册成功",
            data=UserResponse.model_validate(user)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录（OAuth2 密码流）"""
    from app.schemas.user import UserLogin
    try:
        login_data = UserLogin(username=form_data.username, password=form_data.password)
        token = AuthService.login(db, login_data)
        return token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.get("/me", response_model=DataResponse[UserResponse])
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户信息"""
    return DataResponse(
        success=True,
        data=UserResponse.model_validate(current_user)
    )