"""
项目模块接口定义
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from project.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectMemberCreate, ProjectMemberResponse


class ProjectServiceInterface(ABC):
    """项目服务接口"""
    
    @abstractmethod
    async def create_project(self, project_data: ProjectCreate, owner_id: int) -> ProjectResponse:
        """创建项目"""
        pass
    
    @abstractmethod
    async def get_project(self, project_id: int) -> Optional[ProjectResponse]:
        """获取项目"""
        pass
    
    @abstractmethod
    async def update_project(self, project_id: int, project_data: ProjectUpdate) -> Optional[ProjectResponse]:
        """更新项目"""
        pass
    
    @abstractmethod
    async def delete_project(self, project_id: int) -> bool:
        """删除项目"""
        pass
    
    @abstractmethod
    async def list_projects(self, skip: int = 0, limit: int = 100) -> List[ProjectResponse]:
        """获取项目列表"""
        pass
    
    @abstractmethod
    async def list_user_projects(self, user_id: int) -> List[ProjectResponse]:
        """获取用户的项目列表"""
        pass
    
    @abstractmethod
    async def add_member(self, project_id: int, member_data: ProjectMemberCreate) -> ProjectMemberResponse:
        """添加项目成员"""
        pass
    
    @abstractmethod
    async def remove_member(self, project_id: int, user_id: int) -> bool:
        """移除项目成员"""
        pass
    
    @abstractmethod
    async def update_member_role(self, project_id: int, user_id: int, role: str) -> Optional[ProjectMemberResponse]:
        """更新成员角色"""
        pass
    
    @abstractmethod
    async def list_members(self, project_id: int) -> List[ProjectMemberResponse]:
        """获取项目成员列表"""
        pass
