"""
认证服务
"""
from typing import Optional
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.config import settings
from app.core.security import create_access_token
from app.core.password import get_password_hash, verify_password
from app.db import crud
from app.db.models import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token


class AuthService:
    """认证服务"""

    @staticmethod
    def register(db: Session, user_data: UserCreate) -> User:
        """用户注册"""
        # 检查用户名是否存在
        if crud.get_user_by_username(db, user_data.username):
            raise ValueError("用户名已存在")

        # 检查邮箱是否存在
        if crud.get_user_by_email(db, user_data.email):
            raise ValueError("邮箱已被注册")

        # 创建用户
        user = crud.create_user(
            db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password
        )
        return user

    @staticmethod
    def login(db: Session, login_data: UserLogin) -> Token:
        """用户登录"""
        user = crud.authenticate_user(db, login_data.username, login_data.password)
        if not user:
            raise ValueError("用户名或密码错误")

        if not user.is_active:
            raise ValueError("用户已被禁用")

        # 创建 Token
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return Token(access_token=access_token)

    @staticmethod
    def get_current_user(db: Session, user_id: int) -> Optional[User]:
        """获取当前用户"""
        return crud.get_user(db, user_id)

    @staticmethod
    def update_password(db: Session, user_id: int, old_password: str, new_password: str) -> User:
        """更新密码"""
        user = crud.get_user(db, user_id)
        if not user:
            raise ValueError("用户不存在")

        if not verify_password(old_password, user.hashed_password):
            raise ValueError("原密码错误")

        user = crud.update_user(db, user_id, hashed_password=get_password_hash(new_password))
        return user