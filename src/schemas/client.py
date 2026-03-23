"""Client schema for customer management."""

from pydantic import BaseModel, Field


class ClientBase(BaseModel):
    """Client base schema."""

    name: str = Field(..., min_length=1, max_length=100, description="客户名称")
    industry: str | None = Field(None, max_length=50, description="行业")
    description: str | None = Field(None, description="描述")


class ClientCreate(ClientBase):
    """Create client request."""

    pass


class ClientUpdate(BaseModel):
    """Update client request."""

    name: str | None = Field(None, min_length=1, max_length=100)
    industry: str | None = Field(None, max_length=50)
    description: str | None = None


class ClientResponse(ClientBase):
    """Client response."""

    id: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
