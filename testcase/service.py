"""
测试用例服务层
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from testcase.interfaces import TestCaseServiceInterface
from testcase.models import TestCase, TestSuite
from testcase.schemas import (
    TestCaseCreate, TestCaseUpdate, TestCaseResponse,
    TestSuiteCreate, TestSuiteUpdate, TestSuiteResponse
)
from testcase.repository import TestCaseRepository, TestSuiteRepository
from core.logger import get_logger

logger = get_logger(__name__)


class TestCaseService(TestCaseServiceInterface):
    """测试用例服务实现"""
    
    def __init__(self, session: AsyncSession):
        self.case_repo = TestCaseRepository(session)
        self.suite_repo = TestSuiteRepository(session)
    
    async def create_case(self, case_data: TestCaseCreate, user_id: int) -> TestCaseResponse:
        """创建测试用例"""
        case = TestCase(
            project_id=case_data.project_id,
            name=case_data.name,
            description=case_data.description,
            method=case_data.method,
            url=case_data.url,
            headers=case_data.headers,
            params=case_data.params,
            body=case_data.body,
            assertions=case_data.assertions,
            extract=case_data.extract,
            tags=case_data.tags,
            enabled=case_data.enabled,
            timeout=case_data.timeout,
            created_by=user_id
        )
        
        created_case = await self.case_repo.create(case)
        logger.info(f"创建测试用例成功: {created_case.name}")
        
        return TestCaseResponse.from_orm(created_case)
    
    async def get_case(self, case_id: int) -> Optional[TestCaseResponse]:
        """获取测试用例"""
        case = await self.case_repo.get_by_id(case_id)
        if case:
            return TestCaseResponse.from_orm(case)
        return None
    
    async def update_case(self, case_id: int, case_data: TestCaseUpdate) -> Optional[TestCaseResponse]:
        """更新测试用例"""
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            return None
        
        # 更新字段
        update_data = case_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(case, field, value)
        
        updated_case = await self.case_repo.update(case)
        logger.info(f"更新测试用例成功: {updated_case.name}")
        
        return TestCaseResponse.from_orm(updated_case)
    
    async def delete_case(self, case_id: int) -> bool:
        """删除测试用例"""
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            return False
        
        await self.case_repo.delete(case)
        logger.info(f"删除测试用例成功: {case.name}")
        
        return True
    
    async def list_cases(self, project_id: int, skip: int = 0, limit: int = 100) -> List[TestCaseResponse]:
        """获取测试用例列表"""
        cases = await self.case_repo.list_by_project(project_id, skip, limit)
        return [TestCaseResponse.from_orm(case) for case in cases]
    
    async def get_cases_by_ids(self, case_ids: List[int]) -> List[TestCaseResponse]:
        """根据ID列表获取测试用例"""
        cases = await self.case_repo.get_by_ids(case_ids)
        return [TestCaseResponse.from_orm(case) for case in cases]
    
    async def create_suite(self, suite_data: TestSuiteCreate, user_id: int) -> TestSuiteResponse:
        """创建测试用例集"""
        suite = TestSuite(
            project_id=suite_data.project_id,
            name=suite_data.name,
            description=suite_data.description,
            case_ids=suite_data.case_ids,
            created_by=user_id
        )
        
        created_suite = await self.suite_repo.create(suite)
        logger.info(f"创建测试用例集成功: {created_suite.name}")
        
        return TestSuiteResponse.from_orm(created_suite)
    
    async def get_suite(self, suite_id: int) -> Optional[TestSuiteResponse]:
        """获取测试用例集"""
        suite = await self.suite_repo.get_by_id(suite_id)
        if suite:
            return TestSuiteResponse.from_orm(suite)
        return None
    
    async def update_suite(self, suite_id: int, suite_data: TestSuiteUpdate) -> Optional[TestSuiteResponse]:
        """更新测试用例集"""
        suite = await self.suite_repo.get_by_id(suite_id)
        if not suite:
            return None
        
        # 更新字段
        update_data = suite_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(suite, field, value)
        
        updated_suite = await self.suite_repo.update(suite)
        logger.info(f"更新测试用例集成功: {updated_suite.name}")
        
        return TestSuiteResponse.from_orm(updated_suite)
    
    async def delete_suite(self, suite_id: int) -> bool:
        """删除测试用例集"""
        suite = await self.suite_repo.get_by_id(suite_id)
        if not suite:
            return False
        
        await self.suite_repo.delete(suite)
        logger.info(f"删除测试用例集成功: {suite.name}")
        
        return True
    
    async def list_suites(self, project_id: int, skip: int = 0, limit: int = 100) -> List[TestSuiteResponse]:
        """获取测试用例集列表"""
        suites = await self.suite_repo.list_by_project(project_id, skip, limit)
        return [TestSuiteResponse.from_orm(suite) for suite in suites]
