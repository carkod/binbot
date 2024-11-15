from typing import Optional
from uuid import UUID, uuid4
from pydantic import EmailStr
from sqlmodel import Field, SQLModel
from tools.enum_definitions import UserRoles


class UserTable(SQLModel, table=True):
    """
    Basic user schema for access to resources

    For full customer data create a separate table
    """
    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    )
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    role: UserRoles = UserRoles.admin
    # For full name, use internal functions to compose
    full_name: str = Field(default="")
    password: str = Field(min_length=8, max_length=40)
    # Email is the main identifier
    username: Optional[str] = ""
    bio: Optional[str] = ""
    # Future: Only required if customer table exists
    # customer_id: Optional[UUID] = Field(
    #     default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    # )
