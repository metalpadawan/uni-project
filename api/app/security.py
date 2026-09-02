import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from .config import settings

QR_SIGNING_SECRET = settings.qr_signing_secret


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_aware(value: datetime) -> datetime:
    """SQLite drops tzinfo on read even for timezone-aware columns; PostgreSQL does not."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def new_qr_token(session_id: str, expires_at: datetime) -> str:
    nonce = secrets.token_urlsafe(18)
    payload = f"{session_id}.{int(expires_at.timestamp())}.{nonce}"
    signature = hmac.new(QR_SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def signature_is_valid(token: str) -> bool:
    try:
        session_id, expires, nonce, supplied = token.rsplit(".", 3)
        payload = f"{session_id}.{expires}.{nonce}"
        expected = hmac.new(QR_SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, supplied) and int(expires) >= int(utcnow().timestamp())
    except (ValueError, TypeError):
        return False
