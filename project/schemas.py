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


class DeleteProjectResponse(BaseModel):
    """删除项目响应模型"""
    success: bool
    message: str
    project_id: int
    project_name: Optional[str] = None
    detail: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "项目删除成功",
                "project_id": 1,
                "project_name": "test_project",
                "detail": "项目已被成功删除，所有关联数据已清理"
            }
        }


class DeleteProjectError(BaseModel):
    """删除项目错误响应模型"""
    success: bool = False
    message: str
    error_code: str
    detail: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "项目删除失败",
                "error_code": "PROJECT_NOT_FOUND",
                "detail": "项目ID 999 不存在"
            }
        }