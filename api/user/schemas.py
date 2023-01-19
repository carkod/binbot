from pydantic import BaseModel
from tools.handle_error import StandardResponse
from fastapi.security import OAuth2PasswordRequestForm

class UserSchema(BaseModel):
    email: str = ""
    password: str = ""
    username: str = ""
    description: str = ""
    access_token: str = ""
    last_login: str = ""
    created_at: str = ""

class LoginRequest(BaseModel):
    email: str = ""
    password: str = ""
    username: str = ""

class UserResponse(StandardResponse):
    data: LoginRequest
