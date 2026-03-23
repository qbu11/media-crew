"""账号管理服务"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import Account, AccountStatus
from src.core.error_handling import Result, success, error

logger = logging.getLogger(__name__)


class AccountService:
    """账号服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_account(
        self,
        client_id: str,
        platform: str,
        username: str,
        status: str = AccountStatus.ACTIVE,
    ) -> Result[Account]:
        """创建账号"""
        try:
            account = Account(
                client_id=client_id,
                platform=platform,
                username=username,
                status=status,
            )
            self.session.add(account)
            await self.session.commit()
            await self.session.refresh(account)

            logger.info(f"创建账号成功: {account.id}")
            return success(account)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建账号失败: {e}")
            return error(f"创建账号失败: {e}", "ACCOUNT_CREATE_ERROR")

    async def list_accounts(
        self,
        client_id: str | None = None,
        platform: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Result[list[Account]]:
        """列出账号"""
        try:
            query = select(Account)

            if client_id:
                query = query.where(Account.client_id == client_id)
            if platform:
                query = query.where(Account.platform == platform)

            query = query.offset(skip).limit(limit)

            result = await self.session.execute(query)
            accounts = result.scalars().all()
            return success(list(accounts))

        except Exception as e:
            logger.error(f"列出账号失败: {e}")
            return error(f"列出账号失败: {e}", "ACCOUNT_LIST_ERROR")

    async def update_login_status(
        self,
        account_id: str,
        is_logged_in: bool,
    ) -> Result[Account]:
        """更新登录状态"""
        try:
            result = await self.session.execute(
                select(Account).where(Account.id == account_id)
            )
            account = result.scalar_one_or_none()

            if not account:
                return error(f"账号不存在: {account_id}", "ACCOUNT_NOT_FOUND")

            account.is_logged_in = is_logged_in
            if is_logged_in:
                account.last_login = datetime.utcnow()

            await self.session.commit()
            await self.session.refresh(account)

            logger.info(f"更新账号登录状态: {account.id} -> {is_logged_in}")
            return success(account)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新登录状态失败: {e}")
            return error(f"更新登录状态失败: {e}", "ACCOUNT_UPDATE_ERROR")
