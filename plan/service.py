"""
测试计划服务层
"""
import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from plan.interfaces import PlanServiceInterface
from plan.models import TestPlan, ExecutionRecord
from plan.schemas import (
    TestPlanCreate, TestPlanUpdate, TestPlanResponse,
    ExecutionRecordResponse, ExecutionDetailResponse,
    ExecutionResultResponse
)
from plan.repository import TestPlanRepository, ExecutionRecordRepository, ExecutionResultRepository
from core.logger import logger
from core.config import settings


class PlanService(PlanServiceInterface):
    """测试计划服务实现"""
    
    def __init__(self, session: AsyncSession):
        self.plan_repo = TestPlanRepository(session)
        self.execution_repo = ExecutionRecordRepository(session)
        self.execution_result_repo = ExecutionResultRepository(session)
    
    async def create_plan(self, plan_data: TestPlanCreate, user_id: int) -> TestPlanResponse:
        """创建测试计划"""
        plan = TestPlan(
            project_id=plan_data.project_id,
            name=plan_data.name,
            description=plan_data.description,
            suite_ids=plan_data.suite_ids,
            cron_expression=plan_data.cron_expression,
            enabled=plan_data.enabled,
            environment=plan_data.environment,
            config=plan_data.config,
            created_by=user_id
        )
        
        created_plan = await self.plan_repo.create(plan)
        logger.info(f"创建测试计划成功: {created_plan.name}")
        
        return TestPlanResponse.model_validate(created_plan)
    
    async def get_plan(self, plan_id: int) -> Optional[TestPlanResponse]:
        """获取测试计划"""
        plan = await self.plan_repo.get_by_id(plan_id)
        if plan:
            return TestPlanResponse.model_validate(plan)
        return None
    
    async def update_plan(self, plan_id: int, plan_data: TestPlanUpdate) -> Optional[TestPlanResponse]:
        """更新测试计划"""
        plan = await self.plan_repo.get_by_id(plan_id)
        if not plan:
            return None
        
        # 更新字段
        update_data = plan_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plan, field, value)
        
        updated_plan = await self.plan_repo.update(plan)
        logger.info(f"更新测试计划成功: {updated_plan.name}")
        
        return TestPlanResponse.model_validate(updated_plan)
    
    async def delete_plan(self, plan_id: int) -> bool:
        """删除测试计划"""
        plan = await self.plan_repo.get_by_id(plan_id, include_deleted=True)
        if not plan:
            return False
        
        await self.plan_repo.soft_delete(plan)
        logger.info(f"删除测试计划成功: {plan.name}")
        
        return True
    
    async def list_plans(self, project_id: int, page_num: int = 1, page_size: int = 1000) -> List[TestPlanResponse]:
        """获取测试计划列表（分页）"""
        plans = await self.plan_repo.list_by_project(project_id, page_num, page_size)
        return [TestPlanResponse.model_validate(plan) for plan in plans]
    
    async def run_plan(self, plan_id: int, user_id: int) -> ExecutionRecordResponse:
        """执行测试计划"""
        # 获取计划
        plan = await self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise ValueError("测试计划不存在")

        # 创建执行记录
        execution = ExecutionRecord(
            plan_id=plan_id,
            project_id=plan.project_id,
            status="pending",
            triggered_by=user_id,
            trigger_type="manual",
            allure_results_path=f"{settings.ALLURE_RESULTS_DIR}/{uuid.uuid4()}"
        )
        
        created_execution = await self.execution_repo.create(execution)
        logger.info(f"创建执行记录成功: execution_id={created_execution.id}, plan_id={plan_id}")
        
        # 发送任务到Celery队列异步执行
        from executor.tasks import execute_test_task
        task = execute_test_task.delay(created_execution.id)

        # 保存Celery任务ID
        created_execution.celery_task_id = task.id
        await self.execution_repo.update(created_execution)
        
        return ExecutionRecordResponse.model_validate(created_execution)
    
    async def get_execution(self, execution_id: int) -> Optional[ExecutionDetailResponse]:
        """获取执行记录"""
        execution = await self.execution_repo.get_by_id(execution_id)
        if execution:
            results = await self.execution_result_repo.list_by_execution(execution_id)
            return ExecutionDetailResponse(
                **ExecutionRecordResponse.model_validate(execution).model_dump(),
                results=[ExecutionResultResponse.model_validate(result) for result in results]
            )
        return None

    async def list_executions(self, plan_id: int, page_num: int = 1, page_size: int = 1000) -> List[
        ExecutionRecordResponse]:
        """获取执行记录列表（分页）"""
        executions = await self.execution_repo.list_by_plan(plan_id, page_num, page_size)
        return [ExecutionRecordResponse.model_validate(execution) for execution in executions]
