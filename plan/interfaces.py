"""
测试计划模块接口定义
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from plan.schemas import TestPlanCreate, TestPlanUpdate, TestPlanResponse, ExecutionRecordResponse


class PlanServiceInterface(ABC):
    """测试计划服务接口"""
    
    @abstractmethod
    async def create_plan(self, plan_data: TestPlanCreate, user_id: int) -> TestPlanResponse:
        """创建测试计划"""
        pass
    
    @abstractmethod
    async def get_plan(self, plan_id: int) -> Optional[TestPlanResponse]:
        """获取测试计划"""
        pass
    
    @abstractmethod
    async def update_plan(self, plan_id: int, plan_data: TestPlanUpdate) -> Optional[TestPlanResponse]:
        """更新测试计划"""
        pass
    
    @abstractmethod
    async def delete_plan(self, plan_id: int) -> bool:
        """删除测试计划"""
        pass
    
    @abstractmethod
    async def list_plans(self, project_id: int, skip: int = 0, limit: int = 100) -> List[TestPlanResponse]:
        """获取测试计划列表"""
        pass
    
    @abstractmethod
    async def run_plan(self, plan_id: int, user_id: int) -> ExecutionRecordResponse:
        """执行测试计划"""
        pass
    
    @abstractmethod
    async def get_execution(self, execution_id: int) -> Optional[ExecutionRecordResponse]:
        """获取执行记录"""
        pass
    
    @abstractmethod
    async def list_executions(self, plan_id: int, skip: int = 0, limit: int = 100) -> List[ExecutionRecordResponse]:
        """获取执行记录列表"""
        pass
