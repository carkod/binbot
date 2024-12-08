from typing import Optional
from pydantic import BaseModel, EmailStr, SecretStr, field_validator
from sqlmodel import Field
from tools.enum_definitions import UserRoles
from tools.handle_error import StandardResponse
from uuid import UUID, uuid4


class CreateUser(BaseModel):
    """
    Basic user schema for access to resources

    For full customer data create a separate table
    """

    __tablename__ = "user"

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    )
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    role: UserRoles = Field(default=UserRoles.admin)
    full_name: Optional[str] = Field(default="")
    password: SecretStr = Field(min_length=8, max_length=40)
    # Email is the main identifier
    username: Optional[str] = Field(default="")
    bio: Optional[str] = Field(default="")
    # Future: Only required if customer table exists
    # customer_id: Optional[UUID] = Field(
    #     default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    # )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str):
        if v not in UserRoles.__members__:
            raise ValueError(f"User role {v} must be one of {UserRoles.__members__}")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(StandardResponse):
    data: LoginRequest
