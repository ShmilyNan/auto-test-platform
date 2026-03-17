"""
用户相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from core.database import get_session
from core.dependencies import get_current_user, get_current_admin_user, get_current_user_id
from user.service import UserService
from user.schemas import UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user)
):
    """获取当前用户信息"""
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(get_current_user)
):
    """获取用户信息"""
    user_service = UserService(session)
    user = await user_service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(get_current_admin_user)  # 需要管理员权限
):
    """获取用户列表（需要管理员权限）"""
    user_service = UserService(session)
    users = await user_service.list_users(skip, limit)
    return users


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """更新用户信息"""
    # 只能更新自己的信息，或者是管理员
    user_service = UserService(session)
    current = await user_service.get_user(current_user_id)

    if current.id != user_id and current.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改其他用户信息"
        )

    user = await user_service.update_user(user_id, user_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(get_current_admin_user)  # 需要管理员权限
):
    """删除用户（需要管理员权限）"""
    user_service = UserService(session)

    # 不能删除自己
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户"
        )

    success = await user_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
