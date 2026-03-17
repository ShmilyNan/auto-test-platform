"""
测试用例数据访问层
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    
    async def get_by_id(self, case_id: int) -> Optional[TestCase]:
        """根据ID获取测试用例"""
        result = await self.session.execute(
            select(TestCase).where(TestCase.id == case_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, case: TestCase) -> TestCase:
        """更新测试用例"""
        await self.session.commit()
        await self.session.refresh(case)
        return case
    
    async def delete(self, case: TestCase) -> bool:
        """删除测试用例"""
        await self.session.delete(case)
        await self.session.commit()
        return True
    
    async def list_by_project(self, project_id: int, skip: int = 0, limit: int = 100) -> List[TestCase]:
        """获取项目的测试用例列表"""
        result = await self.session.execute(
            select(TestCase)
            .where(TestCase.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_ids(self, case_ids: List[int]) -> List[TestCase]:
        """根据ID列表获取测试用例"""
        result = await self.session.execute(
            select(TestCase).where(TestCase.id.in_(case_ids))
        )
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
    
    async def get_by_id(self, suite_id: int) -> Optional[TestSuite]:
        """根据ID获取测试用例集"""
        result = await self.session.execute(
            select(TestSuite).where(TestSuite.id == suite_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, suite: TestSuite) -> TestSuite:
        """更新测试用例集"""
        await self.session.commit()
        await self.session.refresh(suite)
        return suite
    
    async def delete(self, suite: TestSuite) -> bool:
        """删除测试用例集"""
        await self.session.delete(suite)
        await self.session.commit()
        return True
    
    async def list_by_project(self, project_id: int, skip: int = 0, limit: int = 100) -> List[TestSuite]:
        """获取项目的测试用例集列表"""
        result = await self.session.execute(
            select(TestSuite)
            .where(TestSuite.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
