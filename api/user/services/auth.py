import os
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Auth = Annotated[str, Depends(oauth2_scheme)]
FormData = Annotated[OAuth2PasswordRequestForm, Depends()]


class TokenData(BaseModel):
    email: str | None = None


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(email: str):
    expires_delta = timedelta(minutes=int(os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"]))
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)

    data = {
        "sub": email,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(data, os.environ["SECRET_KEY"], algorithm="HS256")
    return encoded_jwt, expire


def decode_access_token(token: Auth):
    try:
        payload = jwt.decode(token, os.environ["SECRET_KEY"], algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
