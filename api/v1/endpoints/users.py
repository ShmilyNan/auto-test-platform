"""
用户相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.database import get_session
from core.security import decode_access_token
from user.service import UserService
from user.schemas import UserResponse, UserUpdate

router = APIRouter()


async def get_current_user(
    token: str = Depends(lambda: None),
    session: AsyncSession = Depends(get_session)
) -> UserResponse:
    """获取当前用户"""
    # TODO: 实现token验证
    # 这里简化处理，实际应该从header中提取token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未认证"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user)
):
    """获取当前用户信息"""
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
):
    """获取用户列表"""
    user_service = UserService(session)
    users = await user_service.list_users(skip, limit)
    return users


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_session)
):
    """更新用户信息"""
    user_service = UserService(session)
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
    session: AsyncSession = Depends(get_session)
):
    """删除用户"""
    user_service = UserService(session)
    success = await user_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
