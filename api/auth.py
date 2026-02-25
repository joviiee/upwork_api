from fastapi import APIRouter, Depends, HTTPException, Response, status
from asyncpg import UniqueViolationError

from security_utils.auth_schema import RegisterRequest, LoginRequest
from security_utils.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
)
from db.auth import get_user_password, add_user

print("Auth API Loaded")

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=201)
async def register(
    payload: RegisterRequest,
):
    try:
        print("Input password repr:", repr(payload.password))
        print("Length:", len(payload.password))
        status, message = await add_user(
            username=payload.username,
            password_hash=hash_password(payload.password),
        )
    except UniqueViolationError:
        raise HTTPException(
            status_code=409,
            detail="Username already exists",
        )
    except Exception as e:
        print()
        return {"status":"failed", "message":str(e)}
    return {"status": status, "message": message}


@router.post("/login")
async def login(
    payload: LoginRequest,
    response: Response,
):
    stored_password = await get_user_password(payload.username)
    print("Input password repr:", repr(payload.password))
    print("Length:", len(payload.password))

    if not stored_password or not verify_password(payload.password, stored_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Credentials",
        )
        
    token = create_access_token({
        "sub": payload.username,
    })

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,   # set True behind HTTPS
        max_age=60 * 60 * 8,
    )

    return {"status": "logged_in"}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "logged_out"}