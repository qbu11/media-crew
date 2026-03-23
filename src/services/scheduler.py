"""
任务调度服务

使用 APScheduler 实现定时任务调度，集成 Service 层和 Crew。
"""

from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.models.content import Content
from src.models.hot_topic import HotTopic
from src.models.metrics import Metrics
from src.services.account_service import AccountService
from src.services.client_service import ClientService
from src.services.data_collector import get_data_collector
from src.services.metrics_service import MetricsService
from src.services.publish_engine_v2 import get_publish_engine_v2

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
                        from src.crew.crews import CrewInput, HotspotDetectionCrew

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

                    # 从 hot_topics 表中选择最近 24 小时内最相关的热点
                    since = datetime.utcnow() - timedelta(hours=24)
                    topic_query = (
                        select(HotTopic)
                        .where(HotTopic.created_at >= since)
                        .order_by(HotTopic.heat_score.desc().nullslast())
                        .limit(5)
                    )
                    # 如果客户有行业，优先匹配该行业的热点
                    if client.industry:
                        topic_query = topic_query.where(
                            HotTopic.category == client.industry
                        )

                    topic_result = await session.execute(topic_query)
                    hot_topics = topic_result.scalars().all()

                    if not hot_topics:
                        logger.info(
                            "客户 %s 无匹配热点，跳过内容生成", client.name
                        )
                        continue

                    for account in accounts_result.data:
                        # 筛选与账号平台匹配的热点
                        platform_topics = [
                            t for t in hot_topics
                            if t.platform == account.platform
                        ]
                        # 若无平台匹配热点，使用全部热点
                        topics_to_use = platform_topics or hot_topics

                        try:
                            from src.crew.crews import ContentCrew

                            content_crew = ContentCrew.create(
                                llm="openai/gpt-4o-mini",
                                verbose=False,
                            )
                            logger.info(
                                "为客户 %s 账号 %s 生成内容，基于 %d 条热点",
                                client.name,
                                account.username,
                                len(topics_to_use),
                            )
                            # 将热点信息传入 crew
                            topic_data = [
                                {
                                    "title": t.title,
                                    "platform": t.platform,
                                    "heat_score": t.heat_score,
                                    "category": t.category,
                                    "url": t.url,
                                }
                                for t in topics_to_use
                            ]
                            from src.crew.crews import CrewInput

                            crew_input = CrewInput(
                                inputs={
                                    "hot_topics": topic_data,
                                    "platform": account.platform,
                                    "client_name": client.name,
                                    "industry": client.industry or "",
                                },
                            )
                            content_crew.execute(crew_input)
                            logger.info(
                                "客户 %s 账号 %s 内容生成完成",
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
            async with self.SessionLocal() as session:
                # 查询待发布内容：状态为 scheduled 且 scheduled_at <= now
                now = datetime.utcnow()
                stmt = (
                    select(Content)
                    .where(
                        Content.status == "scheduled",
                        Content.published_at.is_(None),
                    )
                    .order_by(Content.created_at.asc())
                    .limit(20)
                )
                result = await session.execute(stmt)
                pending_contents = result.scalars().all()

                if not pending_contents:
                    logger.info("无待发布内容")
                    return

                logger.info("找到 %d 条待发布内容", len(pending_contents))

                for content in pending_contents:
                    try:
                        # 更新状态为 publishing
                        content.status = "publishing"
                        await session.commit()

                        platforms = content.platforms if isinstance(content.platforms, list) else []
                        if not platforms:
                            logger.warning(
                                "内容 %s 无目标平台，跳过", content.id
                            )
                            content.status = "failed"
                            await session.commit()
                            continue

                        # 调用发布引擎
                        publish_result = await self.publish_engine.publish(
                            content_id=content.id,
                            title=content.title,
                            body=content.body,
                            platforms=platforms,
                            images=content.images if isinstance(content.images, list) else [],
                        )

                        if publish_result.get("success"):
                            content.status = "published"
                            content.published_at = now
                            logger.info("内容 %s 发布成功", content.id)
                        else:
                            content.status = "failed"
                            logger.error(
                                "内容 %s 发布失败: %s",
                                content.id,
                                publish_result.get("error", "未知错误"),
                            )

                        await session.commit()

                    except Exception as e:
                        content.status = "failed"
                        await session.commit()
                        logger.error("内容 %s 发布异常: %s", content.id, e)

                logger.info("自动发布任务执行完成")

        except Exception as e:
            logger.error("自动发布失败: %s", e)

    async def hourly_data_collection(self) -> None:
        """每小时数据采集"""
        logger.info("开始数据采集")

        try:
            async with self.SessionLocal() as session:
                metrics_service = MetricsService(session)

                # 获取最近 7 天已发布内容
                seven_days_ago = datetime.utcnow() - timedelta(days=7)
                stmt = (
                    select(Content)
                    .where(
                        Content.status == "published",
                        Content.published_at >= seven_days_ago,
                    )
                    .order_by(Content.published_at.desc())
                )
                result = await session.execute(stmt)
                published_contents = result.scalars().all()

                if not published_contents:
                    logger.info("无最近已发布内容需要采集数据")
                    return

                logger.info(
                    "开始采集 %d 条已发布内容的数据", len(published_contents)
                )

                for content in published_contents:
                    platforms = content.platforms if isinstance(content.platforms, list) else []
                    for platform in platforms:
                        try:
                            collected = await self.data_collector.collect(
                                platform=platform,
                                content_id=content.id,
                            )
                            if collected:
                                await metrics_service.record_metric(
                                    platform=platform,
                                    content_id=content.id,
                                    views=collected.get("views"),
                                    likes=collected.get("likes"),
                                    comments=collected.get("comments"),
                                    shares=collected.get("shares"),
                                    raw_metrics=collected,
                                )
                                logger.info(
                                    "内容 %s 平台 %s 数据采集完成",
                                    content.id,
                                    platform,
                                )
                        except Exception as e:
                            logger.error(
                                "内容 %s 平台 %s 数据采集失败: %s",
                                content.id,
                                platform,
                                e,
                            )

                logger.info("数据采集任务执行完成")

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

                seven_days_ago = datetime.utcnow() - timedelta(days=7)

                for client in clients_result.data:
                    logger.info("为客户 %s 生成周报", client.name)

                    # 从 MetricsService 获取聚合数据
                    # 查询该客户所有账号对应内容的指标
                    account_service = AccountService(session)
                    accounts_result = await account_service.list_accounts(
                        client_id=client.id
                    )

                    total_views = 0
                    total_likes = 0
                    total_comments = 0
                    total_shares = 0
                    content_count = 0
                    platform_stats: dict[str, dict[str, int]] = {}

                    if accounts_result.success and accounts_result.data:
                        # 获取最近 7 天各平台的聚合指标
                        for account in accounts_result.data:
                            platform = account.platform
                            agg_stmt = (
                                select(
                                    func.coalesce(func.sum(Metrics.views), 0),
                                    func.coalesce(func.sum(Metrics.likes), 0),
                                    func.coalesce(func.sum(Metrics.comments), 0),
                                    func.coalesce(func.sum(Metrics.shares), 0),
                                    func.count(Metrics.id),
                                )
                                .where(
                                    Metrics.platform == platform,
                                    Metrics.created_at >= seven_days_ago,
                                )
                            )
                            agg_result = await session.execute(agg_stmt)
                            row = agg_result.one()

                            p_views = int(row[0])
                            p_likes = int(row[1])
                            p_comments = int(row[2])
                            p_shares = int(row[3])
                            p_count = int(row[4])

                            total_views += p_views
                            total_likes += p_likes
                            total_comments += p_comments
                            total_shares += p_shares
                            content_count += p_count

                            if p_count > 0:
                                platform_stats[platform] = {
                                    "views": p_views,
                                    "likes": p_likes,
                                    "comments": p_comments,
                                    "shares": p_shares,
                                    "count": p_count,
                                }

                    # 生成报告
                    report_dir = Path("reports")
                    report_dir.mkdir(exist_ok=True)

                    filename = (
                        f"{client.name}_weekly_"
                        f"{datetime.now().strftime('%Y%m%d')}.md"
                    )
                    report_path = report_dir / filename

                    total_engagement = total_likes + total_comments + total_shares
                    engagement_rate = (
                        f"{(total_engagement / total_views * 100):.2f}%"
                        if total_views > 0
                        else "N/A"
                    )

                    # 平台明细
                    platform_section = ""
                    for plat, stats in platform_stats.items():
                        plat_engagement = stats["likes"] + stats["comments"] + stats["shares"]
                        plat_rate = (
                            f"{(plat_engagement / stats['views'] * 100):.2f}%"
                            if stats["views"] > 0
                            else "N/A"
                        )
                        platform_section += (
                            f"\n### {plat}\n"
                            f"- 数据条数: {stats['count']}\n"
                            f"- 浏览量: {stats['views']:,}\n"
                            f"- 点赞数: {stats['likes']:,}\n"
                            f"- 评论数: {stats['comments']:,}\n"
                            f"- 分享数: {stats['shares']:,}\n"
                            f"- 互动率: {plat_rate}\n"
                        )

                    if not platform_section:
                        platform_section = "\n暂无平台数据\n"

                    report_content = (
                        f"# {client.name} - 7 天数据报告\n\n"
                        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        "## 数据概览\n\n"
                        f"- 数据采集条数: {content_count}\n"
                        f"- 总浏览量: {total_views:,}\n"
                        f"- 总点赞数: {total_likes:,}\n"
                        f"- 总评论数: {total_comments:,}\n"
                        f"- 总分享数: {total_shares:,}\n"
                        f"- 综合互动率: {engagement_rate}\n\n"
                        "## 平台明细\n"
                        f"{platform_section}"
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
