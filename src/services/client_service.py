"""客户管理服务"""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.client import Client
from src.core.error_handling import Result, success, error

logger = logging.getLogger(__name__)


class ClientService:
    """客户服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_client(
        self,
        name: str,
        industry: str | None = None,
        description: str | None = None,
    ) -> Result[Client]:
        """创建客户"""
        try:
            # 检查重名
            result = await self.session.execute(
                select(Client).where(Client.name == name)
            )
            if result.scalar_one_or_none():
                return error(f"客户名称已存在: {name}", "CLIENT_NAME_EXISTS")

            client = Client(name=name, industry=industry, description=description)
            self.session.add(client)
            await self.session.commit()
            await self.session.refresh(client)

            logger.info(f"创建客户成功: {client.id}")
            return success(client)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建客户失败: {e}")
            return error(f"创建客户失败: {e}", "CLIENT_CREATE_ERROR")

    async def get_client(self, client_id: str) -> Result[Client]:
        """获取客户"""
        try:
            result = await self.session.execute(
                select(Client).where(Client.id == client_id)
            )
            client = result.scalar_one_or_none()

            if not client:
                return error(f"客户不存在: {client_id}", "CLIENT_NOT_FOUND")

            return success(client)

        except Exception as e:
            logger.error(f"获取客户失败: {e}")
            return error(f"获取客户失败: {e}", "CLIENT_GET_ERROR")

    async def list_clients(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Result[list[Client]]:
        """列出客户"""
        try:
            result = await self.session.execute(
                select(Client).offset(skip).limit(limit)
            )
            clients = result.scalars().all()
            return success(list(clients))

        except Exception as e:
            logger.error(f"列出客户失败: {e}")
            return error(f"列出客户失败: {e}", "CLIENT_LIST_ERROR")

    async def update_client(
        self,
        client_id: str,
        **kwargs: Any,
    ) -> Result[Client]:
        """更新客户"""
        try:
            result = await self.session.execute(
                select(Client).where(Client.id == client_id)
            )
            client = result.scalar_one_or_none()

            if not client:
                return error(f"客户不存在: {client_id}", "CLIENT_NOT_FOUND")

            for key, value in kwargs.items():
                if hasattr(client, key):
                    setattr(client, key, value)

            await self.session.commit()
            await self.session.refresh(client)

            logger.info(f"更新客户成功: {client.id}")
            return success(client)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新客户失败: {e}")
            return error(f"更新客户失败: {e}", "CLIENT_UPDATE_ERROR")

    async def delete_client(self, client_id: str) -> Result[None]:
        """删除客户"""
        try:
            result = await self.session.execute(
                select(Client).where(Client.id == client_id)
            )
            client = result.scalar_one_or_none()

            if not client:
                return error(f"客户不存在: {client_id}", "CLIENT_NOT_FOUND")

            await self.session.delete(client)
            await self.session.commit()

            logger.info(f"删除客户成功: {client_id}")
            return success(None)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除客户失败: {e}")
            return error(f"删除客户失败: {e}", "CLIENT_DELETE_ERROR")
