"""
用户数据访问层
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from user.models import User


class UserRepository:
    """用户仓库"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user: User) -> User:
        """创建用户"""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_by_id(self, user_id: int, include_deleted: bool = False) -> Optional[User]:
        """根据ID获取用户"""
        query = select(User).where(User.id == user_id)
        if not include_deleted:
            query = query.where(User.is_deleted == False)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str, include_deleted: bool = False) -> Optional[User]:
        """根据用户名获取用户"""
        query = select(User).where(User.username == username)
        if not include_deleted:
            query = query.where(User.is_deleted == False)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str, include_deleted: bool = False) -> Optional[User]:
        """根据邮箱获取用户"""
        query = select(User).where(User.email == email)
        if not include_deleted:
            query = query.where(User.is_deleted == False)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update(self, user: User) -> User:
        """更新用户"""
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def soft_delete(self, user: User) -> bool:
        """软删除用户"""
        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    async def delete(self, user: User) -> bool:
        """物理删除用户"""
        await self.session.delete(user)
        await self.session.commit()
        return True
    
    async def list(self, page_num: int = 1, page_size: int = 1000) -> List[User]:
        """获取用户列表（分页）"""
        offset = (page_num - 1) * page_size
        result = await self.session.execute(
            select(User)
            .where(User.is_deleted == False)
            .offset(offset)
            .limit(page_size)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """获取用户总数"""
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.is_deleted == False)
        )
        return result.scalar()
