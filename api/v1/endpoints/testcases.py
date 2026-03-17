"""
测试用例相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.database import get_session
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
    user_id: int = 1,  # TODO: 从认证中获取
    session: AsyncSession = Depends(get_session)
):
    """创建测试用例"""
    case_service = TestCaseService(session)
    case = await case_service.create_case(case_data, user_id)
    return case


@router.get("/cases", response_model=List[TestCaseResponse])
async def list_cases(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    """获取测试用例列表"""
    case_service = TestCaseService(session)
    cases = await case_service.list_cases(project_id, skip, limit)
    return cases


@router.get("/cases/{case_id}", response_model=TestCaseResponse)
async def get_case(
    case_id: int,
    session: AsyncSession = Depends(get_session)
):
    """获取测试用例详情"""
    case_service = TestCaseService(session)
    case = await case_service.get_case(case_id)
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例不存在"
        )
    
    return case


@router.put("/cases/{case_id}", response_model=TestCaseResponse)
async def update_case(
    case_id: int,
    case_data: TestCaseUpdate,
    session: AsyncSession = Depends(get_session)
):
    """更新测试用例"""
    case_service = TestCaseService(session)
    case = await case_service.update_case(case_id, case_data)
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例不存在"
        )
    
    return case


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: int,
    session: AsyncSession = Depends(get_session)
):
    """删除测试用例"""
    case_service = TestCaseService(session)
    success = await case_service.delete_case(case_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例不存在"
        )


# 测试用例集管理
@router.post("/suites", response_model=TestSuiteResponse, status_code=status.HTTP_201_CREATED)
async def create_suite(
    suite_data: TestSuiteCreate,
    user_id: int = 1,  # TODO: 从认证中获取
    session: AsyncSession = Depends(get_session)
):
    """创建测试用例集"""
    case_service = TestCaseService(session)
    suite = await case_service.create_suite(suite_data, user_id)
    return suite


@router.get("/suites", response_model=List[TestSuiteResponse])
async def list_suites(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    """获取测试用例集列表"""
    case_service = TestCaseService(session)
    suites = await case_service.list_suites(project_id, skip, limit)
    return suites


@router.get("/suites/{suite_id}", response_model=TestSuiteResponse)
async def get_suite(
    suite_id: int,
    session: AsyncSession = Depends(get_session)
):
    """获取测试用例集详情"""
    case_service = TestCaseService(session)
    suite = await case_service.get_suite(suite_id)
    
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例集不存在"
        )
    
    return suite


@router.put("/suites/{suite_id}", response_model=TestSuiteResponse)
async def update_suite(
    suite_id: int,
    suite_data: TestSuiteUpdate,
    session: AsyncSession = Depends(get_session)
):
    """更新测试用例集"""
    case_service = TestCaseService(session)
    suite = await case_service.update_suite(suite_id, suite_data)
    
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例集不存在"
        )
    
    return suite


@router.delete("/suites/{suite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_suite(
    suite_id: int,
    session: AsyncSession = Depends(get_session)
):
    """删除测试用例集"""
    case_service = TestCaseService(session)
    success = await case_service.delete_suite(suite_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例集不存在"
        )
