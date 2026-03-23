"""Account schema for platform account management."""

from enum import Enum

from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    """Platform types."""

    XIAOHONGSHU = "xiaohongshu"
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    BILIBILI = "bilibili"
    DOUYIN = "douyin"


class AccountStatusEnum(str, Enum):
    """Account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class AccountBase(BaseModel):
    """Account base schema."""

    client_id: str = Field(..., description="客户 ID")
    platform: PlatformType = Field(..., description="平台")
    username: str = Field(..., min_length=1, max_length=100, description="用户名")
    status: AccountStatusEnum = Field(default=AccountStatusEnum.ACTIVE, description="状态")


class AccountCreate(AccountBase):
    """Create account request."""

    pass


class AccountUpdate(BaseModel):
    """Update account request."""

    platform: PlatformType | None = None
    username: str | None = Field(None, min_length=1, max_length=100)
    status: AccountStatusEnum | None = None
    is_logged_in: bool | None = None


class AccountResponse(AccountBase):
    """Account response."""

    id: str
    is_logged_in: bool
    last_login: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
