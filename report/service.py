"""
报告服务层
"""
from typing import Dict, Any, Optional
import os
import subprocess
import shutil
from report.interfaces import ReportServiceInterface
from core.logger import logger
from core.config import settings
from core.database import async_session_maker


class ReportService(ReportServiceInterface):
    """报告服务实现"""

    def _build_allure_dirs(self, allure_subdir: str) -> tuple[str, str]:
        """构建 Allure 结果目录和 HTML 报告目录。"""
        allure_dir = os.path.join(settings.ALLURE_RESULTS_DIR, allure_subdir)
        report_dir = os.path.join(settings.ALLURE_REPORT_DIR, allure_subdir)
        return allure_dir, report_dir

    def _build_report_path(self, allure_subdir: str) -> str:
        """构建静态报告相对访问路径。"""
        return f"/reports/{allure_subdir}/index.html"

    def _build_report_url(self, allure_subdir: str, base_url: Optional[str] = None) -> str:
        """构建静态报告访问地址。"""
        report_path = (settings.COZE_PROJECT_DOMAIN_DEFAULT or "").rstrip("/")
        domain = (base_url or settings.COZE_PROJECT_DOMAIN_DEFAULT or "").rstrip("/")
        if domain:
            return f"{domain}{report_path}"
        return report_path

    async def generate_report(self, execution_id: int, base_url: Optional[str] = None) -> Dict[str, Any]:
        """生成报告"""
        from plan.repository import ExecutionRecordRepository
        
        async with async_session_maker() as session:
            execution_repo = ExecutionRecordRepository(session)
            
            # 获取执行记录
            execution = await execution_repo.get_by_id(execution_id)
            if not execution:
                raise ValueError(f"执行记录不存在: {execution_id}")
            
            # 检查Allure结果目录
            # execution.allure_results_path 保存的是相对路径（UUID子目录名）
            allure_subdir = execution.allure_results_path
            if not allure_subdir:
                raise ValueError(f"执行记录没有Allure结果路径")

            # 构建完整路径
            allure_dir, report_dir = self._build_allure_dirs(allure_subdir)
            logger.info(f"检查Allure结果目录: {allure_dir}")
            logger.info(f"ALLURE_RESULTS_DIR配置: {settings.ALLURE_RESULTS_DIR}")
            logger.info(f"ALLURE_REPORT_DIR配置: {settings.ALLURE_REPORT_DIR}")
            logger.info(f"相对子目录: {allure_subdir}")

            if not os.path.exists(allure_dir):
                # 列出可能的目录帮助调试
                base_dir = settings.ALLURE_RESULTS_DIR
                existing_dirs = os.listdir(base_dir) if os.path.exists(base_dir) else []
                raise ValueError(
                    f"Allure结果目录不存在: {allure_dir}\n"
                    f"基础目录: {base_dir}\n"
                    f"期望子目录: {allure_subdir}\n"
                    f"现有子目录: {existing_dirs}"
                )

            # 检查目录内容
            allure_files = os.listdir(allure_dir)
            logger.info(f"Allure目录文件数量: {len(allure_files)}")
            
            # 生成HTML报告
            report_url = await self.generate_allure_html(
                allure_dir,
                report_dir,
                self._build_report_url(allure_subdir, base_url),
            )
            
            # 更新执行记录
            execution.report_url = self._build_report_path(allure_subdir)
            await execution_repo.update(execution)
            
            logger.info(f"生成报告成功: execution_id={execution_id}, report_url={report_url}")
            
            return {
                "execution_id": execution_id,
                "report_url": report_url,
                "report_dir": report_dir,
                "allure_dir": allure_dir
            }
    
    async def get_report(self, execution_id: int, base_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取报告"""
        from plan.repository import ExecutionRecordRepository, ExecutionResultRepository
        
        async with async_session_maker() as session:
            execution_repo = ExecutionRecordRepository(session)
            execution_result_repo = ExecutionResultRepository(session)
            
            # 获取执行记录
            execution = await execution_repo.get_by_id(execution_id)
            if not execution:
                return None

            execution_results = await execution_result_repo.list_by_execution(execution_id)
            report_url = None
            if execution.allure_results_path:
                report_url = self._build_report_url(execution.allure_results_path, base_url)
            elif execution.report_url:
                report_url = execution.report_url

            return {
                "execution_id": execution_id,
                "plan_id": execution.plan_id,
                "status": execution.status,
                "start_time": execution.start_time.isoformat() if execution.start_time else None,
                "end_time": execution.end_time.isoformat() if execution.end_time else None,
                "duration": execution.duration,
                "summary": execution.summary,
                "report_url": report_url,
                "test_results": [
                    {
                        "case_id": result.case_id,
                        "name": result.case_name,
                        "status": result.status,
                        "duration": result.duration,
                        "request": result.request,
                        "response": result.response,
                        "assertions": result.assertions,
                        "error_message": result.error_message,
                        "stack_trace": result.stack_trace,
                    }
                    for result in execution_results
                ]
            }
    
    async def generate_allure_html(self, allure_dir: str, output_dir: str, report_url: str) -> str:
        """生成Allure HTML报告"""
        os.makedirs(os.path.dirname(output_dir), exist_ok=True)

        logger.info(f"生成Allure报告: allure_dir={allure_dir}, output_dir={output_dir}")

        # 执行Allure命令生成报告
        cmd = [
            "allure",
            "generate",
            allure_dir,
            "-o",
            output_dir,
            "--clean"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode != 0:
                logger.error(f"Allure报告生成失败: {result.stderr}")
                raise RuntimeError(f"Allure报告生成失败:{result.stderr.strip()}")

            report_index_path = os.path.join(output_dir, "index.html")
            if not os.path.isfile(report_index_path):
                raise RuntimeError(f"Allure报告生成后缺少首页文件: {report_index_path}")

            logger.info(f"Allure报告生成成功: {output_dir}")
            return report_url
            
        except subprocess.TimeoutExpired:
            logger.error("Allure报告生成超时")
            raise RuntimeError("Allure报告生成超时")
        except FileNotFoundError:
            logger.error("Allure命令未安装，无法生成HTML报告")
            raise RuntimeError("Allure命令未安装，无法生成HTML报告")
    
    async def archive_report(self, execution_id: int, report_dir: str) -> str:
        """归档报告"""
        from plan.repository import ExecutionRecordRepository
        
        async with async_session_maker() as session:
            execution_repo = ExecutionRecordRepository(session)
            
            # 获取执行记录
            execution = await execution_repo.get_by_id(execution_id)
            if not execution:
                raise ValueError(f"执行记录不存在: {execution_id}")
            
            # 创建归档目录
            archive_dir = os.path.join(settings.STORAGE_PATH, "archive", f"execution_{execution_id}")
            os.makedirs(archive_dir, exist_ok=True)
            
            # 复制报告文件
            if os.path.exists(report_dir):
                shutil.copytree(report_dir, archive_dir, dirs_exist_ok=True)
            
            # 创建压缩包
            archive_path = shutil.make_archive(
                archive_dir,
                'zip',
                report_dir
            )
            
            logger.info(f"报告归档成功: execution_id={execution_id}, archive_path={archive_path}")
            
            return archive_path
