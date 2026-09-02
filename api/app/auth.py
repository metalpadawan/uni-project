from datetime import timedelta
from typing import Callable

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import RefreshToken, User, UserRole
from .security import as_aware, token_hash, utcnow

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


def token_pair(user: User, db: Session) -> dict:
    access = issue_token(user, "access", timedelta(minutes=settings.access_token_minutes))
    refresh_lifetime = timedelta(days=settings.refresh_token_days)
    refresh = issue_token(user, "refresh", refresh_lifetime)
    now = utcnow()
    db.add(RefreshToken(user_id=user.id, token_hash=token_hash(refresh), issued_at=now, expires_at=now + refresh_lifetime))
    db.commit()
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer", "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role.value}}


def redeem_refresh_token(token: str, db: Session) -> User:
    """Validates and rotates a refresh token: the old token is revoked so it can't be replayed."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user = db.get(User, payload.get("sub")) if payload.get("type") == "refresh" else None
    except JWTError:
        user = None
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(token))) if user else None
    if not user or not row or row.revoked_at or as_aware(row.expires_at) < utcnow():
        raise HTTPException(401, "Invalid or expired refresh token.")
    row.revoked_at = utcnow()
    db.commit()
    return user


def revoke_refresh_token(token: str, db: Session) -> None:
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(token)))
    if row and not row.revoked_at:
        row.revoked_at = utcnow()
        db.commit()


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
