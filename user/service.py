"""
用户服务层
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from core.dependencies import get_current_user_id
from user.interfaces import UserServiceInterface
from user.models import User
from user.schemas import UserCreate, UserUpdate, UserResponse
from user.repository import UserRepository
from core.security import get_password_hash, verify_password
from core.logger import logger


class UserService(UserServiceInterface):
    """用户服务实现"""

    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)
        self.session = session

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

        return UserResponse.model_validate(created_user)

    async def get_user(self, user_id: int) -> Optional[UserResponse]:
        """获取用户"""
        user = await self.repository.get_by_id(user_id)
        if user:
            return UserResponse.model_validate(user)
        return None

    async def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """根据用户名获取用户"""
        user = await self.repository.get_by_username(username)
        if user:
            return UserResponse.model_validate(user)
        return None

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """根据邮箱获取用户"""
        user = await self.repository.get_by_email(email)
        if user:
            return UserResponse.model_validate(user)
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

        return UserResponse.model_validate(updated_user)

    async def delete_user(self, user_id: int) -> dict:
        """
        删除用户
        Args:
            user_id: 用户ID
        Returns:
            dict: 删除结果，包含success、message、username等信息
        Raises:
            ValueError: 各种删除失败的场景
        """
        user = await self.repository.get_by_id(user_id, include_deleted=True)
        if not user:
            raise ValueError("用户不存在")
        if user.is_superuser:
            raise ValueError("超级管理员不能被删除")
        if user.id == get_current_user_id():
            raise ValueError("不能删除自己的账户")

        try:
            await self._check_user_dependencies(user_id)
        except ValueError as e:
            raise ValueError(f"无法删除用户: {str(e)}")

        # 软删除用户
        await self.repository.soft_delete(user)
        logger.info(f"删除用户成功（软删除）: {user.username}")

        return {
            "success": True,
            "message": "用户删除成功",
            "user_id": user_id,
            "username": user.username,
            "detail": "用户已被成功删除"
        }

    async def _check_user_dependencies(self, user_id: int) -> None:
        """
        检查用户是否有关联数据
        Args:
            user_id: 用户ID
        Raises:
            ValueError: 如果用户有关联数据
        """
        from sqlalchemy import select, func
        from project.models import Project
        from testcase.models import TestCase
        from plan.models import TestPlan, ExecutionRecord

        async with self.repository.session as session:
            # 检查用户是否为项目所有者
            stmt = select(func.count()).select_from(Project).where(
                Project.owner_id == user_id,
                Project.is_deleted == False
            )
            result = await session.execute(stmt)
            project_count = result.scalar()

            if project_count > 0:
                raise ValueError(f"用户是 {project_count} 个项目的所有者，请先转移项目所有权")

            # 检查用户创建的测试用例
            stmt = select(func.count()).select_from(TestCase).where(
                TestCase.created_by == user_id,
                TestCase.is_deleted == False
            )
            result = await session.execute(stmt)
            case_count = result.scalar()

            if case_count > 0:
                # 可以选择转移或删除，这里只是警告
                logger.warning(f"用户创建了 {case_count} 个测试用例")

            # 检查用户创建的测试计划
            stmt = select(func.count()).select_from(TestPlan).where(
                TestPlan.created_by == user_id,
                TestPlan.is_deleted == False
            )
            result = await session.execute(stmt)
            plan_count = result.scalar()

            if plan_count > 0:
                logger.warning(f"用户创建了 {plan_count} 个测试计划")

            # 检查用户的执行记录
            stmt = select(func.count()).select_from(ExecutionRecord).where(ExecutionRecord.triggered_by == user_id)
            result = await session.execute(stmt)
            execution_count = result.scalar()

            if execution_count > 0:
                logger.warning(f"用户有 {execution_count} 条执行记录")

    async def list_users(self, page_num: int = 1, page_size: int = 1000) -> List[UserResponse]:
        """获取用户列表（分页）"""
        users = await self.repository.list(page_num, page_size)
        return [UserResponse.model_validate(user) for user in users]

    async def authenticate_user(self, username: str, password: str) -> Optional[UserResponse]:
        """验证用户"""
        user = await self.repository.get_by_username(username)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return UserResponse.model_validate(user)

    async def check_permission(self, user_id: int, project_id: int, permission: str) -> bool:
        """检查用户权限"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            return False

        # 超级用户拥有所有权限
        if user.is_superuser:
            return True

        # 管理员拥有所有权限
        if user.role == "admin":
            return True

        # 检查项目成员表中的权限
        from sqlalchemy import select
        from project.models import ProjectMember

        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
        result = await self.session.execute(stmt)
        member = result.scalar_one_or_none()

        if not member:
            return False

        # 根据角色和权限判断
        role_permissions = {
            "admin": ["create", "read", "update", "delete", "execute", "manage"],
            "member": ["create", "read", "update", "execute"],
            "viewer": ["read"]
        }

        allowed_permissions = role_permissions.get(member.role, [])
        return permission in allowed_permissions
