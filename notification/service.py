"""
通知服务模块
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
from core.config import settings
from core.logger import logger


class NotificationService:
    """通知服务"""

    def __init__(self):
        self.email_config = {
            "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "smtp_user": os.getenv("SMTP_USER", ""),
            "smtp_password": os.getenv("SMTP_PASSWORD", ""),
            "from_email": os.getenv("FROM_EMAIL", ""),
        }

        self.dingtalk_webhook = os.getenv("DINGTALK_WEBHOOK", "")
        self.wechat_webhook = os.getenv("WECHAT_WEBHOOK", "")

    async def send_execution_notification(
            self,
            execution_id: int,
            plan_name: str,
            status: str,
            total_cases: int,
            passed_cases: int,
            failed_cases: int,
            recipients: Optional[List[str]] = None
    ) -> bool:
        """
        发送执行完成通知

        Args:
            execution_id: 执行记录ID
            plan_name: 测试计划名称
            status: 执行状态
            total_cases: 总用例数
            passed_cases: 通过用例数
            failed_cases: 失败用例数
            recipients: 收件人列表

        Returns:
            是否发送成功
        """
        # 构建通知内容
        subject = f"测试计划执行完成: {plan_name}"

        success_rate = (passed_cases / total_cases * 100) if total_cases > 0 else 0

        content = f"""
        <h2>测试执行报告</h2>
        <p><strong>测试计划:</strong> {plan_name}</p>
        <p><strong>执行状态:</strong> {status.upper()}</p>
        <p><strong>执行时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h3>执行统计</h3>
        <ul>
            <li>总用例数: {total_cases}</li>
            <li>通过数: {passed_cases}</li>
            <li>失败数: {failed_cases}</li>
            <li>通过率: {success_rate:.2f}%</li>
        </ul>

        <p>详情请查看: <a href="{settings.BASE_URL}/executions/{execution_id}">执行记录</a></p>
        """

        # 发送邮件通知
        if recipients:
            await self._send_email(recipients, subject, content)

        # 发送钉钉通知
        if self.dingtalk_webhook:
            await self._send_dingtalk(subject, content)

        # 发送企业微信通知
        if self.wechat_webhook:
            await self._send_wechat(subject, content)

        logger.info(f"执行通知发送完成: execution_id={execution_id}")
        return True

    async def send_alert(
            self,
            title: str,
            message: str,
            level: str = "warning",
            recipients: Optional[List[str]] = None
    ) -> bool:
        """
        发送告警通知

        Args:
            title: 告警标题
            message: 告警消息
            level: 告警级别
            recipients: 收件人列表

        Returns:
            是否发送成功
        """
        # 构建告警内容
        subject = f"[{level.upper()}] {title}"

        content = f"""
        <h2>{title}</h2>
        <p><strong>告警级别:</strong> {level.upper()}</p>
        <p><strong>告警时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>告警内容:</strong></p>
        <pre>{message}</pre>
        """

        # 发送通知
        if recipients:
            await self._send_email(recipients, subject, content)

        if self.dingtalk_webhook:
            await self._send_dingtalk(subject, message)

        if self.wechat_webhook:
            await self._send_wechat(subject, message)

        logger.info(f"告警通知发送完成: title={title}")
        return True

    async def _send_email(
            self,
            to_emails: List[str],
            subject: str,
            html_content: str
    ) -> bool:
        """
        发送邮件

        Args:
            to_emails: 收件人邮箱列表
            subject: 邮件主题
            html_content: HTML内容

        Returns:
            是否发送成功
        """
        if not self.email_config["smtp_user"]:
            logger.warning("邮件配置不完整，跳过邮件发送")
            return False

        try:
            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_config["from_email"] or self.email_config["smtp_user"]
            msg["To"] = ", ".join(to_emails)

            # 添加HTML内容
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # 发送邮件
            with smtplib.SMTP(
                    self.email_config["smtp_host"],
                    self.email_config["smtp_port"]
            ) as server:
                server.starttls()
                server.login(
                    self.email_config["smtp_user"],
                    self.email_config["smtp_password"]
                )
                server.sendmail(
                    msg["From"],
                    to_emails,
                    msg.as_string()
                )

            logger.info(f"邮件发送成功: to={to_emails}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False

    async def _send_dingtalk(
            self,
            title: str,
            content: str
    ) -> bool:
        """
        发送钉钉通知

        Args:
            title: 标题
            content: 内容

        Returns:
            是否发送成功
        """
        if not self.dingtalk_webhook:
            return False

        try:
            import aiohttp

            # 构建钉钉消息
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"### {title}\n\n{content}"
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                        self.dingtalk_webhook,
                        json=message
                ) as response:
                    if response.status == 200:
                        logger.info("钉钉通知发送成功")
                        return True
                    else:
                        logger.error(f"钉钉通知发送失败: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"钉钉通知发送失败: {e}")
            return False

    async def _send_wechat(
            self,
            title: str,
            content: str
    ) -> bool:
        """
        发送企业微信通知

        Args:
            title: 标题
            content: 内容

        Returns:
            是否发送成功
        """
        if not self.wechat_webhook:
            return False

        try:
            import aiohttp

            # 构建企业微信消息
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"### {title}\n\n{content}"
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                        self.wechat_webhook,
                        json=message
                ) as response:
                    if response.status == 200:
                        logger.info("企业微信通知发送成功")
                        return True
                    else:
                        logger.error(f"企业微信通知发送失败: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"企业微信通知发送失败: {e}")
            return False


# 全局通知服务实例
notification_service = NotificationService()
