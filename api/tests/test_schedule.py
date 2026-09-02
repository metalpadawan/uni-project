from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import settings
from app.database import Base
from app.main import add_schedule, delete_schedule
from app.models import AttendanceSession, ClassSchedule, Course, SessionStatus, User, UserRole
from app.scheduling import sync_scheduled_sessions
from app.schemas import ScheduleCreate
from app.security import utcnow


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def user(db, role, email):
    u = User(name=email, email=email, password_hash=hash_password("password123"), role=role, created_at=utcnow())
    db.add(u)
    db.flush()
    return u


def local_now():
    return utcnow().astimezone(ZoneInfo(settings.timezone))


def test_sync_opens_a_session_within_the_scheduled_window(db):
    lecturer = user(db, UserRole.lecturer, "lecturer@example.test")
    course = Course(code="CSC 421", title="AI", lecturer_id=lecturer.id)
    db.add(course)
    db.flush()
    now = local_now()
    schedule = ClassSchedule(course_id=course.id, day_of_week=now.weekday(), start_time=(now - timedelta(minutes=5)).time(), duration_minutes=30)
    db.add(schedule)
    db.commit()

    sync_scheduled_sessions(db)

    sessions = db.scalars(select(AttendanceSession).where(AttendanceSession.course_id == course.id)).all()
    assert len(sessions) == 1
    assert sessions[0].status == SessionStatus.open
    assert sessions[0].lecturer_id == lecturer.id


def test_sync_does_nothing_outside_the_scheduled_window(db):
    lecturer = user(db, UserRole.lecturer, "lecturer@example.test")
    course = Course(code="CSC 421", title="AI", lecturer_id=lecturer.id)
    db.add(course)
    db.flush()
    now = local_now()
    schedule = ClassSchedule(course_id=course.id, day_of_week=now.weekday(), start_time=(now + timedelta(hours=3)).time(), duration_minutes=30)
    db.add(schedule)
    db.commit()

    sync_scheduled_sessions(db)

    assert db.scalars(select(AttendanceSession).where(AttendanceSession.course_id == course.id)).all() == []


def test_sync_does_not_duplicate_an_already_open_scheduled_session(db):
    lecturer = user(db, UserRole.lecturer, "lecturer@example.test")
    course = Course(code="CSC 421", title="AI", lecturer_id=lecturer.id)
    db.add(course)
    db.flush()
    now = local_now()
    schedule = ClassSchedule(course_id=course.id, day_of_week=now.weekday(), start_time=(now - timedelta(minutes=5)).time(), duration_minutes=30)
    db.add(schedule)
    db.commit()

    sync_scheduled_sessions(db)
    sync_scheduled_sessions(db)

    assert len(db.scalars(select(AttendanceSession).where(AttendanceSession.course_id == course.id)).all()) == 1


def test_sync_closes_sessions_past_their_end_time(db):
    lecturer = user(db, UserRole.lecturer, "lecturer@example.test")
    course = Course(code="CSC 421", title="AI", lecturer_id=lecturer.id)
    db.add(course)
    db.flush()
    session = AttendanceSession(course_id=course.id, lecturer_id=lecturer.id, started_at=utcnow() - timedelta(hours=2), ends_at=utcnow() - timedelta(minutes=1), status=SessionStatus.open)
    db.add(session)
    db.commit()

    sync_scheduled_sessions(db)

    db.refresh(session)
    assert session.status == SessionStatus.closed


def test_add_schedule_rejects_a_course_owned_by_another_lecturer(db):
    owner = user(db, UserRole.lecturer, "owner@example.test")
    intruder = user(db, UserRole.lecturer, "intruder@example.test")
    db.commit()
    add_schedule(ScheduleCreate(course_code="CSC 421", course_title="AI", day_of_week=0, start_time="09:00", duration_minutes=60), db, owner)

    with pytest.raises(HTTPException) as error:
        add_schedule(ScheduleCreate(course_code="CSC 421", course_title="AI", day_of_week=1, start_time="10:00", duration_minutes=60), db, intruder)

    assert error.value.status_code == 403


def test_delete_schedule_rejects_a_non_owning_lecturer(db):
    owner = user(db, UserRole.lecturer, "owner@example.test")
    intruder = user(db, UserRole.lecturer, "intruder@example.test")
    db.commit()
    created = add_schedule(ScheduleCreate(course_code="CSC 421", course_title="AI", day_of_week=0, start_time="09:00", duration_minutes=60), db, owner)

    with pytest.raises(HTTPException) as error:
        delete_schedule(created.id, db, intruder)
    assert error.value.status_code == 404


def test_delete_schedule_allows_admin(db):
    owner = user(db, UserRole.lecturer, "owner@example.test")
    admin = user(db, UserRole.admin, "admin@example.test")
    db.commit()
    created = add_schedule(ScheduleCreate(course_code="CSC 421", course_title="AI", day_of_week=0, start_time="09:00", duration_minutes=60), db, owner)

    delete_schedule(created.id, db, admin)

    assert db.get(ClassSchedule, created.id) is None
