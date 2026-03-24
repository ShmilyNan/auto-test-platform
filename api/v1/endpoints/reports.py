"""
报告相关API
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from report.service import ReportService

router = APIRouter()


@router.post("/generate/{execution_id}")
async def generate_report(
    execution_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """生成报告"""
    report_service = ReportService()
    try:
        result = await report_service.generate_report(execution_id, str(request.base_url).rstrip("/"))
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{execution_id}")
async def get_report(
    execution_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """获取报告"""
    report_service = ReportService()
    report = await report_service.get_report(execution_id, str(request.base_url).rstrip("/"))
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在"
        )
    
    return report


@router.post("/archive/{execution_id}")
async def archive_report(
    execution_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """归档报告"""
    report_service = ReportService()
    try:
        result = await report_service.generate_report(execution_id, str(request.base_url).rstrip("/"))
        archive_path = await report_service.archive_report(execution_id, result["report_dir"])
        return {"archive_path": archive_path}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
