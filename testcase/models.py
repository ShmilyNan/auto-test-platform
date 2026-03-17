"""
测试用例数据模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from core.database import Base


class TestCase(Base):
    """测试用例表"""
    __tablename__ = "test_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # 请求配置
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE, etc.
    url = Column(String(500), nullable=False)
    headers = Column(JSON, nullable=True)  # {"Content-Type": "application/json"}
    params = Column(JSON, nullable=True)  # Query parameters
    body = Column(JSON, nullable=True)  # Request body
    
    # 断言和提取
    assertions = Column(JSON, nullable=True)  # [{"type": "status_code", "expected": 200}]
    extract = Column(JSON, nullable=True)  # [{"name": "token", "path": "$.data.token"}]
    
    # 其他配置
    tags = Column(JSON, nullable=True)  # ["smoke", "api"]
    enabled = Column(Boolean, default=True, nullable=False)
    timeout = Column(Integer, default=30)  # 超时时间（秒）
    
    # 元数据
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<TestCase(id={self.id}, name='{self.name}')>"


class TestSuite(Base):
    """测试用例集表"""
    __tablename__ = "test_suites"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    case_ids = Column(JSON, nullable=False)  # [1, 2, 3, ...]
    
    # 元数据
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<TestSuite(id={self.id}, name='{self.name}')>"
