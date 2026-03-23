"""
测试计划相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from core.logger import logger
from core.database import get_session
from core.dependencies import get_current_user_id, check_project_permission
from plan.service import PlanService
from plan.repository import ExecutionRecordRepository
from plan.schemas import (
    TestPlanCreate, TestPlanUpdate, TestPlanResponse,
    ExecutionRecordResponse, ExecutionDetailResponse
)

router = APIRouter()


@router.post("/", response_model=TestPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_data: TestPlanCreate,
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """创建测试计划"""
    # 检查项目权限
    await check_project_permission(plan_data.project_id, current_user_id, session, "member")

    plan_service = PlanService(session)
    plan = await plan_service.create_plan(plan_data, current_user_id)
    return plan


@router.get("/", response_model=List[TestPlanResponse])
async def list_plans(
    project_id: int,
    page_num: int = Query(default=1, ge=1, description="页码，从1开始"),
    page_size: int = Query(default=1000, ge=1, le=10000, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取测试计划列表"""
    # 检查项目权限
    await check_project_permission(project_id, current_user_id, session, "viewer")

    plan_service = PlanService(session)
    plans = await plan_service.list_plans(project_id, page_num, page_size)
    return plans


@router.get("/{plan_id}", response_model=TestPlanResponse)
async def get_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取测试计划详情"""
    plan_service = PlanService(session)
    plan = await plan_service.get_plan(plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试计划不存在"
        )

    # 检查项目权限
    await check_project_permission(plan.project_id, current_user_id, session, "viewer")

    return plan


@router.put("/{plan_id}", response_model=TestPlanResponse)
async def update_plan(
    plan_id: int,
    plan_data: TestPlanUpdate,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """更新测试计划"""
    plan_service = PlanService(session)
    plan = await plan_service.get_plan(plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试计划不存在"
        )

    # 检查项目权限
    await check_project_permission(plan.project_id, current_user_id, session, "member")

    updated_plan = await plan_service.update_plan(plan_id, plan_data)
    return updated_plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """删除测试计划"""
    plan_service = PlanService(session)
    plan = await plan_service.get_plan(plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试计划不存在"
        )

    # 检查项目权限
    await check_project_permission(plan.project_id, current_user_id, session, "member")

    await plan_service.delete_plan(plan_id)


@router.post("/{plan_id}/run", response_model=ExecutionRecordResponse, status_code=status.HTTP_201_CREATED)
async def run_plan(
    plan_id: int,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """执行测试计划"""
    plan_service = PlanService(session)
    plan = await plan_service.get_plan(plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试计划不存在"
        )

    # 检查项目权限
    await check_project_permission(plan.project_id, current_user_id, session, "member")

    try:
        execution = await plan_service.run_plan(plan_id, current_user_id)

        # 异步执行测试任务
        from executor.tasks import dispatch_test_execution
        # dispatch_test_execution(execution.id, background_tasks)
        dispatch_type = dispatch_test_execution(execution.id, background_tasks)

        logger.info(f"测试任务已分发: execution_id={execution.id}, dispatch_type={dispatch_type}")

        return execution
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{plan_id}/run-sync", response_model=ExecutionDetailResponse)
async def run_plan_sync(
    plan_id: int,
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """同步执行测试计划（等待执行完成）"""
    plan_service = PlanService(session)
    plan = await plan_service.get_plan(plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试计划不存在"
        )

    # 检查项目权限
    await check_project_permission(plan.project_id, current_user_id, session, "member")

    try:
        execution = await plan_service.run_plan(plan_id, current_user_id)

        # 同步执行测试
        from executor.service import ExecutorService
        executor = ExecutorService()
        result = await executor.execute(execution.id)

        # 获取更新后的执行记录
        execution = await plan_service.get_execution(execution.id)
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
    page_num: int = Query(default=1, ge=1, description="页码，从1开始"),
    page_size: int = Query(default=1000, ge=1, le=10000, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取执行记录列表"""
    plan_service = PlanService(session)
    plan = await plan_service.get_plan(plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试计划不存在"
        )

    # 检查项目权限
    await check_project_permission(plan.project_id, current_user_id, session, "viewer")

    executions = await plan_service.list_executions(plan_id, page_num, page_size)
    return executions


@router.get("/executions/{execution_id}", response_model=ExecutionDetailResponse)
async def get_execution(
    execution_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取执行记录详情"""
    plan_service = PlanService(session)
    execution = await plan_service.get_execution(execution_id)

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="执行记录不存在"
        )

    # 检查项目权限
    await check_project_permission(execution.project_id, current_user_id, session, "viewer")

    return execution


@router.post("/executions/{execution_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_execution(
    execution_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """取消执行"""
    execution_repo = ExecutionRecordRepository(session)
    execution = await execution_repo.get_by_id(execution_id)

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="执行记录不存在"
        )

    # 检查项目权限
    await check_project_permission(execution.project_id, current_user_id, session, "member")

    # 实现取消执行逻辑
    if execution.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能取消待执行或执行中的任务"
        )

    # 更新执行状态为已取消
    from datetime import datetime, timezone
    execution.status = "cancelled"
    execution.end_time = datetime.now(timezone.utc)
    execution.error_message = "用户取消执行"

    # 如果有Celery任务正在运行，发送取消信号
    if execution.celery_task_id:
        try:
            from executor.tasks import execute_test_task
            from celery.result import AsyncResult

            # 撤销任务
            execute_test_task.AsyncResult(execution.celery_task_id).revoke(terminate=True)
            logger.info(f"已撤销Celery任务: {execution.celery_task_id}")
        except Exception as e:
            logger.warning(f"撤销Celery任务失败: {e}")

    await execution_repo.update(execution)

    return {"message": "执行已取消", "execution_id": execution_id}


@router.post("/executions/{execution_id}/rerun", response_model=ExecutionRecordResponse, status_code=status.HTTP_201_CREATED)
async def rerun_execution(
    execution_id: int,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """重新执行"""
    plan_service = PlanService(session)
    execution = await plan_service.get_execution(execution_id)

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="执行记录不存在"
        )

    # 检查项目权限
    await check_project_permission(execution.project_id, current_user_id, session, "member")

    # 创建新的执行记录
    new_execution = await plan_service.run_plan(execution.plan_id, current_user_id)

    # 优先投递到Celery；Broker不可用时回退到应用进程后台执行
    from executor.tasks import dispatch_test_execution
    dispatch_test_execution(new_execution.id, background_tasks)

    return new_execution
