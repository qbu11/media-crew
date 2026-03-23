"""数据指标服务"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.error_handling import Result, error, success
from src.models.metrics import Metrics

logger = logging.getLogger(__name__)


class MetricsService:
    """指标服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_metric(
        self,
        platform: str,
        post_url: str | None = None,
        content_id: str | None = None,
        views: int | None = None,
        likes: int | None = None,
        comments: int | None = None,
        shares: int | None = None,
        raw_metrics: dict | None = None,
    ) -> Result[Metrics]:
        """记录指标"""
        try:
            # 计算互动率
            engagement_rate = None
            if views and views > 0:
                total_engagement = (likes or 0) + (comments or 0) + (shares or 0)
                engagement_rate = total_engagement / views

            metric = Metrics(
                platform=platform,
                post_url=post_url,
                content_id=content_id,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                engagement_rate=engagement_rate,
                raw_metrics=raw_metrics,
            )
            self.session.add(metric)
            await self.session.commit()
            await self.session.refresh(metric)

            logger.info(f"记录指标成功: {metric.id}")
            return success(metric)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"记录指标失败: {e}")
            return error(f"记录指标失败: {e}", "METRIC_RECORD_ERROR")

    async def get_metrics_by_content(
        self,
        content_id: str,
    ) -> Result[list[Metrics]]:
        """获取内容的所有指标"""
        try:
            result = await self.session.execute(
                select(Metrics).where(Metrics.content_id == content_id)
            )
            metrics = result.scalars().all()
            return success(list(metrics))

        except Exception as e:
            logger.error(f"获取指标失败: {e}")
            return error(f"获取指标失败: {e}", "METRIC_GET_ERROR")
