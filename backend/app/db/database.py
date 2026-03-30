"""
数据库连接配置
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from app.core.config import settings
from app.core.logger import app_logger

# 计算数据库文件的绝对路径
# 数据库文件放在 backend/data/ 目录下
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 使用绝对路径创建数据库 URL
DB_PATH = os.path.join(DATA_DIR, "app.db")
DATABASE_URL = f"sqlite:///{DB_PATH.replace(os.sep, '/')}"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 需要此参数
    echo=settings.DEBUG
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表）"""
    from app.db import models  # 导入模型以确保表被创建
    from app.db import crud

    Base.metadata.create_all(bind=engine)

    # 创建默认管理员用户
    db = SessionLocal()
    try:
        admin_user = crud.get_user_by_username(db, "admin")
        if not admin_user:
            admin_user = crud.create_user(
                db,
                username="admin",
                email="admin@example.com",
                password="admin123",
                is_superuser=True
            )
            app_logger.info(f"✅ 默认管理员用户已创建: admin / admin123")
    except Exception as e:
        app_logger.error(f"创建默认管理员用户失败: {e}")
    finally:
        db.close()