"""
统计相关API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from core.database import get_session
from stats.service import StatsService

router = APIRouter()


@router.get("/project/{project_id}")
async def get_project_stats(
    project_id: int,
    session: AsyncSession = Depends(get_session)
):
    """获取项目统计"""
    stats_service = StatsService()
    stats = await stats_service.get_project_stats(project_id)
    return stats


@router.get("/project/{project_id}/execution-trend")
async def get_execution_trend(
    project_id: int,
    days: int = 7,
    session: AsyncSession = Depends(get_session)
):
    """获取执行趋势"""
    stats_service = StatsService()
    trend = await stats_service.get_execution_trend(project_id, days)
    return trend


@router.get("/project/{project_id}/pass-rate-trend")
async def get_pass_rate_trend(
    project_id: int,
    days: int = 7,
    session: AsyncSession = Depends(get_session)
):
    """获取通过率趋势"""
    stats_service = StatsService()
    trend = await stats_service.get_pass_rate_trend(project_id, days)
    return trend


@router.get("/project/{project_id}/cases")
async def get_case_stats(
    project_id: int,
    session: AsyncSession = Depends(get_session)
):
    """获取用例统计"""
    stats_service = StatsService()
    stats = await stats_service.get_case_stats(project_id)
    return stats


@router.get("/project/{project_id}/duration")
async def get_duration_stats(
    project_id: int,
    days: int = 7,
    session: AsyncSession = Depends(get_session)
):
    """获取执行时长统计"""
    stats_service = StatsService()
    stats = await stats_service.get_duration_stats(project_id, days)
    return stats
