"""
任务调度服务

使用 APScheduler 实现定时任务调度，集成 Service 层和 Crew。
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.error_handling import Result, success, error
from src.services.client_service import ClientService
from src.services.account_service import AccountService
from src.services.metrics_service import MetricsService
from src.services.data_collector import DataCollector, get_data_collector
from src.services.publish_engine_v2 import PublishEngineV2, get_publish_engine_v2

logger = logging.getLogger(__name__)


class HotspotScheduler:
    """热点调度器"""

    def __init__(self, db_url: str | None = None) -> None:
        self.scheduler = AsyncIOScheduler(
            timezone=settings.SCHEDULER_TIMEZONE,
        )
        self.db_url = db_url or settings.DATABASE_URL
        self.engine = create_async_engine(self.db_url)
        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.data_collector = get_data_collector()
        self.publish_engine = get_publish_engine_v2()

    def start(self) -> None:
        """启动调度器"""
        if not settings.SCHEDULER_ENABLED:
            logger.info("调度器已禁用 (SCHEDULER_ENABLED=false)")
            return

        # 每日热点监控（每天早上 8 点）
        self.scheduler.add_job(
            self.daily_hotspot_detection,
            CronTrigger(hour=8, minute=0),
            id="daily_hotspot_detection",
            name="每日热点监控",
            replace_existing=True,
        )

        # 每日内容生成（每天早上 9 点）
        self.scheduler.add_job(
            self.daily_content_generation,
            CronTrigger(hour=9, minute=0),
            id="daily_content_generation",
            name="每日内容生成",
            replace_existing=True,
        )

        # 自动发布（每天 10:00、15:00、20:00）
        self.scheduler.add_job(
            self.auto_publish,
            CronTrigger(hour="10,15,20", minute=0),
            id="auto_publish",
            name="自动发布",
            replace_existing=True,
        )

        # 数据采集（每小时）
        self.scheduler.add_job(
            self.hourly_data_collection,
            IntervalTrigger(hours=1),
            id="hourly_data_collection",
            name="数据采集",
            replace_existing=True,
        )

        # 周报生成（每周一早上 9 点）
        self.scheduler.add_job(
            self.generate_weekly_reports,
            CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="generate_weekly_reports",
            name="周报生成",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("调度器已启动")

    def shutdown(self) -> None:
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("调度器已关闭")

    async def daily_hotspot_detection(self) -> None:
        """每日热点监控"""
        logger.info("开始每日热点监控")

        try:
            async with self.SessionLocal() as session:
                client_service = ClientService(session)

                clients_result = await client_service.list_clients()
                if not clients_result.success:
                    logger.error("获取客户列表失败: %s", clients_result.error)
                    return

                for client in clients_result.data:
                    logger.info("为客户 %s 监控热点", client.name)

                    keywords = [client.industry] if client.industry else []

                    try:
                        from src.crew.crews import HotspotDetectionCrew, CrewInput

                        crew = HotspotDetectionCrew.create(
                            llm="openai/gpt-4o-mini",
                            verbose=False,
                        )
                        crew_input = CrewInput(
                            inputs={
                                "keywords": keywords,
                                "platforms": [
                                    "xiaohongshu",
                                    "weibo",
                                    "zhihu",
                                ],
                            },
                        )
                        result = crew.execute(crew_input)
                        logger.info(
                            "客户 %s 热点监控完成: %d 条热点",
                            client.name,
                            result.topic_count,
                        )
                    except Exception as e:
                        logger.error(
                            "客户 %s 热点监控失败: %s", client.name, e
                        )

        except Exception as e:
            logger.error("每日热点监控失败: %s", e)

    async def daily_content_generation(self) -> None:
        """每日内容生成"""
        logger.info("开始每日内容生成")

        try:
            async with self.SessionLocal() as session:
                client_service = ClientService(session)
                account_service = AccountService(session)

                clients_result = await client_service.list_clients()
                if not clients_result.success:
                    logger.error("获取客户列表失败: %s", clients_result.error)
                    return

                for client in clients_result.data:
                    logger.info("为客户 %s 生成内容", client.name)

                    accounts_result = await account_service.list_accounts(
                        client_id=client.id
                    )
                    if not accounts_result.success:
                        continue

                    for account in accounts_result.data:
                        try:
                            from src.crew.crews import ContentCrew

                            crew = ContentCrew.create(
                                llm="openai/gpt-4o-mini",
                                verbose=False,
                            )
                            # TODO: 从 hot_topics 表中选择最相关的热点
                            logger.info(
                                "为客户 %s 账号 %s 生成内容",
                                client.name,
                                account.username,
                            )
                        except Exception as e:
                            logger.error(
                                "客户 %s 账号 %s 内容生成失败: %s",
                                client.name,
                                account.username,
                                e,
                            )

        except Exception as e:
            logger.error("每日内容生成失败: %s", e)

    async def auto_publish(self) -> None:
        """自动发布待发布内容"""
        logger.info("开始自动发布")

        try:
            # TODO: 从数据库获取待发布内容（scheduled_at <= now, human_reviewed=True）
            # 需要 ContentService（尚未创建），暂时记录日志
            logger.info("自动发布任务执行完成（待接入 ContentService）")
        except Exception as e:
            logger.error("自动发布失败: %s", e)

    async def hourly_data_collection(self) -> None:
        """每小时数据采集"""
        logger.info("开始数据采集")

        try:
            async with self.SessionLocal() as session:
                metrics_service = MetricsService(session)

                # TODO: 从 ContentService 获取最近 7 天已发布内容
                # 对每个内容调用 data_collector.collect_and_save()
                logger.info("数据采集任务执行完成（待接入 ContentService）")

        except Exception as e:
            logger.error("数据采集失败: %s", e)

    async def generate_weekly_reports(self) -> None:
        """生成周报"""
        logger.info("开始生成周报")

        try:
            async with self.SessionLocal() as session:
                client_service = ClientService(session)

                clients_result = await client_service.list_clients()
                if not clients_result.success:
                    logger.error("获取客户列表失败: %s", clients_result.error)
                    return

                for client in clients_result.data:
                    logger.info("为客户 %s 生成周报", client.name)

                    # TODO: 从 MetricsService 获取聚合数据生成报告
                    report_dir = Path("reports")
                    report_dir.mkdir(exist_ok=True)

                    filename = (
                        f"{client.name}_weekly_"
                        f"{datetime.now().strftime('%Y%m%d')}.md"
                    )
                    report_path = report_dir / filename

                    report_content = (
                        f"# {client.name} - 7 天数据报告\n\n"
                        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        "## 数据概览\n\n"
                        "（待接入 MetricsService 聚合查询）\n"
                    )

                    report_path.write_text(report_content, encoding="utf-8")
                    logger.info(
                        "客户 %s 的周报已生成: %s", client.name, report_path
                    )

        except Exception as e:
            logger.error("周报生成失败: %s", e)

    def add_custom_job(
        self,
        func: Any,
        trigger: Any,
        job_id: str,
        name: str,
        **kwargs: Any,
    ) -> None:
        """添加自定义任务"""
        self.scheduler.add_job(
            func,
            trigger,
            id=job_id,
            name=name,
            replace_existing=True,
            **kwargs,
        )

    def remove_job(self, job_id: str) -> None:
        """移除任务"""
        self.scheduler.remove_job(job_id)

    def get_jobs(self) -> list[dict[str, Any]]:
        """获取所有任务"""
        jobs: list[dict[str, Any]] = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": (
                    job.next_run_time.isoformat()
                    if job.next_run_time
                    else None
                ),
                "trigger": str(job.trigger),
            })
        return jobs


_scheduler: HotspotScheduler | None = None


def get_scheduler() -> HotspotScheduler:
    """获取调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = HotspotScheduler()
    return _scheduler
