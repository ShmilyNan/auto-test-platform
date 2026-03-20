"""
用户相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from core.dependencies import get_current_user, get_current_admin_user, get_current_user_id
from user.service import UserService
from user.schemas import UserResponse, UserUpdate, DeleteUserResponse, DeleteUserError

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


@router.get("/", response_model=list[UserResponse])
async def list_users(
    page_num: int = Query(default=1, ge=1, description="页码，从1开始"),
    page_size: int = Query(default=1000, ge=1, le=10000, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(get_current_admin_user)  # 需要管理员权限
):
    """获取用户列表（需要管理员权限）"""
    user_service = UserService(session)
    users = await user_service.list_users(page_num, page_size)
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


@router.delete(
    "/{user_id}",
    response_model=DeleteUserResponse,
    responses={
        200: {
            "description": "用户删除成功",
            "model": DeleteUserResponse,
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "用户删除成功",
                        "user_id": 1,
                        "username": "testuser",
                        "detail": "用户已被成功删除，所有关联数据已清理"
                    }
                }
            }
        },
        400: {
            "description": "删除失败 - 不能删除自己的账户",
            "model": DeleteUserError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "用户删除失败",
                        "error_code": "CANNOT_DELETE_SELF",
                        "detail": "不能删除自己的账户"
                    }
                }
            }
        },
        403: {
            "description": "删除失败 - 无权限",
            "model": DeleteUserError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "用户删除失败",
                        "error_code": "FORBIDDEN",
                        "detail": "需要管理员权限"
                    }
                }
            }
        },
        404: {
            "description": "删除失败 - 用户不存在",
            "model": DeleteUserError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "用户删除失败",
                        "error_code": "USER_NOT_FOUND",
                        "detail": "用户ID 999 不存在"
                    }
                }
            }
        },
        409: {
            "description": "删除失败 - 用户有关联数据",
            "model": DeleteUserError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "用户删除失败",
                        "error_code": "HAS_DEPENDENCIES",
                        "detail": "用户是 3 个项目的所有者，请先转移项目所有权"
                    }
                }
            }
        },
        423: {
            "description": "删除失败 - 超级管理员不能被删除",
            "model": DeleteUserError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "用户删除失败",
                        "error_code": "SUPERUSER_PROTECTED",
                        "detail": "无法删除超级管理员账户"
                    }
                }
            }
        },
        500: {
            "description": "删除失败 - 服务器内部错误",
            "model": DeleteUserError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "用户删除失败",
                        "error_code": "INTERNAL_ERROR",
                        "detail": "删除用户时发生内部错误"
                    }
                }
            }
        }
    },
)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(get_current_admin_user)  # 需要管理员权限
):
    """
    删除用户（需要管理员权限）
    **可能的错误场景：**
    - 400: 不能删除自己的账户
    - 403: 无权限（非管理员）
    - 404: 用户不存在
    - 409: 用户有关联数据（项目所有者等）
    - 423: 超级管理员不能被删除
    - 500: 服务器内部错误
    """
    user_service = UserService(session)

    # 不能删除自己
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "用户删除失败",
                "error_code": "CANNOT_DELETE_SELF",
                "detail": "不能删除自己的账户"
            }
        )

    try:
        # 调用服务层删除用户
        result = await user_service.delete_user(user_id)
        return result

    except ValueError as e:
        error_msg = str(e)

        # 用户不存在
        if "不存在" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "message": "用户删除失败",
                    "error_code": "USER_NOT_FOUND",
                    "detail": error_msg
                }
            )

        # 超级管理员保护
        if "超级管理员" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "success": False,
                    "message": "用户删除失败",
                    "error_code": "SUPERUSER_PROTECTED",
                    "detail": error_msg
                }
            )

        # 用户有关联数据
        if "项目所有者" in error_msg or "关联数据" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "success": False,
                    "message": "用户删除失败",
                    "error_code": "HAS_DEPENDENCIES",
                    "detail": error_msg
                }
            )

        # 其他业务错误
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "用户删除失败",
                "error_code": "BUSINESS_ERROR",
                "detail": error_msg
            }
        )

    except Exception as e:
        # 记录异常日志
        from core.logger import logger
        logger.error(f"删除用户异常: user_id={user_id}, error={str(e)}", exc_info=True)

        # 返回500错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "用户删除失败",
                "error_code": "INTERNAL_ERROR",
                "detail": "删除用户时发生内部错误，请稍后重试"
            }
        )
