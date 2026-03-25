"""
数据库配置和会话管理
仅支持PostgreSQL数据库
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text
from sqlalchemy.orm import declarative_base
from core.config import settings
from core.logger import logger

# 创建异步引擎 - PostgreSQL 专用配置
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

# 创建异步会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# 声明基类
Base = declarative_base()
_models_imported = False


def import_all_models():
    """
    导入所有模型，确保它们被注册到 Base.metadata
    这个函数必须在 Base.metadata.create_all 之前调用，
    否则 SQLAlchemy 无法识别外键引用的表。
    """
    global _models_imported

    if _models_imported:
        return

    # 导入所有模型（顺序很重要：先导入被依赖的表）
    # 1. 用户表（被多个表引用）
    from user.models import User  # noqa: F401

    # 2. 项目表（被测试计划、执行记录等引用）
    from project.models import Project, ProjectMember  # noqa: F401

    # 3. 测试用例相关表
    from testcase.models import TestCase, TestSuite  # noqa: F401

    # 4. 测试计划相关表
    from plan.models import TestPlan, ExecutionRecord, ExecutionResult  # noqa: F401

    # 5. 统计表
    from stats.models import DailyStats  # noqa: F401
    _models_imported = True
    logger.debug("所有模型已导入并注册到 Base.metadata")

async def init_db():
    """初始化数据库连接"""
    # 隐藏密码显示连接信息（用于日志输出）
    db_url_display = _mask_password(settings.DATABASE_URL)
    # db_url_display = settings.DATABASE_URL
    logger.info(f"正在连接 PostgreSQL 数据库: {db_url_display}")
    max_attempts = 20
    retry_delay = 3

    for attempt in range(1, max_attempts + 1):
        try:
            # 测试连接
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            import_all_models()

            # 创建所有表
            # 创建所有表（使用 PostgreSQL advisory lock 避免多副本并发初始化导致 DDL 竞争）
            async with engine.connect() as conn:
                lock_id = _schema_init_lock_id(settings.DATABASE_NAME)
                lock_acquired = False
                try:
                    await conn.execute(
                        text("SELECT pg_advisory_lock(:lock_id)"),
                        {"lock_id": lock_id},
                    )
                    lock_acquired = True
                    await conn.run_sync(Base.metadata.create_all)
                    await conn.commit()
                finally:
                    if lock_acquired:
                        await conn.execute(
                            text("SELECT pg_advisory_unlock(:lock_id)"),
                            {"lock_id": lock_id},
                        )
                        await conn.commit()

            logger.info(f"PostgreSQL 数据库连接成功: {db_url_display}")
            return
        except Exception as e:
            if attempt == max_attempts:
                logger.error(f"数据库连接失败: {db_url_display}")
                logger.error(f"错误详情: {e}")
                raise

            logger.warning(
                f"第 {attempt}/{max_attempts} 次连接数据库失败，"
                f"{retry_delay} 秒后重试: {e}"
            )
            await asyncio.sleep(retry_delay)


def _mask_password(url: str) -> str:
    """
    隐藏数据库URL中的密码信息
    Args:
        url: 数据库连接URL
    Returns:
        隐藏密码后的URL，格式如: postgresql+asyncpg://user:***@host:port/db
    """
    if '@' not in url:
        return url

    try:
        # 分割协议和连接信息
        # 格式: postgresql+asyncpg://user:password@host:port/database
        protocol, rest = url.split('://', 1)
        if ':' in rest.split('@')[0]:
            # 有密码的情况
            auth_part, host_part = rest.split('@', 1)
            user = auth_part.split(':')[0]
            return f"{protocol}://{user}:***@{host_part}"
        else:
            # 无密码的情况
            return url
    except Exception:
        # 解析失败时返回原URL（不应该发生）
        return url


def _schema_init_lock_id(database_name: str) -> int:
    """
    计算 schema 初始化所使用的 advisory lock id。
    使用稳定的 31-bit 正整数，避免超出 PostgreSQL int4 范围。
    """
    base = f"auto-test-platform::{database_name}::schema-init"
    return sum(ord(ch) for ch in base) % 2_147_483_647


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
    logger.info("数据库连接已关闭")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（用于依赖注入）"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话异常: {e}")
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（用于上下文管理器）"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话异常: {e}")
            raise
        finally:
            await session.close()


# 在模块导入阶段立即注册所有模型，确保 Celery worker 等非 init_db 路径
# 也能在 SQLAlchemy 配置映射和解析外键时拿到完整的元数据。
import_all_models()