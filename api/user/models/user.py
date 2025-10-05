from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from sqlmodel import Field
from tools.enum_definitions import UserRoles
from tools.handle_error import StandardResponse
from uuid import UUID, uuid4
from databases.utils import timestamp
from typing import Sequence
from databases.tables.user_table import UserTable


class UserDetails(BaseModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: Optional[bool] = True
    role: Optional[UserRoles] = Field(default=UserRoles.admin)
    full_name: Optional[str] = Field(default="")
    password: Optional[str] = Field(
        min_length=8,
        max_length=40,
        description="Not using SecretStr because not supported by SQLModel",
    )
    # Email is the main identifier
    username: Optional[str] = Field(default="")
    description: Optional[str] = Field(default="")
    created_at: Optional[int] = Field(default_factory=timestamp)
    updated_at: Optional[int] = Field(default=timestamp())

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str):
        if v not in UserRoles.__members__:
            raise ValueError(f"User role {v} must be one of {UserRoles.__members__}")
        return v


class CreateUser(UserDetails):
    """
    Basic user schema for access to resources

    For full customer data create a separate table
    """

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    )
    # Future: Only required if customer table exists
    # customer_id: Optional[UUID] = Field(
    #     default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    # )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoggedInDetails(BaseModel):
    email: EmailStr
    token: str


class UserResponse(StandardResponse):
    data: Sequence[UserTable]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: str


class LoginResponse(StandardResponse):
    data: Optional[TokenResponse]


class GetOneUser(StandardResponse):
    data: Optional[UserTable]
