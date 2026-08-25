from datetime import timedelta

from app.security import new_qr_token, signature_is_valid, utcnow


def test_signed_qr_token_is_valid_before_expiry():
    assert signature_is_valid(new_qr_token("session-1", utcnow() + timedelta(seconds=30)))


def test_tampered_qr_token_is_rejected():
    token = new_qr_token("session-1", utcnow() + timedelta(seconds=30))
    assert not signature_is_valid(token + "tampered")


def test_expired_qr_token_is_rejected():
    assert not signature_is_valid(new_qr_token("session-1", utcnow() - timedelta(seconds=1)))

