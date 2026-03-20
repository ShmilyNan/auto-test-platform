"""
测试用例数据访问层
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from testcase.models import TestCase, TestSuite


class TestCaseRepository:
    """测试用例仓库"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, case: TestCase) -> TestCase:
        """创建测试用例"""
        self.session.add(case)
        await self.session.commit()
        await self.session.refresh(case)
        return case
    
    async def get_by_id(self, case_id: int, include_deleted: bool = False) -> Optional[TestCase]:
        """根据ID获取测试用例"""
        query = select(TestCase).where(TestCase.id == case_id)
        if not include_deleted:
            query = query.where(TestCase.is_deleted == False)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update(self, case: TestCase) -> TestCase:
        """更新测试用例"""
        await self.session.commit()
        await self.session.refresh(case)
        return case

    async def soft_delete(self, case: TestCase) -> bool:
        """软删除测试用例"""
        case.is_deleted = True
        case.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    async def delete(self, case: TestCase) -> bool:
        """物理删除测试用例"""
        await self.session.delete(case)
        await self.session.commit()
        return True
    
    async def list_by_project(self, project_id: int, page_num: int = 1, page_size: int = 1000) -> List[TestCase]:
        """获取项目的测试用例列表（分页）"""
        offset = (page_num - 1) * page_size
        result = await self.session.execute(
            select(TestCase)
            .where(
                TestCase.project_id == project_id,
                TestCase.is_deleted == False
            )
            .offset(offset)
            .limit(page_size)
        )
        return result.scalars().all()
    
    async def count_by_project(self, project_id: int) -> int:
        """获取项目的测试用例总数"""
        result = await self.session.execute(
            select(func.count()).select_from(TestCase).where(
                TestCase.project_id == project_id,
                TestCase.is_deleted == False
            )
        )
        return result.scalar()

    async def get_by_ids(self, case_ids: List[int], include_deleted: bool = False) -> List[TestCase]:
        """根据ID列表获取测试用例"""
        query = select(TestCase).where(TestCase.id.in_(case_ids))
        if not include_deleted:
            query = query.where(TestCase.is_deleted == False)
        result = await self.session.execute(query)
        return result.scalars().all()


class TestSuiteRepository:
    """测试用例集仓库"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, suite: TestSuite) -> TestSuite:
        """创建测试用例集"""
        self.session.add(suite)
        await self.session.commit()
        await self.session.refresh(suite)
        return suite
    
    async def get_by_id(self, suite_id: int, include_deleted: bool = False) -> Optional[TestSuite]:
        """根据ID获取测试用例集"""
        query = select(TestSuite).where(TestSuite.id == suite_id)
        if not include_deleted:
            query = query.where(TestSuite.is_deleted == False)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update(self, suite: TestSuite) -> TestSuite:
        """更新测试用例集"""
        await self.session.commit()
        await self.session.refresh(suite)
        return suite

    async def soft_delete(self, suite: TestSuite) -> bool:
        """软删除测试用例集"""
        suite.is_deleted = True
        suite.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    async def delete(self, suite: TestSuite) -> bool:
        """物理删除测试用例集"""
        await self.session.delete(suite)
        await self.session.commit()
        return True
    
    async def list_by_project(self, project_id: int, page_num: int = 1, page_size: int = 1000) -> List[TestSuite]:
        """获取项目的测试用例集列表（分页）"""
        offset = (page_num - 1) * page_size
        result = await self.session.execute(
            select(TestSuite)
            .where(
                TestSuite.project_id == project_id,
                TestSuite.is_deleted == False
            )
            .offset(offset)
            .limit(page_size)
        )
        return result.scalars().all()

    async def count_by_project(self, project_id: int) -> int:
        """获取项目的测试用例集总数"""
        result = await self.session.execute(
            select(func.count()).select_from(TestSuite).where(
                TestSuite.project_id == project_id,
                TestSuite.is_deleted == False
            )
        )
        return result.scalar()
