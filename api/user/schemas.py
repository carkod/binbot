from datetime import date
from typing import Optional
from pydantic import BaseModel
from tools.handle_error import StandardResponse


class UserSchema(BaseModel):
    email: str
    password: str
    username: Optional[str] = ""
    description: Optional[str] = ""
    access_token: str = ""
    last_login: str = ""
    created_at: str = date.today().strftime("%Y-%m-%d")


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(StandardResponse):
    data: LoginRequest
