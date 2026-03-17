"""
用户服务层
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from user.interfaces import UserServiceInterface
from user.models import User
from user.schemas import UserCreate, UserUpdate, UserResponse
from user.repository import UserRepository
from core.security import get_password_hash, verify_password
from core.logger import get_logger

logger = get_logger(__name__)


class UserService(UserServiceInterface):
    """用户服务实现"""
    
    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """创建用户"""
        # 检查用户名是否已存在
        existing_user = await self.repository.get_by_username(user_data.username)
        if existing_user:
            raise ValueError("用户名已存在")
        
        # 检查邮箱是否已存在
        existing_email = await self.repository.get_by_email(user_data.email)
        if existing_email:
            raise ValueError("邮箱已存在")
        
        # 创建用户
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name
        )
        
        created_user = await self.repository.create(user)
        logger.info(f"创建用户成功: {created_user.username}")
        
        return UserResponse.from_orm(created_user)
    
    async def get_user(self, user_id: int) -> Optional[UserResponse]:
        """获取用户"""
        user = await self.repository.get_by_id(user_id)
        if user:
            return UserResponse.from_orm(user)
        return None
    
    async def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """根据用户名获取用户"""
        user = await self.repository.get_by_username(username)
        if user:
            return UserResponse.from_orm(user)
        return None
    
    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """根据邮箱获取用户"""
        user = await self.repository.get_by_email(email)
        if user:
            return UserResponse.from_orm(user)
        return None
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[UserResponse]:
        """更新用户"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            return None
        
        # 更新字段
        if user_data.email:
            user.email = user_data.email
        if user_data.full_name:
            user.full_name = user_data.full_name
        if user_data.password:
            user.hashed_password = get_password_hash(user_data.password)
        
        updated_user = await self.repository.update(user)
        logger.info(f"更新用户成功: {updated_user.username}")
        
        return UserResponse.from_orm(updated_user)
    
    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            return False
        
        await self.repository.delete(user)
        logger.info(f"删除用户成功: {user.username}")
        
        return True
    
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """获取用户列表"""
        users = await self.repository.list(skip, limit)
        return [UserResponse.from_orm(user) for user in users]
    
    async def authenticate_user(self, username: str, password: str) -> Optional[UserResponse]:
        """验证用户"""
        user = await self.repository.get_by_username(username)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        return UserResponse.from_orm(user)
    
    async def check_permission(self, user_id: int, project_id: int, permission: str) -> bool:
        """检查用户权限"""
        # TODO: 实现基于RBAC的权限检查
        # 这里简化处理，实际应该查询用户在项目中的角色和权限
        user = await self.repository.get_by_id(user_id)
        if not user:
            return False
        
        # 超级用户拥有所有权限
        if user.is_superuser:
            return True
        
        # 管理员拥有所有权限
        if user.role == "admin":
            return True
        
        # TODO: 检查项目成员表中的权限
        return True
