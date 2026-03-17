"""
项目相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProjectBase(BaseModel):
    """项目基础模型"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    """项目创建模型"""
    pass


class ProjectUpdate(BaseModel):
    """项目更新模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectResponse(ProjectBase):
    """项目响应模型"""
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

class ProjectMemberBase(BaseModel):
    """项目成员基础模型"""
    user_id: int
    role: str = "member"


class ProjectMemberCreate(ProjectMemberBase):
    """项目成员创建模型"""
    pass


class ProjectMemberResponse(ProjectMemberBase):
    """项目成员响应模型"""
    id: int
    project_id: int
    joined_at: datetime

    model_config = {
        "from_attributes": True
    }

class ProjectWithMembers(ProjectResponse):
    """项目详情（包含成员）"""
    members: List[ProjectMemberResponse] = []
