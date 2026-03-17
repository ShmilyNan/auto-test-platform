"""
测试计划数据访问层
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from plan.models import TestPlan, ExecutionRecord


class TestPlanRepository:
    """测试计划仓库"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, plan: TestPlan) -> TestPlan:
        """创建测试计划"""
        self.session.add(plan)
        await self.session.commit()
        await self.session.refresh(plan)
        return plan
    
    async def get_by_id(self, plan_id: int) -> Optional[TestPlan]:
        """根据ID获取测试计划"""
        result = await self.session.execute(
            select(TestPlan).where(TestPlan.id == plan_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, plan: TestPlan) -> TestPlan:
        """更新测试计划"""
        await self.session.commit()
        await self.session.refresh(plan)
        return plan
    
    async def delete(self, plan: TestPlan) -> bool:
        """删除测试计划"""
        await self.session.delete(plan)
        await self.session.commit()
        return True
    
    async def list_by_project(self, project_id: int, skip: int = 0, limit: int = 100) -> List[TestPlan]:
        """获取项目的测试计划列表"""
        result = await self.session.execute(
            select(TestPlan)
            .where(TestPlan.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()


class ExecutionRecordRepository:
    """执行记录仓库"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, record: ExecutionRecord) -> ExecutionRecord:
        """创建执行记录"""
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record
    
    async def get_by_id(self, record_id: int) -> Optional[ExecutionRecord]:
        """根据ID获取执行记录"""
        result = await self.session.execute(
            select(ExecutionRecord).where(ExecutionRecord.id == record_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, record: ExecutionRecord) -> ExecutionRecord:
        """更新执行记录"""
        await self.session.commit()
        await self.session.refresh(record)
        return record
    
    async def list_by_plan(self, plan_id: int, skip: int = 0, limit: int = 100) -> List[ExecutionRecord]:
        """获取测试计划的执行记录列表"""
        result = await self.session.execute(
            select(ExecutionRecord)
            .where(ExecutionRecord.plan_id == plan_id)
            .order_by(ExecutionRecord.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
