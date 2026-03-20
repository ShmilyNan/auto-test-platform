"""
项目服务层
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from project.interfaces import ProjectServiceInterface
from project.models import Project, ProjectMember
from project.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectMemberCreate, ProjectMemberResponse
)
from project.repository import ProjectRepository, ProjectMemberRepository
from core.logger import logger



class ProjectService(ProjectServiceInterface):
    """项目服务实现"""
    
    def __init__(self, session: AsyncSession):
        self.project_repo = ProjectRepository(session)
        self.member_repo = ProjectMemberRepository(session)
    
    async def create_project(self, project_data: ProjectCreate, owner_id: int) -> ProjectResponse:
        """创建项目"""
        project = Project(
            name=project_data.name,
            description=project_data.description,
            owner_id=owner_id
        )
        
        created_project = await self.project_repo.create(project)
        
        # 将创建者添加为项目管理员
        member = ProjectMember(
            project_id=created_project.id,
            user_id=owner_id,
            role="admin"
        )
        await self.member_repo.create(member)
        
        logger.info(f"创建项目成功: {created_project.name}")
        
        return ProjectResponse.model_validate(created_project)
    
    async def get_project(self, project_id: int) -> Optional[ProjectResponse]:
        """获取项目"""
        project = await self.project_repo.get_by_id(project_id)
        if project:
            return ProjectResponse.model_validate(project)
        return None
    
    async def update_project(self, project_id: int, project_data: ProjectUpdate) -> Optional[ProjectResponse]:
        """更新项目"""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            return None
        
        # 更新字段
        if project_data.name is not None:
            project.name = project_data.name
        if project_data.description is not None:
            project.description = project_data.description
        if project_data.is_active is not None:
            project.is_active = project_data.is_active
        
        updated_project = await self.project_repo.update(project)
        logger.info(f"更新项目成功: {updated_project.name}")
        
        return ProjectResponse.model_validate(updated_project)
    
    async def delete_project(self, project_id: int) -> dict:
        """删除项目"""
        project = await self.project_repo.get_by_id(project_id, include_deleted=True)
        if not project:
            raise ValueError(f"项目ID {project_id} 不存在")

        project_name = project.name
        await self.project_repo.soft_delete(project)
        logger.info(f"删除项目成功（软删除）: {project.name}")
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_name,
            "message": f"删除项目成功: {project_name}",
            "detail": "项目已被成功删除"
        }

    async def list_projects(self, page_num: int = 1, page_size: int = 1000) -> List[ProjectResponse]:
        """获取项目列表（分页）"""
        projects = await self.project_repo.list(page_num, page_size)
        return [ProjectResponse.model_validate(project) for project in projects]
    
    async def list_user_projects(self, user_id: int) -> List[ProjectResponse]:
        """获取用户的项目列表"""
        # 获取用户拥有的项目
        owned_projects = await self.project_repo.list_by_owner(user_id)
        
        # 获取用户参与的项目
        member_projects = await self.project_repo.list_by_member(user_id)
        
        # 合并并去重
        all_projects = {project.id: project for project in owned_projects}
        for project in member_projects:
            all_projects[project.id] = project
        
        return [ProjectResponse.model_validate(project) for project in all_projects.values()]
    
    async def add_member(self, project_id: int, member_data: ProjectMemberCreate) -> ProjectMemberResponse:
        """添加项目成员"""
        # 检查是否已存在
        existing = await self.member_repo.get_by_project_and_user(
            project_id, member_data.user_id
        )
        if existing:
            raise ValueError("用户已是项目成员")
        
        member = ProjectMember(
            project_id=project_id,
            user_id=member_data.user_id,
            role=member_data.role
        )
        
        created_member = await self.member_repo.create(member)
        logger.info(f"添加项目成员成功: project_id={project_id}, user_id={member_data.user_id}")
        
        return ProjectMemberResponse.model_validate(created_member)
    
    async def remove_member(self, project_id: int, user_id: int) -> bool:
        """移除项目成员"""
        member = await self.member_repo.get_by_project_and_user(project_id, user_id)
        if not member:
            return False
        
        await self.member_repo.delete(member)
        logger.info(f"移除项目成员成功: project_id={project_id}, user_id={user_id}")
        
        return True
    
    async def update_member_role(self, project_id: int, user_id: int, role: str) -> Optional[ProjectMemberResponse]:
        """更新成员角色"""
        member = await self.member_repo.get_by_project_and_user(project_id, user_id)
        if not member:
            return None
        
        member.role = role
        updated_member = await self.member_repo.update(member)
        logger.info(f"更新成员角色成功: project_id={project_id}, user_id={user_id}, role={role}")
        
        return ProjectMemberResponse.model_validate(updated_member)
    
    async def list_members(self, project_id: int) -> List[ProjectMemberResponse]:
        """获取项目成员列表"""
        members = await self.member_repo.list_by_project(project_id)
        return [ProjectMemberResponse.model_validate(member) for member in members]
