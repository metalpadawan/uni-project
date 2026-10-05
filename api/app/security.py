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


def new_qr_receipt(session_id: str, student_id: str, expires_at: datetime) -> str:
    """Create a short-lived proof that a signed-in student scanned a live QR."""
    nonce = secrets.token_urlsafe(18)
    payload = f"{session_id}:{student_id}:{int(expires_at.timestamp())}:{nonce}"
    signature = hmac.new(QR_SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def qr_receipt_is_valid(receipt: str, session_id: str, student_id: str) -> bool:
    try:
        payload, supplied = receipt.rsplit(".", 1)
        receipt_session, receipt_student, expires, _nonce = payload.split(":", 3)
        expected = hmac.new(QR_SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return (
            hmac.compare_digest(expected, supplied)
            and receipt_session == session_id
            and receipt_student == student_id
            and int(expires) >= int(utcnow().timestamp())
        )
    except (ValueError, TypeError):
        return False
