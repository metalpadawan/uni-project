from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import AttendanceSession, ClassSchedule, Course, SessionStatus
from .security import utcnow


def _local_zone() -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def scheduled_window_for_today(schedule: ClassSchedule, now: datetime) -> tuple[datetime, datetime] | None:
    """Returns the (start, end) UTC window for this schedule's occurrence today, or None if today isn't its day."""
    local_now = now.astimezone(_local_zone())
    if local_now.weekday() != schedule.day_of_week:
        return None
    start_local = local_now.replace(
        hour=schedule.start_time.hour,
        minute=schedule.start_time.minute,
        second=0,
        microsecond=0,
    )
    end_local = start_local + timedelta(minutes=schedule.duration_minutes)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def sync_scheduled_sessions(db: Session) -> None:
    """Auto-closes sessions past their end time and auto-opens sessions whose scheduled window has started."""
    now = utcnow()

    for session in db.scalars(
        select(AttendanceSession).where(
            AttendanceSession.status == SessionStatus.open,
            AttendanceSession.ends_at <= now,
        )
    ):
        session.status = SessionStatus.closed

    schedules = db.execute(select(ClassSchedule, Course).join(Course, ClassSchedule.course_id == Course.id)).all()
    for schedule, course in schedules:
        window = scheduled_window_for_today(schedule, now)
        if not window:
            continue
        start_at, end_at = window
        if not (start_at <= now < end_at):
            continue
        already_exists = db.scalar(
            select(AttendanceSession.id).where(
                AttendanceSession.course_id == course.id,
                AttendanceSession.started_at == start_at,
            )
        )
        if already_exists:
            continue
        db.add(
            AttendanceSession(
                course_id=course.id,
                lecturer_id=course.lecturer_id,
                started_at=start_at,
                ends_at=end_at,
                status=SessionStatus.open,
            )
        )

    db.commit()
