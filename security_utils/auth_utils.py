from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Cookie
import os

SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_NOW") #TODO: Move to env variable and make it more secure in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    print("VALUE:", repr(password))
    print("TYPE:", type(password))
    encoded = password.encode("utf-8")
    print("BYTE LENGTH:", len(encoded))
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

async def require_auth(
    access_token: str | None = Cookie(default=None),
):
    if not access_token:
        raise HTTPException(status_code=401)

    try:
        payload = decode_access_token(access_token)
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401)