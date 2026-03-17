"""
统计数据模型
"""
from sqlalchemy import Column, Integer, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class DailyStats(Base):
    """每日统计记录"""
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # 用例统计
    total_cases = Column(Integer, default=0)
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    skipped_cases = Column(Integer, default=0)

    # 执行统计
    execution_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    # 关系
    project = relationship("Project", back_populates="daily_stats")

    def __repr__(self):
        return f"<DailyStats(project_id={self.project_id}, date={self.date})>"
