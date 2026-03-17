"""
依赖注入容器
"""
from typing import Any, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    """获取数据库会话依赖"""
    async for session in get_session():
        yield session


# 以下为各模块服务的依赖注入
# 在实现各模块后取消注释

# @lru_cache()
# def get_user_service():
#     from user.service import UserService
#     return UserService()
#
#
# @lru_cache()
# def get_project_service():
#     from project.service import ProjectService
#     return ProjectService()
