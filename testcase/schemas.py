"""
测试用例相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TestCaseBase(BaseModel):
    """测试用例基础模型"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    method: str = Field(..., pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$")
    url: str = Field(..., max_length=500)
    headers: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    assertions: Optional[List[Dict[str, Any]]] = None
    extract: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    enabled: bool = True
    timeout: int = Field(default=30, ge=1, le=600)


class TestCaseCreate(TestCaseBase):
    """测试用例创建模型"""
    project_id: int


class TestCaseUpdate(BaseModel):
    """测试用例更新模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    method: Optional[str] = Field(None, pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$")
    url: Optional[str] = Field(None, max_length=500)
    headers: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    assertions: Optional[List[Dict[str, Any]]] = None
    extract: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    enabled: Optional[bool] = None
    timeout: Optional[int] = Field(None, ge=1, le=600)


class TestCaseResponse(TestCaseBase):
    """测试用例响应模型"""
    id: int
    project_id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TestSuiteBase(BaseModel):
    """测试用例集基础模型"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    case_ids: List[int] = Field(default_factory=list)


class TestSuiteCreate(TestSuiteBase):
    """测试用例集创建模型"""
    project_id: int


class TestSuiteUpdate(BaseModel):
    """测试用例集更新模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    case_ids: Optional[List[int]] = None


class TestSuiteResponse(TestSuiteBase):
    """测试用例集响应模型"""
    id: int
    project_id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TestSuiteWithCases(TestSuiteResponse):
    """测试用例集详情（包含用例）"""
    cases: List[TestCaseResponse] = []
