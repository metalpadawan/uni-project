from datetime import timedelta
from typing import Callable

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User, UserRole
from .security import utcnow

hasher = PasswordHasher()
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def issue_token(user: User, kind: str, lifetime: timedelta) -> str:
    return jwt.encode({"sub": user.id, "role": user.role.value, "type": kind, "exp": utcnow() + lifetime}, settings.jwt_secret, algorithm="HS256")


def token_pair(user: User) -> dict:
    return {"access_token": issue_token(user, "access", timedelta(minutes=settings.access_token_minutes)), "refresh_token": issue_token(user, "refresh", timedelta(days=settings.refresh_token_days)), "token_type": "bearer", "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role.value}}


def user_from_refresh(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user = db.get(User, payload.get("sub")) if payload.get("type") == "refresh" else None
    except JWTError:
        user = None
    if not user:
        raise HTTPException(401, "Invalid or expired refresh token.")
    return user


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise JWTError("wrong token type")
        user = db.get(User, payload.get("sub"))
    except JWTError:
        user = None
    if not user:
        raise HTTPException(401, "Invalid or expired authentication token.", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_roles(*roles: UserRole) -> Callable:
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Your account does not have permission for this action.")
        return user
    return dependency
