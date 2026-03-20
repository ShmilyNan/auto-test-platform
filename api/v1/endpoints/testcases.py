"""
测试用例相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from core.database import get_session
from core.dependencies import get_current_user_id, check_project_permission
from testcase.service import TestCaseService
from testcase.schemas import (
    TestCaseCreate, TestCaseUpdate, TestCaseResponse,
    TestSuiteCreate, TestSuiteUpdate, TestSuiteResponse
)

router = APIRouter()


# 测试用例管理
@router.post("/cases", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: TestCaseCreate,
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """创建测试用例"""
    # 检查项目权限
    await check_project_permission(case_data.project_id, current_user_id, session, "member")

    case_service = TestCaseService(session)
    case = await case_service.create_case(case_data, current_user_id)
    return case


@router.get("/cases", response_model=List[TestCaseResponse])
async def list_cases(
    project_id: int,
    page_num: int = Query(default=1, ge=1, description="页码，从1开始"),
    page_size: int = Query(default=1000, ge=1, le=10000, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取测试用例列表"""
    # 检查项目权限
    await check_project_permission(project_id, current_user_id, session, "viewer")

    case_service = TestCaseService(session)
    cases = await case_service.list_cases(project_id, page_size, page_num)
    return cases


@router.get("/cases/{case_id}", response_model=TestCaseResponse)
async def get_case(
    case_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取测试用例详情"""
    case_service = TestCaseService(session)
    case = await case_service.get_case(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例不存在"
        )

    # 检查项目权限
    await check_project_permission(case.project_id, current_user_id, session, "viewer")

    return case


@router.put("/cases/{case_id}", response_model=TestCaseResponse)
async def update_case(
    case_id: int,
    case_data: TestCaseUpdate,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """更新测试用例"""
    case_service = TestCaseService(session)
    case = await case_service.get_case(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例不存在"
        )

    # 检查项目权限
    await check_project_permission(case.project_id, current_user_id, session, "member")

    updated_case = await case_service.update_case(case_id, case_data)
    return updated_case


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """删除测试用例"""
    case_service = TestCaseService(session)
    case = await case_service.get_case(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例不存在"
        )

    # 检查项目权限
    await check_project_permission(case.project_id, current_user_id, session, "member")

    await case_service.delete_case(case_id)


@router.post("/cases/batch", response_model=List[TestCaseResponse], status_code=status.HTTP_201_CREATED)
async def batch_create_cases(
    cases_data: List[TestCaseCreate],
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """批量创建测试用例"""
    if not cases_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用例列表不能为空"
        )

    # 检查所有项目的权限
    project_ids = set(case.project_id for case in cases_data)
    for project_id in project_ids:
        await check_project_permission(project_id, current_user_id, session, "member")

    case_service = TestCaseService(session)
    created_cases = []
    for case_data in cases_data:
        case = await case_service.create_case(case_data, current_user_id)
        created_cases.append(case)

    return created_cases


# 测试用例集管理
@router.post("/suites", response_model=TestSuiteResponse, status_code=status.HTTP_201_CREATED)
async def create_suite(
    suite_data: TestSuiteCreate,
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """创建测试用例集"""
    # 检查项目权限
    await check_project_permission(suite_data.project_id, current_user_id, session, "member")

    case_service = TestCaseService(session)
    suite = await case_service.create_suite(suite_data, current_user_id)
    return suite


@router.get("/suites", response_model=List[TestSuiteResponse])
async def list_suites(
    project_id: int,
    page_num: int = Query(default=1, ge=1, description="页码，从1开始"),
    page_size: int = Query(default=1000, ge=1, le=10000, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取测试用例集列表"""
    # 检查项目权限
    await check_project_permission(project_id, current_user_id, session, "viewer")

    case_service = TestCaseService(session)
    suites = await case_service.list_suites(project_id, page_num, page_size)
    return suites


@router.get("/suites/{suite_id}", response_model=TestSuiteResponse)
async def get_suite(
    suite_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取测试用例集详情"""
    case_service = TestCaseService(session)
    suite = await case_service.get_suite(suite_id)

    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例集不存在"
        )

    # 检查项目权限
    await check_project_permission(suite.project_id, current_user_id, session, "viewer")

    return suite


@router.put("/suites/{suite_id}", response_model=TestSuiteResponse)
async def update_suite(
    suite_id: int,
    suite_data: TestSuiteUpdate,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """更新测试用例集"""
    case_service = TestCaseService(session)
    suite = await case_service.get_suite(suite_id)

    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例集不存在"
        )

    # 检查项目权限
    await check_project_permission(suite.project_id, current_user_id, session, "member")

    updated_suite = await case_service.update_suite(suite_id, suite_data)
    return updated_suite


@router.delete("/suites/{suite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_suite(
    suite_id: int,
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """删除测试用例集"""
    case_service = TestCaseService(session)
    suite = await case_service.get_suite(suite_id)

    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例集不存在"
        )

    # 检查项目权限
    await check_project_permission(suite.project_id, current_user_id, session, "member")

    await case_service.delete_suite(suite_id)


# 用例导入导出
@router.post("/cases/import", response_model=List[TestCaseResponse], status_code=status.HTTP_201_CREATED)
async def import_cases(
    project_id: int,
    cases_data: List[dict],
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """导入测试用例"""
    # 检查项目权限
    await check_project_permission(project_id, current_user_id, session, "member")

    case_service = TestCaseService(session)
    imported_cases = []

    for case_dict in cases_data:
        case_create = TestCaseCreate(project_id=project_id, **case_dict)
        case = await case_service.create_case(case_create, current_user_id)
        imported_cases.append(case)

    return imported_cases


@router.get("/cases/export")
async def export_cases(
    project_id: int,
    case_ids: str = None,  # 逗号分隔的用例ID
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """导出测试用例"""
    # 检查项目权限
    await check_project_permission(project_id, current_user_id, session, "viewer")

    case_service = TestCaseService(session)

    if case_ids:
        ids = [int(id) for id in case_ids.split(",")]
        cases = await case_service.get_cases_by_ids(ids)
    else:
        cases = await case_service.list_cases(project_id, page_size=1000)

    return {"cases": cases}
