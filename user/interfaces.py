"""
用户模块接口定义
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from user.schemas import UserCreate, UserUpdate, UserResponse


class UserServiceInterface(ABC):
    """用户服务接口"""
    
    @abstractmethod
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """创建用户"""
        pass
    
    @abstractmethod
    async def get_user(self, user_id: int) -> Optional[UserResponse]:
        """获取用户"""
        pass
    
    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """根据用户名获取用户"""
        pass
    
    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """根据邮箱获取用户"""
        pass
    
    @abstractmethod
    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[UserResponse]:
        """更新用户"""
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        pass
    
    @abstractmethod
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """获取用户列表"""
        pass
    
    @abstractmethod
    async def authenticate_user(self, username: str, password: str) -> Optional[UserResponse]:
        """验证用户"""
        pass
    
    @abstractmethod
    async def check_permission(self, user_id: int, project_id: int, permission: str) -> bool:
        """检查用户权限"""
        pass
