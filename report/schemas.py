"""
报告相关的Pydantic模型
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class ReportSummary(BaseModel):
    """报告摘要"""
    total: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    duration: int


class TestCaseResult(BaseModel):
    """测试用例结果"""
    name: str
    status: str
    duration: float
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None


class ReportDetail(BaseModel):
    """报告详情"""
    execution_id: int
    plan_id: int
    plan_name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    summary: ReportSummary
    test_results: List[TestCaseResult]
    report_url: Optional[str] = None
