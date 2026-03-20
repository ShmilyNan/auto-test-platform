"""
测试计划数据访问层
"""
from datetime import datetime, timezone
from http.cookiejar import offset_from_tz_string
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from plan.models import TestPlan, ExecutionRecord, ExecutionResult


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
    
    async def get_by_id(self, plan_id: int, include_deleted: bool = False) -> Optional[TestPlan]:
        """根据ID获取测试计划"""
        query = select(TestPlan).where(TestPlan.id == plan_id)
        if not include_deleted:
            query = query.where(TestPlan.is_deleted == False)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update(self, plan: TestPlan) -> TestPlan:
        """更新测试计划"""
        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def soft_delete(self, plan: TestPlan) -> bool:
        """软删除测试计划"""
        plan.is_deleted = True
        plan.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    async def delete(self, plan: TestPlan) -> bool:
        """物理删除测试计划"""
        await self.session.delete(plan)
        await self.session.commit()
        return True
    
    async def list_by_project(self, project_id: int, page_num: int = 1, page_size: int = 1000) -> List[TestPlan]:
        """获取项目的测试计划列表"""
        offset = (page_num - 1) * page_size
        result = await self.session.execute(
            select(TestPlan)
            .where(
                TestPlan.project_id == project_id,
                TestPlan.is_deleted == False
            )
            .offset(offset)
            .limit(page_size)
        )
        return result.scalars().all()

    async def count_by_project(self, project_id: int) -> int:
        """获取项目的测试计划总数"""
        result = await self.session.execute(
            select(func.count()).select_from(TestPlan).where(
                TestPlan.project_id == project_id,
                TestPlan.is_deleted == False
            )
        )
        return result.scalar()


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
    
    async def list_by_plan(self, plan_id: int, page_num: int = 1, page_size: int = 1000) -> List[ExecutionRecord]:
        """获取测试计划的执行记录列表（分页）"""
        offset = (page_num - 1) * page_size
        result = await self.session.execute(
            select(ExecutionRecord)
            .where(ExecutionRecord.plan_id == plan_id)
            .order_by(ExecutionRecord.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return result.scalars().all()

    async def count_by_plan(self, plan_id: int) -> int:
        """获取测试计划的执行记录总数"""
        result = await self.session.execute(
            select(func.count()).select_from(ExecutionRecord).where(
                ExecutionRecord.plan_id == plan_id
            )
        )
        return result.scalar()


class ExecutionResultRepository:
    """执行结果详情仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, result: ExecutionResult) -> ExecutionResult:
        """创建单条执行结果"""
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def create_batch(self, results: List[ExecutionResult]) -> List[ExecutionResult]:
        """批量创建执行结果"""
        self.session.add_all(results)
        await self.session.commit()
        for result in results:
            await self.session.refresh(result)
        return results

    async def list_by_execution(self, execution_id: int) -> List[ExecutionResult]:
        """根据执行记录获取测试结果详情"""
        result = await self.session.execute(
            select(ExecutionResult)
            .where(ExecutionResult.execution_id == execution_id)
            .order_by(ExecutionResult.id.asc())
        )
        return result.scalars().all()