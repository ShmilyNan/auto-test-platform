"""
统计相关的Pydantic模型
"""
from pydantic import BaseModel
from typing import Dict
from datetime import datetime


class ProjectStats(BaseModel):
    """项目统计"""
    total_cases: int
    total_suites: int
    total_plans: int
    total_executions: int
    recent_pass_rate: float
    recent_avg_duration: float


class ExecutionTrend(BaseModel):
    """执行趋势"""
    date: str
    total: int
    passed: int
    failed: int
    skipped: int


class PassRateTrend(BaseModel):
    """通过率趋势"""
    date: str
    pass_rate: float


class CaseStats(BaseModel):
    """用例统计"""
    total: int
    enabled: int
    disabled: int
    by_method: Dict[str, int]
    by_tag: Dict[str, int]


class DurationStats(BaseModel):
    """执行时长统计"""
    execution_id: int
    plan_name: str
    duration: int
    start_time: datetime
    status: str
