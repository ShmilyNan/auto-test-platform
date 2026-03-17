"""
用户相关的Pydantic模型
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., min_length=6, max_length=100)


class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    role: str
    is_superuser: bool = False
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }


class Token(BaseModel):
    """访问令牌模型"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """令牌数据模型"""
    user_id: Optional[int] = None
    username: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


class DeleteUserResponse(BaseModel):
    """删除用户响应模型"""
    success: bool
    message: str
    user_id: int
    username: Optional[str] = None
    detail: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "用户删除成功",
                "user_id": 1,
                "username": "testuser",
                "detail": "用户已被成功删除，所有关联数据已清理"
            }
        }


class DeleteUserError(BaseModel):
    """删除用户错误响应模型"""
    success: bool = False
    message: str
    error_code: str
    detail: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "用户删除失败",
                "error_code": "USER_NOT_FOUND",
                "detail": "用户ID 999 不存在"
            }
        }
