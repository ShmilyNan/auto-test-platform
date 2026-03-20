"""
项目相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from core.database import get_session
from core.dependencies import get_current_user, get_current_user_id, check_project_permission
from project.service import ProjectService
from project.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectMemberCreate, ProjectMemberResponse,
    DeleteProjectResponse, DeleteProjectError
)
from user.schemas import UserResponse

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """创建项目"""
    project_service = ProjectService(session)
    project = await project_service.create_project(project_data, current_user_id)
    return project


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    page_num: int = Query(default=1, ge=1, description="页码，从1开始"),
    page_size: int = Query(default=1000, ge=1, le=10000, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(get_current_user)
):
    """获取项目列表"""
    project_service = ProjectService(session)
    projects = await project_service.list_projects(page_size, page_num)
    return projects


@router.get("/my", response_model=list[ProjectResponse])
async def list_my_projects(
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """获取我的项目列表"""
    project_service = ProjectService(session)
    projects = await project_service.list_user_projects(current_user_id)
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取项目详情"""
    # 检查权限
    await check_project_permission(project_id, current_user_id, session, "viewer")

    project_service = ProjectService(session)
    project = await project_service.get_project(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """更新项目"""
    # 检查权限
    await check_project_permission(project_id, current_user_id, session, "admin")

    project_service = ProjectService(session)
    project = await project_service.update_project(project_id, project_data)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    return project


@router.delete(
    "/{project_id}",
    response_model=DeleteProjectResponse,
    responses={
        200: {
            "description": "项目删除成功",
            "model": DeleteProjectResponse,
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "项目删除成功",
                        "project_id": 1,
                        "project_name": "test_project",
                        "detail": "项目已被成功删除，所有关联数据已清理"
                    }
                }
            }
        },
        403: {
            "description": "删除失败 - 当前账号无权限",
            "model": DeleteProjectError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "项目删除失败",
                        "error_code": "FORBIDDEN",
                        "detail": "需要项目管理员权限"
                    }
                }
            }
        },
        404: {
            "description": "删除失败 - 项目不存在",
            "model": DeleteProjectError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "项目删除失败",
                        "error_code": "PROJECT_NOT_FOUND",
                        "detail": "项目ID 999 不存在"
                    }
                }
            }
        },
        500: {
            "description": "删除失败 - 服务器内部错误",
            "model": DeleteProjectError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "项目删除失败",
                        "error_code": "INTERNAL_ERROR",
                        "detail": "删除项目时发生内部错误"
                    }
                }
            }
        }
    }
)
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    删除项目
    **可能的错误场景：**
    - 403: 无权限（非管理员/所有者）
    - 404: 项目不存在
    - 500: 服务器内部错误
    """
    # 检查权限
    await check_project_permission(project_id, current_user_id, session, "admin")

    project_service = ProjectService(session)
    try:
        result = await project_service.delete_project(project_id)
        return result
    except ValueError as e:
        error_msg = str(e)

        if "不存在" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "message": "项目删除失败",
                    "error_code": "PROJECT_NOT_FOUND",
                    "detail": error_msg,
                },
            )
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = {
                "success": False,
                "message": "项目删除失败",
                "error_code": "BUSINESS_ERROR",
                "detail": error_msg,
            },
        )
    except Exception as e:
        from core.logger import logger

        logger.error(f"删除项目异常: project_id={project_id}, error={str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "项目删除失败",
                "error_code": "INTERNAL_ERROR",
                "detail": "删除项目时发生内部错误，请稍后重试",
            },
        )


# 项目成员管理
@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    project_id: int,
    member_data: ProjectMemberCreate,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """添加项目成员"""
    # 检查权限
    await check_project_permission(project_id, current_user_id, session, "admin")

    project_service = ProjectService(session)
    try:
        member = await project_service.add_member(project_id, member_data)
        return member
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
async def list_members(
    project_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取项目成员列表"""
    # 检查权限
    await check_project_permission(project_id, current_user_id, session, "viewer")

    project_service = ProjectService(session)
    members = await project_service.list_members(project_id)
    return members


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    project_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """移除项目成员"""
    # 检查权限
    await check_project_permission(project_id, current_user_id, session, "admin")

    project_service = ProjectService(session)
    success = await project_service.remove_member(project_id, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="成员不存在"
        )


@router.put("/{project_id}/members/{user_id}/role", response_model=ProjectMemberResponse)
async def update_member_role(
    project_id: int,
    user_id: int,
    role: str,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """更新成员角色"""
    # 检查权限
    await check_project_permission(project_id, current_user_id, session, "admin")

    project_service = ProjectService(session)
    member = await project_service.update_member_role(project_id, user_id, role)

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="成员不存在"
        )

    return member
