"""
测试计划相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TestPlanBase(BaseModel):
    """测试计划基础模型"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    suite_ids: List[int] = Field(default_factory=list)
    cron_expression: Optional[str] = None
    enabled: bool = True
    environment: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class TestPlanCreate(TestPlanBase):
    """测试计划创建模型"""
    project_id: int


class TestPlanUpdate(BaseModel):
    """测试计划更新模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    suite_ids: Optional[List[int]] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    environment: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class TestPlanResponse(TestPlanBase):
    """测试计划响应模型"""
    id: int
    project_id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }


class ExecutionRecordBase(BaseModel):
    """执行记录基础模型"""
    plan_id: int
    project_id: int
    trigger_type: str = "manual"


class ExecutionRecordCreate(ExecutionRecordBase):
    """执行记录创建模型"""
    pass


class ExecutionRecordResponse(BaseModel):
    """执行记录响应模型"""
    id: int
    plan_id: int
    project_id: int
    status: str
    triggered_by: int
    trigger_type: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    total_cases: int
    passed_cases: int
    failed_cases: int
    skipped_cases: int
    allure_results_path: Optional[str] = None
    report_url: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class ExecutionSummary(BaseModel):
    """执行摘要模型"""
    total: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    duration: int
