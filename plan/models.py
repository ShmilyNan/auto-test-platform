"""
测试计划数据模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from core.database import Base


class TestPlan(Base):
    """测试计划表"""
    __tablename__ = "test_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # 用例集配置
    suite_ids = Column(JSON, nullable=False)  # [1, 2, 3, ...]
    
    # 定时任务配置
    cron_expression = Column(String(100), nullable=True)  # cron表达式
    enabled = Column(Boolean, default=True, nullable=False)
    
    # 执行配置
    environment = Column(String(50), nullable=True)  # dev, test, prod
    config = Column(JSON, nullable=True)  # 其他配置
    
    # 元数据
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<TestPlan(id={self.id}, name='{self.name}')>"


class ExecutionRecord(Base):
    """执行记录表"""
    __tablename__ = "execution_records"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 执行状态
    status = Column(String(20), default="pending", nullable=False)  # pending, running, finished, failed
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    trigger_type = Column(String(20), default="manual", nullable=False)  # manual, schedule
    celery_task_id = Column(String(100), nullable=True)  # Celery任务ID，用于取消任务

    # 执行时间
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # 执行时长（秒）
    
    # 执行结果
    total_cases = Column(Integer, default=0)
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    skipped_cases = Column(Integer, default=0)
    
    # 报告路径
    allure_results_path = Column(String(500), nullable=True)
    report_url = Column(String(500), nullable=True)
    
    # 详细信息
    summary = Column(JSON, nullable=True)  # 执行摘要
    error_message = Column(Text, nullable=True)
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<ExecutionRecord(id={self.id}, plan_id={self.plan_id}, status='{self.status}')>"


class ExecutionResult(Base):
    """执行结果详情表 - 存储每个测试用例的执行结果"""
    __tablename__ = "execution_results"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("execution_records.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    case_name = Column(String(200), nullable=False)  # 用例名称快照

    # 执行状态
    status = Column(String(20), default="pending", nullable=False)  # pending, passed, failed, skipped
    duration = Column(Integer, nullable=True)  # 执行时长（毫秒）

    # 请求响应详情
    request = Column(JSON, nullable=True)  # 请求快照
    response = Column(JSON, nullable=True)  # 响应快照

    # 断言结果
    assertions = Column(JSON,
                        nullable=True)  # [{"type": "status_code", "expected": 200, "actual": 200, "passed": true}]

    # 错误信息
    error_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)

    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ExecutionResult(id={self.id}, case_name='{self.case_name}', status='{self.status}')>"