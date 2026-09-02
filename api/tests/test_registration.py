import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth import hash_password, require_roles
from app.database import Base
from app.main import (
    approve_pending_student,
    login,
    reject_pending_student,
    register_student,
)
from app.models import PendingStudent, RegistrationStatus, Student, User, UserRole
from app.schemas import LoginRequest, RejectRequest, StudentRegisterRequest
from app.security import utcnow


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_user(db, role, email, password="password123"):
    u = User(name=email, email=email, password_hash=hash_password(password), role=role, created_at=utcnow())
    db.add(u)
    db.flush()
    return u


def registration_payload(**overrides):
    data = dict(
        name="New Student",
        email="student@example.test",
        password="password123",
        matric_no="21/CSC/900",
        department="Computer Science",
        level=400,
        face_embedding=[0.1] * 128,
        biometric_consent=True,
    )
    data.update(overrides)
    return StudentRegisterRequest(**data)


def test_register_creates_a_pending_request_and_no_account_yet(db):
    register_student.__wrapped__(None, registration_payload(), db)

    pending = db.scalar(select(PendingStudent))
    assert pending.status == RegistrationStatus.pending
    assert db.scalar(select(Student)) is None
    with pytest.raises(HTTPException) as error:
        login.__wrapped__(None, LoginRequest(email="student@example.test", password="password123"), db)
    assert error.value.status_code == 401


def test_register_requires_biometric_consent(db):
    with pytest.raises(HTTPException) as error:
        register_student.__wrapped__(None, registration_payload(biometric_consent=False), db)
    assert error.value.status_code == 422


def test_register_rejects_an_email_already_in_use(db):
    make_user(db, UserRole.student, "student@example.test")
    db.commit()

    with pytest.raises(HTTPException) as error:
        register_student.__wrapped__(None, registration_payload(), db)
    assert error.value.status_code == 409


def test_approve_creates_a_working_account(db):
    admin = make_user(db, UserRole.admin, "admin@example.test")
    register_student.__wrapped__(None, registration_payload(), db)
    db.commit()
    pending = db.scalar(select(PendingStudent))

    approve_pending_student(pending.id, db, admin)

    db.refresh(pending)
    assert pending.status == RegistrationStatus.approved
    logged_in = login.__wrapped__(None, LoginRequest(email="student@example.test", password="password123"), db)
    assert logged_in["user"]["role"] == "student"


def test_reject_marks_rejected_and_creates_no_account(db):
    admin = make_user(db, UserRole.admin, "admin@example.test")
    register_student.__wrapped__(None, registration_payload(), db)
    db.commit()
    pending = db.scalar(select(PendingStudent))

    reject_pending_student(pending.id, RejectRequest(reason="Could not verify matric number"), db, admin)

    db.refresh(pending)
    assert pending.status == RegistrationStatus.rejected
    assert pending.rejection_reason == "Could not verify matric number"
    assert db.scalar(select(Student)) is None
    with pytest.raises(HTTPException) as error:
        login.__wrapped__(None, LoginRequest(email="student@example.test", password="password123"), db)
    assert error.value.status_code == 401


def test_approve_and_reject_require_admin_role(db):
    # approve_pending_student/reject_pending_student delegate role enforcement entirely to
    # Depends(require_roles(UserRole.admin)), which only runs through real FastAPI request
    # handling, not a direct Python call (see test_auth.py's test_require_roles_* for that
    # mechanism's own coverage). Live-verified separately over HTTP.
    dependency = require_roles(UserRole.admin)
    lecturer = make_user(db, UserRole.lecturer, "lecturer@example.test")
    db.commit()

    with pytest.raises(HTTPException) as error:
        dependency(user=lecturer)
    assert error.value.status_code == 403


def test_approving_a_duplicate_matric_no_after_the_first_approval_fails(db):
    admin = make_user(db, UserRole.admin, "admin@example.test")
    register_student.__wrapped__(None, registration_payload(email="a@example.test"), db)
    register_student.__wrapped__(None, registration_payload(email="b@example.test"), db)
    db.commit()
    first, second = db.scalars(select(PendingStudent).order_by(PendingStudent.requested_at)).all()

    approve_pending_student(first.id, db, admin)
    db.commit()

    with pytest.raises(HTTPException) as error:
        approve_pending_student(second.id, db, admin)
    assert error.value.status_code == 409
