"""
依赖注入模块
提供统一的依赖注入配置
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import ProjectRole, UserRole
from core.database import get_session
from core.security import decode_access_token
from core.config import settings


# OAuth2密码模式
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/login",
    auto_error=True
)


async def get_current_user_id(
    token: str = Depends(oauth2_scheme)
) -> int:
    """
    从JWT token中获取当前用户ID
    Returns:
        int: 用户ID
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise credentials_exception

    return user_id


async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """
    获取当前用户完整信息
    Returns:
        User: 用户对象
    """
    from user.repository import UserRepository
    from user.schemas import UserResponse

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    return UserResponse.model_validate(user)


async def get_current_active_user(
    current_user = Depends(get_current_user)
):
    """
    获取当前活跃用户
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户未激活"
        )
    return current_user


async def get_current_admin_user(
    current_user = Depends(get_current_user)
):
    """
    获取当前管理员用户
    """
    if current_user.role != UserRole.ADMIN.value and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限"
        )
    return current_user


async def check_project_permission(
    project_id: int,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    required_role: str = "member"
) -> bool:
    """
    检查用户对项目的权限
    Args:
        project_id: 项目ID
        user_id: 用户ID
        session: 数据库会话
        required_role: 需要的角色 (admin, member, viewer)
    Returns:
        bool: 是否有权限
    """
    from project.repository import ProjectRepository, ProjectMemberRepository

    project_repo = ProjectRepository(session)
    member_repo = ProjectMemberRepository(session)

    # 获取项目
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    # 项目所有者拥有所有权限
    if project.owner_id == user_id:
        return True

    # 检查项目成员权限
    member = await member_repo.get_by_project_and_user(project_id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该项目的成员"
        )

    # 权限级别检查
    role_hierarchy = {
        ProjectRole.VIEWER.value: 1,
        ProjectRole.MEMBER.value: 2,
        ProjectRole.ADMIN.value: 3
    }

    user_level = role_hierarchy.get(member.role, 0)
    required_level = role_hierarchy.get(required_role, 0)

    if user_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    return True


# 数据库会话依赖
async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async for session in get_session():
        yield session
