"""
API v1路由
"""
from fastapi import APIRouter
from api.v1.endpoints import auth, users, projects, testcases, plans, reports, stats

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(projects.router, prefix="/projects", tags=["项目"])
api_router.include_router(testcases.router, prefix="/testcases", tags=["测试用例"])
api_router.include_router(plans.router, prefix="/plans", tags=["测试计划"])
api_router.include_router(reports.router, prefix="/reports", tags=["报告"])
api_router.include_router(stats.router, prefix="/stats", tags=["统计"])
