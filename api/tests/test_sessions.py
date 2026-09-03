from datetime import timedelta

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.main import check_in, create_session, list_open_sessions
from app.models import AttendanceAttempt, AttendanceRecord, AttendanceSession, Course, CourseEnrollment, FaceEmbedding, QRToken, SessionStatus, Student, User, UserRole
from app.database import Base
from app.schemas import CheckIn, SessionCreate
from app.security import new_qr_token, token_hash, utcnow


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def user(role, email):
    return User(name=email, email=email, password_hash="test", role=role, created_at=utcnow())


def test_lecturer_cannot_start_another_lecturers_course(db):
    owner = user(UserRole.lecturer, "owner@example.test")
    intruder = user(UserRole.lecturer, "intruder@example.test")
    db.add_all([owner, intruder]); db.flush()
    db.add(Course(code="CSC 421", title="AI", lecturer_id=owner.id)); db.commit()

    with pytest.raises(HTTPException) as error:
        create_session(SessionCreate(), db, intruder)

    assert error.value.status_code == 403


def test_student_only_discovers_enrolled_open_sessions(db):
    lecturer = user(UserRole.lecturer, "lecturer@example.test")
    student_user = user(UserRole.student, "student@example.test")
    db.add_all([lecturer, student_user]); db.flush()
    student = Student(user_id=student_user.id, matric_no="21/CSC/001", department="Computer Science", level=400)
    course = Course(code="CSC 421", title="AI", lecturer_id=lecturer.id)
    db.add_all([student, course]); db.flush()
    db.add(CourseEnrollment(course_id=course.id, student_id=student.id))
    db.add(AttendanceSession(course_id=course.id, lecturer_id=lecturer.id, started_at=utcnow(), ends_at=utcnow() + timedelta(minutes=30), status=SessionStatus.open))
    db.commit()

    sessions = list_open_sessions(db, student_user)

    assert len(sessions) == 1
    assert sessions[0]["course_code"] == "CSC 421"


def test_expired_session_is_rejected_before_qr_or_face_checks(db):
    lecturer = user(UserRole.lecturer, "lecturer@example.test")
    student_user = user(UserRole.student, "student@example.test")
    db.add_all([lecturer, student_user]); db.flush()
    student = Student(user_id=student_user.id, matric_no="21/CSC/001", department="Computer Science", level=400)
    course = Course(code="CSC 421", title="AI", lecturer_id=lecturer.id)
    db.add_all([student, course]); db.flush()
    session = AttendanceSession(course_id=course.id, lecturer_id=lecturer.id, started_at=utcnow() - timedelta(hours=2), ends_at=utcnow() - timedelta(minutes=1), status=SessionStatus.open)
    db.add_all([CourseEnrollment(course_id=course.id, student_id=student.id), session]); db.commit()
    payload = CheckIn(session_id=session.id, qr_token="invalid", frame_a="frame-a", frame_b="frame-b")

    with pytest.raises(HTTPException) as error:
        request = Request({"type": "http", "method": "POST", "path": "/attendance/checkin", "headers": [], "client": ("test", 1234)})
        check_in(request, payload, db, student_user)

    assert error.value.status_code == 409


class FaceResponse:
    is_success = True

    def __init__(self, matched=True):
        self.matched = matched

    def json(self):
        return {"matched": self.matched, "score": .98 if self.matched else .1}


def checkin_setup(db):
    lecturer = user(UserRole.lecturer, "lecturer@example.test")
    student_user = user(UserRole.student, "student@example.test")
    db.add_all([lecturer, student_user]); db.flush()
    student = Student(user_id=student_user.id, matric_no="21/CSC/001", department="Computer Science", level=400)
    course = Course(code="CSC 421", title="AI", lecturer_id=lecturer.id)
    db.add_all([student, course]); db.flush()
    session = AttendanceSession(course_id=course.id, lecturer_id=lecturer.id, started_at=utcnow(), ends_at=utcnow() + timedelta(minutes=30), status=SessionStatus.open)
    db.add_all([CourseEnrollment(course_id=course.id, student_id=student.id), FaceEmbedding(student_id=student.id, embedding=[0.1] * 128, enrolled_at=utcnow()), session]); db.flush()
    raw = new_qr_token(session.id, utcnow() + timedelta(seconds=30))
    db.add(QRToken(session_id=session.id, token_hash=token_hash(raw), issued_at=utcnow(), expires_at=utcnow() + timedelta(seconds=30))); db.commit()
    return student_user, session, raw


def test_combined_checkin_writes_present_only_after_both_checks(db, monkeypatch):
    student_user, session, raw = checkin_setup(db)
    monkeypatch.setattr("app.main.httpx.post", lambda *args, **kwargs: FaceResponse(True))
    payload = CheckIn(session_id=session.id, qr_token=raw, frame_a="frame-a", frame_b="frame-b")

    result = check_in.__wrapped__(None, payload, db, student_user)

    assert result.status == "present"
    assert db.query(AttendanceRecord).count() == 1


def test_face_mismatch_is_audited_and_allows_a_later_valid_retry(db, monkeypatch):
    student_user, session, raw = checkin_setup(db)
    monkeypatch.setattr("app.main.httpx.post", lambda *args, **kwargs: FaceResponse(False))
    payload = CheckIn(session_id=session.id, qr_token=raw, frame_a="frame-a", frame_b="frame-b")

    with pytest.raises(HTTPException) as error:
        check_in.__wrapped__(None, payload, db, student_user)

    assert error.value.status_code == 422
    assert "may try again" in error.value.detail
    assert db.query(AttendanceRecord).count() == 0
    assert db.scalar(select(AttendanceAttempt)).status.value == "flagged"

    monkeypatch.setattr("app.main.httpx.post", lambda *args, **kwargs: FaceResponse(True))
    result = check_in.__wrapped__(None, payload, db, student_user)

    assert result.status == "present"
    assert db.query(AttendanceRecord).count() == 1
    assert db.query(AttendanceAttempt).count() == 1
