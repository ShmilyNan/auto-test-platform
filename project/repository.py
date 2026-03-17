"""
项目数据访问层
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from project.models import Project, ProjectMember


class ProjectRepository:
    """项目仓库"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, project: Project) -> Project:
        """创建项目"""
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project
    
    async def get_by_id(self, project_id: int) -> Optional[Project]:
        """根据ID获取项目"""
        result = await self.session.execute(
            select(Project)
            .options(selectinload(Project.members))
            .where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, project: Project) -> Project:
        """更新项目"""
        await self.session.commit()
        await self.session.refresh(project)
        return project
    
    async def delete(self, project: Project) -> bool:
        """删除项目"""
        await self.session.delete(project)
        await self.session.commit()
        return True
    
    async def list(self, skip: int = 0, limit: int = 100) -> List[Project]:
        """获取项目列表"""
        result = await self.session.execute(
            select(Project).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def list_by_owner(self, owner_id: int) -> List[Project]:
        """获取用户拥有的项目"""
        result = await self.session.execute(
            select(Project).where(Project.owner_id == owner_id)
        )
        return result.scalars().all()
    
    async def list_by_member(self, user_id: int) -> List[Project]:
        """获取用户参与的项目"""
        result = await self.session.execute(
            select(Project)
            .join(ProjectMember, Project.id == ProjectMember.project_id)
            .where(ProjectMember.user_id == user_id)
        )
        return result.scalars().all()


class ProjectMemberRepository:
    """项目成员仓库"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, member: ProjectMember) -> ProjectMember:
        """添加成员"""
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member
    
    async def get_by_project_and_user(self, project_id: int, user_id: int) -> Optional[ProjectMember]:
        """获取项目成员"""
        result = await self.session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
    
    async def delete(self, member: ProjectMember) -> bool:
        """删除成员"""
        await self.session.delete(member)
        await self.session.commit()
        return True
    
    async def update(self, member: ProjectMember) -> ProjectMember:
        """更新成员"""
        await self.session.commit()
        await self.session.refresh(member)
        return member
    
    async def list_by_project(self, project_id: int) -> List[ProjectMember]:
        """获取项目成员列表"""
        result = await self.session.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_id)
        )
        return result.scalars().all()
