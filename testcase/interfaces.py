"""
测试用例模块接口定义
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from testcase.schemas import (
    TestCaseCreate, TestCaseUpdate, TestCaseResponse,
    TestSuiteCreate, TestSuiteUpdate, TestSuiteResponse
)


class TestCaseServiceInterface(ABC):
    """测试用例服务接口"""
    
    @abstractmethod
    async def create_case(self, case_data: TestCaseCreate, user_id: int) -> TestCaseResponse:
        """创建测试用例"""
        pass
    
    @abstractmethod
    async def get_case(self, case_id: int) -> Optional[TestCaseResponse]:
        """获取测试用例"""
        pass
    
    @abstractmethod
    async def update_case(self, case_id: int, case_data: TestCaseUpdate) -> Optional[TestCaseResponse]:
        """更新测试用例"""
        pass
    
    @abstractmethod
    async def delete_case(self, case_id: int) -> bool:
        """删除测试用例"""
        pass
    
    @abstractmethod
    async def list_cases(self, project_id: int, skip: int = 0, limit: int = 100) -> List[TestCaseResponse]:
        """获取测试用例列表"""
        pass
    
    @abstractmethod
    async def get_cases_by_ids(self, case_ids: List[int]) -> List[TestCaseResponse]:
        """根据ID列表获取测试用例"""
        pass
    
    @abstractmethod
    async def create_suite(self, suite_data: TestSuiteCreate, user_id: int) -> TestSuiteResponse:
        """创建测试用例集"""
        pass
    
    @abstractmethod
    async def get_suite(self, suite_id: int) -> Optional[TestSuiteResponse]:
        """获取测试用例集"""
        pass
    
    @abstractmethod
    async def update_suite(self, suite_id: int, suite_data: TestSuiteUpdate) -> Optional[TestSuiteResponse]:
        """更新测试用例集"""
        pass
    
    @abstractmethod
    async def delete_suite(self, suite_id: int) -> bool:
        """删除测试用例集"""
        pass
    
    @abstractmethod
    async def list_suites(self, project_id: int, skip: int = 0, limit: int = 100) -> List[TestSuiteResponse]:
        """获取测试用例集列表"""
        pass
