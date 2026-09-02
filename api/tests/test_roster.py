from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import Base
from app.main import admin_overview, lecturer_roster, list_students, my_attendance
from app.models import (
    AttendanceAttempt,
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
    Course,
    CourseEnrollment,
    FaceEmbedding,
    PendingStudent,
    RegistrationStatus,
    SessionStatus,
    Student,
    User,
    UserRole,
)
from app.security import utcnow


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_user(db, role, email):
    u = User(name=email, email=email, password_hash=hash_password("password123"), role=role, created_at=utcnow())
    db.add(u)
    db.flush()
    return u


def make_student(db, email, matric_no):
    user = make_user(db, UserRole.student, email)
    student = Student(user_id=user.id, matric_no=matric_no, department="Computer Science", level=400)
    db.add(student)
    db.flush()
    db.add(FaceEmbedding(student_id=student.id, embedding=[0.1] * 128, enrolled_at=utcnow()))
    return user, student


def test_list_students_returns_the_full_roster(db):
    admin = make_user(db, UserRole.admin, "admin@example.test")
    make_student(db, "a@example.test", "21/CSC/001")
    make_student(db, "b@example.test", "21/CSC/002")
    db.commit()

    rows = list_students(db, admin)

    assert {r.matric_no for r in rows} == {"21/CSC/001", "21/CSC/002"}


def test_my_attendance_only_shows_the_callers_own_records(db):
    lecturer = make_user(db, UserRole.lecturer, "lecturer@example.test")
    user_a, student_a = make_student(db, "a@example.test", "21/CSC/001")
    user_b, student_b = make_student(db, "b@example.test", "21/CSC/002")
    course = Course(code="CSC 421", title="AI", lecturer_id=lecturer.id)
    db.add(course)
    db.flush()
    session = AttendanceSession(course_id=course.id, lecturer_id=lecturer.id, started_at=utcnow(), ends_at=utcnow() + timedelta(hours=1), status=SessionStatus.open)
    db.add(session)
    db.flush()
    # SQLite doesn't enforce FK constraints by default, so a placeholder qr_token_id is fine here.
    db.add(AttendanceRecord(session_id=session.id, student_id=student_a.id, face_match_score=0.95, qr_token_id="placeholder", marked_at=utcnow(), status=AttendanceStatus.present))
    db.add(AttendanceAttempt(session_id=session.id, student_id=student_b.id, face_match_score=0.2, qr_token_id="placeholder", attempted_at=utcnow(), status=AttendanceStatus.flagged))
    db.commit()

    rows_a = my_attendance(db, user_a)
    rows_b = my_attendance(db, user_b)

    assert len(rows_a) == 1 and rows_a[0].status == "present"
    assert len(rows_b) == 1 and rows_b[0].status == "flagged"


def test_lecturer_roster_only_includes_their_own_courses(db):
    owner = make_user(db, UserRole.lecturer, "owner@example.test")
    other = make_user(db, UserRole.lecturer, "other@example.test")
    _, student = make_student(db, "student@example.test", "21/CSC/001")
    owned_course = Course(code="CSC 421", title="AI", lecturer_id=owner.id)
    other_course = Course(code="CSC 311", title="Data Structures", lecturer_id=other.id)
    db.add_all([owned_course, other_course])
    db.flush()
    db.add(CourseEnrollment(course_id=owned_course.id, student_id=student.id))
    db.commit()

    roster = lecturer_roster(db, owner)

    assert len(roster) == 1
    assert roster[0].course_code == "CSC 421"
    assert roster[0].students[0].matric_no == "21/CSC/001"


def test_admin_overview_counts(db):
    admin = make_user(db, UserRole.admin, "admin@example.test")
    lecturer = make_user(db, UserRole.lecturer, "lecturer@example.test")
    make_student(db, "a@example.test", "21/CSC/001")
    db.add(Course(code="CSC 421", title="AI", lecturer_id=lecturer.id))
    db.add(
        PendingStudent(
            name="Pending One",
            email="pending@example.test",
            password_hash=hash_password("password123"),
            matric_no="21/CSC/900",
            department="Computer Science",
            level=400,
            face_embedding=[0.1] * 128,
            biometric_consent=True,
            status=RegistrationStatus.pending,
            requested_at=utcnow(),
        )
    )
    db.commit()

    overview = admin_overview(db, admin)

    assert overview.registered_students == 1
    assert overview.active_courses == 1
    assert overview.pending_registrations == 1
