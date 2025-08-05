from typing import Optional
from uuid import UUID, uuid4
from pydantic import EmailStr
from sqlmodel import Field, SQLModel
from databases.utils import timestamp
from tools.enum_definitions import UserRoles


class UserTable(SQLModel, table=True):
    """
    Basic user schema for access to resources

    For full customer data create a separate table
    """

    __tablename__ = "binbot_user"

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    )
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = Field(default=True)
    role: UserRoles = Field(default=UserRoles.user)
    full_name: str = Field(
        default="", description="For full name, use internal functions to compose"
    )
    password: str = Field(min_length=8, max_length=40)
    username: Optional[str] = Field(default="")
    description: Optional[str] = Field(default="")
    created_at: str = Field(default_factory=timestamp)
    updated_at: str = Field(default=timestamp())
    # Future: Only required if customer table exists
    # customer_id: Optional[UUID] = Field(
    #     default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    # )

    model_config = {
        "use_enum_values": True,
    }
