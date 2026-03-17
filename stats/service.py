"""
统计服务层
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_

from stats.interfaces import StatsServiceInterface
from core.logger import get_logger
from core.database import async_session_maker

logger = get_logger(__name__)


class StatsService(StatsServiceInterface):
    """统计服务实现"""
    
    async def get_project_stats(self, project_id: int) -> Dict[str, Any]:
        """获取项目统计"""
        from testcase.models import TestCase, TestSuite
        from plan.models import TestPlan, ExecutionRecord
        
        async with async_session_maker() as session:
            # 用例数量
            case_count = await session.scalar(
                select(func.count(TestCase.id)).where(TestCase.project_id == project_id)
            )
            
            # 用例集数量
            suite_count = await session.scalar(
                select(func.count(TestSuite.id)).where(TestSuite.project_id == project_id)
            )
            
            # 计划数量
            plan_count = await session.scalar(
                select(func.count(TestPlan.id)).where(TestPlan.project_id == project_id)
            )
            
            # 执行记录数量
            execution_count = await session.scalar(
                select(func.count(ExecutionRecord.id)).where(ExecutionRecord.project_id == project_id)
            )
            
            # 最近7天的通过率
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_executions = await session.execute(
                select(ExecutionRecord)
                .where(and_(
                    ExecutionRecord.project_id == project_id,
                    ExecutionRecord.created_at >= seven_days_ago,
                    ExecutionRecord.status == "finished"
                ))
            )
            recent_execs = recent_executions.scalars().all()
            
            total_cases = sum(e.total_cases for e in recent_execs)
            passed_cases = sum(e.passed_cases for e in recent_execs)
            recent_pass_rate = round(passed_cases / total_cases * 100, 2) if total_cases > 0 else 0
            
            # 平均执行时长
            durations = [e.duration for e in recent_execs if e.duration]
            avg_duration = round(sum(durations) / len(durations), 2) if durations else 0
            
            return {
                "total_cases": case_count or 0,
                "total_suites": suite_count or 0,
                "total_plans": plan_count or 0,
                "total_executions": execution_count or 0,
                "recent_pass_rate": recent_pass_rate,
                "recent_avg_duration": avg_duration
            }
    
    async def get_execution_trend(self, project_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """获取执行趋势"""
        from plan.models import ExecutionRecord
        
        async with async_session_maker() as session:
            trend = []
            
            for i in range(days):
                date = datetime.utcnow().date() - timedelta(days=i)
                date_start = datetime.combine(date, datetime.min.time())
                date_end = datetime.combine(date, datetime.max.time())
                
                executions = await session.execute(
                    select(ExecutionRecord)
                    .where(and_(
                        ExecutionRecord.project_id == project_id,
                        ExecutionRecord.created_at >= date_start,
                        ExecutionRecord.created_at <= date_end,
                        ExecutionRecord.status == "finished"
                    ))
                )
                execs = executions.scalars().all()
                
                trend.append({
                    "date": date.isoformat(),
                    "total": sum(e.total_cases for e in execs),
                    "passed": sum(e.passed_cases for e in execs),
                    "failed": sum(e.failed_cases for e in execs),
                    "skipped": sum(e.skipped_cases for e in execs)
                })
            
            return list(reversed(trend))
    
    async def get_pass_rate_trend(self, project_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """获取通过率趋势"""
        from plan.models import ExecutionRecord
        
        async with async_session_maker() as session:
            trend = []
            
            for i in range(days):
                date = datetime.utcnow().date() - timedelta(days=i)
                date_start = datetime.combine(date, datetime.min.time())
                date_end = datetime.combine(date, datetime.max.time())
                
                executions = await session.execute(
                    select(ExecutionRecord)
                    .where(and_(
                        ExecutionRecord.project_id == project_id,
                        ExecutionRecord.created_at >= date_start,
                        ExecutionRecord.created_at <= date_end,
                        ExecutionRecord.status == "finished"
                    ))
                )
                execs = executions.scalars().all()
                
                total = sum(e.total_cases for e in execs)
                passed = sum(e.passed_cases for e in execs)
                pass_rate = round(passed / total * 100, 2) if total > 0 else 0
                
                trend.append({
                    "date": date.isoformat(),
                    "pass_rate": pass_rate
                })
            
            return list(reversed(trend))
    
    async def get_case_stats(self, project_id: int) -> Dict[str, Any]:
        """获取用例统计"""
        from testcase.models import TestCase
        
        async with async_session_maker() as session:
            # 总数
            total = await session.scalar(
                select(func.count(TestCase.id)).where(TestCase.project_id == project_id)
            )
            
            # 启用/禁用
            enabled = await session.scalar(
                select(func.count(TestCase.id)).where(
                    and_(TestCase.project_id == project_id, TestCase.enabled == True)
                )
            )
            
            disabled = await session.scalar(
                select(func.count(TestCase.id)).where(
                    and_(TestCase.project_id == project_id, TestCase.enabled == False)
                )
            )
            
            # 按请求方法统计
            method_result = await session.execute(
                select(TestCase.method, func.count(TestCase.id))
                .where(TestCase.project_id == project_id)
                .group_by(TestCase.method)
            )
            by_method = {row[0]: row[1] for row in method_result}
            
            # 按标签统计（需要遍历所有用例）
            cases = await session.execute(
                select(TestCase).where(TestCase.project_id == project_id)
            )
            all_cases = cases.scalars().all()
            
            by_tag = {}
            for case in all_cases:
                if case.tags:
                    for tag in case.tags:
                        by_tag[tag] = by_tag.get(tag, 0) + 1
            
            return {
                "total": total or 0,
                "enabled": enabled or 0,
                "disabled": disabled or 0,
                "by_method": by_method,
                "by_tag": by_tag
            }
    
    async def get_duration_stats(self, project_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """获取执行时长统计"""
        from plan.models import ExecutionRecord, TestPlan
        
        async with async_session_maker() as session:
            seven_days_ago = datetime.utcnow() - timedelta(days=days)
            
            result = await session.execute(
                select(ExecutionRecord, TestPlan)
                .join(TestPlan, ExecutionRecord.plan_id == TestPlan.id)
                .where(and_(
                    ExecutionRecord.project_id == project_id,
                    ExecutionRecord.created_at >= seven_days_ago,
                    ExecutionRecord.status == "finished"
                ))
                .order_by(ExecutionRecord.created_at.desc())
                .limit(20)
            )
            
            stats = []
            for record, plan in result:
                stats.append({
                    "execution_id": record.id,
                    "plan_name": plan.name,
                    "duration": record.duration or 0,
                    "start_time": record.start_time.isoformat() if record.start_time else None,
                    "status": record.status
                })
            
            return stats
