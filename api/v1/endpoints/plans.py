"""
测试计划相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.database import get_session
from plan.service import PlanService
from plan.schemas import (
    TestPlanCreate, TestPlanUpdate, TestPlanResponse,
    ExecutionRecordResponse
)

router = APIRouter()


@router.post("/", response_model=TestPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_data: TestPlanCreate,
    user_id: int = 1,  # TODO: 从认证中获取
    session: AsyncSession = Depends(get_session)
):
    """创建测试计划"""
    plan_service = PlanService(session)
    plan = await plan_service.create_plan(plan_data, user_id)
    return plan


@router.get("/", response_model=List[TestPlanResponse])
async def list_plans(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    """获取测试计划列表"""
    plan_service = PlanService(session)
    plans = await plan_service.list_plans(project_id, skip, limit)
    return plans


@router.get("/{plan_id}", response_model=TestPlanResponse)
async def get_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_session)
):
    """获取测试计划详情"""
    plan_service = PlanService(session)
    plan = await plan_service.get_plan(plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试计划不存在"
        )
    
    return plan


@router.put("/{plan_id}", response_model=TestPlanResponse)
async def update_plan(
    plan_id: int,
    plan_data: TestPlanUpdate,
    session: AsyncSession = Depends(get_session)
):
    """更新测试计划"""
    plan_service = PlanService(session)
    plan = await plan_service.update_plan(plan_id, plan_data)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试计划不存在"
        )
    
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_session)
):
    """删除测试计划"""
    plan_service = PlanService(session)
    success = await plan_service.delete_plan(plan_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试计划不存在"
        )


@router.post("/{plan_id}/run", response_model=ExecutionRecordResponse, status_code=status.HTTP_201_CREATED)
async def run_plan(
    plan_id: int,
    user_id: int = 1,  # TODO: 从认证中获取
    session: AsyncSession = Depends(get_session)
):
    """执行测试计划"""
    plan_service = PlanService(session)
    try:
        execution = await plan_service.run_plan(plan_id, user_id)
        return execution
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# 执行记录管理
@router.get("/{plan_id}/executions", response_model=List[ExecutionRecordResponse])
async def list_executions(
    plan_id: int,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    """获取执行记录列表"""
    plan_service = PlanService(session)
    executions = await plan_service.list_executions(plan_id, skip, limit)
    return executions


@router.get("/executions/{execution_id}", response_model=ExecutionRecordResponse)
async def get_execution(
    execution_id: int,
    session: AsyncSession = Depends(get_session)
):
    """获取执行记录详情"""
    plan_service = PlanService(session)
    execution = await plan_service.get_execution(execution_id)
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="执行记录不存在"
        )
    
    return execution
