from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import (
    current_user,
    hash_password,
    redeem_refresh_token,
    require_roles,
    revoke_refresh_token,
    token_pair,
    verify_password,
)
from app.database import Base
from app.main import close_session, demo_login, enroll_student, login, register
from app.models import AttendanceSession, Course, SessionStatus, User, UserRole
from app.schemas import LoginRequest, RegisterRequest, StudentEnroll
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


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_login_succeeds_with_correct_credentials(db):
    make_user(db, UserRole.lecturer, "lecturer@example.test")
    db.commit()

    result = login.__wrapped__(None, LoginRequest(email="lecturer@example.test", password="password123"), db)

    assert result["user"]["role"] == "lecturer"
    assert result["access_token"] and result["refresh_token"]


def test_login_rejects_wrong_password(db):
    make_user(db, UserRole.lecturer, "lecturer@example.test")
    db.commit()

    with pytest.raises(HTTPException) as error:
        login.__wrapped__(None, LoginRequest(email="lecturer@example.test", password="wrong-password"), db)

    assert error.value.status_code == 401


def test_login_rejects_unknown_email(db):
    with pytest.raises(HTTPException) as error:
        login.__wrapped__(None, LoginRequest(email="nobody@example.test", password="password123"), db)

    assert error.value.status_code == 401


def test_register_requires_admin_role(db):
    lecturer = make_user(db, UserRole.lecturer, "lecturer@example.test")
    db.commit()
    dependency = require_roles(UserRole.admin)

    with pytest.raises(HTTPException) as error:
        dependency(user=lecturer)

    assert error.value.status_code == 403


def test_register_rejects_unknown_role(db):
    admin = make_user(db, UserRole.admin, "admin@example.test")
    db.commit()

    with pytest.raises(HTTPException) as error:
        register(RegisterRequest(name="New Person", email="new@example.test", password="password123", role="superuser"), db, admin)

    assert error.value.status_code == 422


def test_register_rejects_duplicate_email(db):
    admin = make_user(db, UserRole.admin, "admin@example.test")
    make_user(db, UserRole.lecturer, "taken@example.test")
    db.commit()

    with pytest.raises(HTTPException) as error:
        register(RegisterRequest(name="New Person", email="taken@example.test", password="password123", role="lecturer"), db, admin)

    assert error.value.status_code == 409


def test_register_creates_a_working_lecturer_account(db):
    admin = make_user(db, UserRole.admin, "admin@example.test")
    db.commit()

    created = register(RegisterRequest(name="Dr. New", email="dr.new@example.test", password="password123", role="lecturer"), db, admin)

    assert created["role"] == "lecturer"
    logged_in = login.__wrapped__(None, LoginRequest(email="dr.new@example.test", password="password123"), db)
    assert logged_in["user"]["email"] == "dr.new@example.test"


def test_demo_login_disabled_outside_demo_mode(db, monkeypatch):
    monkeypatch.setattr("app.main.settings.demo_mode", False)

    with pytest.raises(HTTPException) as error:
        demo_login.__wrapped__(None, UserRole.admin, db)

    assert error.value.status_code == 404


def test_refresh_token_cannot_be_replayed_after_use(db):
    user = make_user(db, UserRole.student, "student@example.test")
    db.commit()
    pair = token_pair(user, db)

    rotated_user = redeem_refresh_token(pair["refresh_token"], db)
    assert rotated_user.id == user.id

    with pytest.raises(HTTPException) as error:
        redeem_refresh_token(pair["refresh_token"], db)

    assert error.value.status_code == 401


def test_logout_revokes_the_refresh_token(db):
    user = make_user(db, UserRole.student, "student@example.test")
    db.commit()
    pair = token_pair(user, db)

    revoke_refresh_token(pair["refresh_token"], db)

    with pytest.raises(HTTPException) as error:
        redeem_refresh_token(pair["refresh_token"], db)

    assert error.value.status_code == 401


def test_current_user_rejects_a_refresh_token_used_as_access(db):
    user = make_user(db, UserRole.student, "student@example.test")
    db.commit()
    pair = token_pair(user, db)

    with pytest.raises(HTTPException) as error:
        current_user(token=pair["refresh_token"], db=db)

    assert error.value.status_code == 401


def test_current_user_accepts_a_valid_access_token(db):
    user = make_user(db, UserRole.student, "student@example.test")
    db.commit()
    pair = token_pair(user, db)

    resolved = current_user(token=pair["access_token"], db=db)

    assert resolved.id == user.id


def test_require_roles_allows_matching_role_and_blocks_others(db):
    lecturer = make_user(db, UserRole.lecturer, "lecturer@example.test")
    student = make_user(db, UserRole.student, "student@example.test")
    db.commit()
    dependency = require_roles(UserRole.lecturer)

    assert dependency(user=lecturer).id == lecturer.id
    with pytest.raises(HTTPException) as error:
        dependency(user=student)
    assert error.value.status_code == 403


def test_enroll_student_requires_biometric_consent(db):
    admin = make_user(db, UserRole.admin, "admin@example.test")
    db.commit()
    payload = StudentEnroll(
        name="New Student",
        email="new.student@example.test",
        temporary_password="password123",
        matric_no="21/CSC/900",
        photo="dummy-photo",
        biometric_consent=False,
    )

    with pytest.raises(HTTPException) as error:
        enroll_student(payload, db, admin)

    assert error.value.status_code == 422


def test_close_session_rejects_non_owning_lecturer(db):
    owner = make_user(db, UserRole.lecturer, "owner@example.test")
    intruder = make_user(db, UserRole.lecturer, "intruder@example.test")
    course = Course(code="CSC 421", title="AI", lecturer_id=owner.id)
    db.add(course)
    db.flush()
    session = AttendanceSession(course_id=course.id, lecturer_id=owner.id, started_at=utcnow(), ends_at=utcnow() + timedelta(minutes=30), status=SessionStatus.open)
    db.add(session)
    db.commit()

    with pytest.raises(HTTPException) as error:
        close_session(session.id, db, intruder)

    assert error.value.status_code == 404
