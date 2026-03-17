import os
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pybinbot import UserRoles
from pydantic import BaseModel
from user.models.user import UserTokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Auth = Annotated[str, Depends(oauth2_scheme)]
FormData = Annotated[OAuth2PasswordRequestForm, Depends()]


class TokenData(BaseModel):
    email: str | None = None


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credentials are invalid",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(email: str, role: str):
    expires_delta = timedelta(minutes=int(os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"]))
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    data = {
        "sub": email,
        "exp": expire,
        "role": role,
    }
    encoded_jwt = jwt.encode(data, os.environ["SECRET_KEY"], algorithm="HS256")
    return encoded_jwt, expire


def decode_access_token(token: Auth):
    try:
        payload = jwt.decode(token, os.environ["SECRET_KEY"], algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserTokenData:
    """
    FastAPI authentication dependency that decodes the JWT token and returns the payload.
    If the token is invalid or expired, raises a 401 HTTPException internally.
    """
    payload = decode_access_token(token)
    user_data = UserTokenData(
        email=payload.get("sub"),
        role=UserRoles(payload.get("role")),
        expires_in=payload.get("exp"),
    )
    return user_data
