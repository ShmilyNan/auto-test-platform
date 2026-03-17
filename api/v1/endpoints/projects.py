"""
项目相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from core.database import get_session
from core.dependencies import get_current_user, get_current_user_id, check_project_permission
from project.service import ProjectService
from project.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectMemberCreate, ProjectMemberResponse
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


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(get_current_user)
):
    """获取项目列表"""
    project_service = ProjectService(session)
    projects = await project_service.list_projects(skip, limit)
    return projects


@router.get("/my", response_model=List[ProjectResponse])
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


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """删除项目"""
    # 检查权限
    await check_project_permission(project_id, current_user_id, session, "admin")

    project_service = ProjectService(session)
    success = await project_service.delete_project(project_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
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
