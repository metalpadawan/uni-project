import base64
import io
from datetime import timedelta
import re
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
import httpx
import qrcode
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import settings
from .database import Base, engine, get_db
from .auth import hash_password, redeem_refresh_token, require_roles, revoke_refresh_token, token_pair, verify_password
from .models import AttendanceAttempt, AttendanceRecord, AttendanceSession, AttendanceStatus, ClassSchedule, Course, CourseEnrollment, FaceEmbedding, PendingStudent, QRToken, RegistrationStatus, SessionStatus, Student, User, UserRole, uid
from .schemas import AdminOverviewOut, AttendanceHistoryOut, CheckIn, CheckInOut, CourseEnrollmentCreate, CourseEnrollmentOut, CourseOut, LecturerAttendanceRowOut, LecturerDashboardOut, LecturerLiveSessionOut, LecturerNextSessionOut, LoginRequest, NotificationOut, PendingStudentOut, QRTokenOut, QRVerify, QRVerifyOut, RefreshRequest, RegisterRequest, RejectRequest, RosterCourseOut, RosterStudentOut, ScheduleCreate, ScheduleOut, SessionCreate, SessionOut, StudentEnroll, StudentRegisterRequest, StudentRosterOut
from .scheduling import sync_scheduled_sessions
from .security import as_aware, new_qr_receipt, new_qr_token, qr_receipt_is_valid, signature_is_valid, token_hash, utcnow

Base.metadata.create_all(bind=engine)
app = FastAPI(title="SmartAttend API", version="0.1.0")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "core": "face+qr"}


@app.post("/auth/bootstrap", status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User.id).limit(1)):
        raise HTTPException(409, "Bootstrap is disabled after the first account is created.")
    user = User(name=payload.name, email=payload.email.lower(), password_hash=hash_password(payload.password), role=UserRole.admin, created_at=utcnow())
    db.add(user); db.commit()
    return token_pair(user, db)


@app.post("/auth/login")
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect.")
    return token_pair(user, db)


@app.post("/auth/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return token_pair(redeem_refresh_token(payload.refresh_token, db), db)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    revoke_refresh_token(payload.refresh_token, db)


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    try: role = UserRole(payload.role.lower())
    except ValueError: raise HTTPException(422, "Role must be admin, lecturer, or student.")
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "An account with this email already exists.")
    user = User(name=payload.name, email=payload.email.lower(), password_hash=hash_password(payload.password), role=role, created_at=utcnow())
    db.add(user); db.commit()
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role.value}


@app.post("/auth/demo/{role}")
@limiter.limit("5/minute")
def demo_login(request: Request, role: UserRole, db: Session = Depends(get_db)):
    if not settings.demo_mode:
        raise HTTPException(404, "Demo login is disabled.")
    email = f"{role.value}@smartattend.local"
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(name={UserRole.admin:"System Admin",UserRole.lecturer:"Dr. E. E. Umoh",UserRole.student:"Jecintha Odok"}[role], email=email, password_hash=hash_password("local-demo-password"), role=role, created_at=utcnow())
        db.add(user); db.flush()
        if role == UserRole.student:
            student = Student(user_id=user.id, matric_no="21/CSC/156", department="Computer Science", level=400)
            db.add(student); db.flush()
            db.add(FaceEmbedding(student_id=student.id, embedding=[0.1] * 128, enrolled_at=utcnow()))
            for course in db.scalars(select(Course)).all():
                db.add(CourseEnrollment(course_id=course.id, student_id=student.id))
        db.commit()
    return token_pair(user, db)


def create_student_account(db: Session, *, name: str, email: str, password_hash: str, matric_no: str, department: str, level: int, embedding: list[float] | None = None) -> Student:
    if db.scalar(select(Student).where(Student.matric_no == matric_no)):
        raise HTTPException(409, "A student with this matric number already exists.")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")
    user = User(name=name, email=email, password_hash=password_hash, role=UserRole.student, created_at=utcnow())
    db.add(user); db.flush()
    student = Student(user_id=user.id, matric_no=matric_no, department=department, level=level)
    db.add(student); db.flush()
    if embedding is not None:
        db.add(FaceEmbedding(student_id=student.id, embedding=embedding, enrolled_at=utcnow()))
    return student


@app.post("/students", status_code=status.HTTP_201_CREATED)
def enroll_student(payload: StudentEnroll, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    student = create_student_account(
        db,
        name=payload.name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.temporary_password),
        matric_no=payload.matric_no,
        department=payload.department,
        level=payload.level,
    )
    db.commit()
    return {"id": student.id, "name": payload.name, "matric_no": student.matric_no, "face_enrolled": False}


@app.post("/auth/register-student", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register_student(request: Request, payload: StudentRegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")
    if db.scalar(select(PendingStudent).where(PendingStudent.email == email, PendingStudent.status == RegistrationStatus.pending)):
        raise HTTPException(409, "A registration request for this email is already pending review.")
    request_row = PendingStudent(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        matric_no=payload.matric_no,
        department=payload.department,
        level=payload.level,
        face_embedding=None,
        biometric_consent=False,
        status=RegistrationStatus.pending,
        requested_at=utcnow(),
    )
    db.add(request_row)
    db.commit()
    return {"status": "pending", "message": "Your registration has been submitted. An admin will review it before you can sign in."}


@app.get("/students/pending", response_model=list[PendingStudentOut])
def list_pending_students(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    rows = db.scalars(select(PendingStudent).where(PendingStudent.status == RegistrationStatus.pending).order_by(PendingStudent.requested_at)).all()
    return [PendingStudentOut(id=r.id, name=r.name, email=r.email, matric_no=r.matric_no, department=r.department, level=r.level, status=r.status.value, requested_at=r.requested_at) for r in rows]


@app.post("/students/pending/{request_id}/approve", status_code=status.HTTP_201_CREATED)
def approve_pending_student(request_id: str, db: Session = Depends(get_db), admin: User = Depends(require_roles(UserRole.admin))):
    pending = db.get(PendingStudent, request_id)
    if not pending or pending.status != RegistrationStatus.pending:
        raise HTTPException(404, "Pending registration was not found.")
    student = create_student_account(
        db,
        name=pending.name,
        email=pending.email,
        password_hash=pending.password_hash,
        matric_no=pending.matric_no,
        department=pending.department,
        level=pending.level,
        embedding=pending.face_embedding,
    )
    pending.status = RegistrationStatus.approved
    pending.reviewed_at = utcnow()
    pending.reviewed_by = admin.id
    db.commit()
    return {"id": student.id, "name": pending.name, "matric_no": student.matric_no, "face_enrolled": pending.face_embedding is not None}


@app.post("/students/pending/{request_id}/reject")
def reject_pending_student(request_id: str, payload: RejectRequest, db: Session = Depends(get_db), admin: User = Depends(require_roles(UserRole.admin))):
    pending = db.get(PendingStudent, request_id)
    if not pending or pending.status != RegistrationStatus.pending:
        raise HTTPException(404, "Pending registration was not found.")
    pending.status = RegistrationStatus.rejected
    pending.reviewed_at = utcnow()
    pending.reviewed_by = admin.id
    pending.rejection_reason = payload.reason
    db.commit()
    return {"id": pending.id, "status": pending.status.value}


@app.get("/students", response_model=list[StudentRosterOut])
def list_students(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    rows = db.execute(select(Student, User).join(User, Student.user_id == User.id).order_by(User.name)).all()
    return [StudentRosterOut(id=student.id, name=user.name, email=user.email, matric_no=student.matric_no, department=student.department, level=student.level) for student, user in rows]


@app.get("/students/me/attendance", response_model=list[AttendanceHistoryOut])
def my_attendance(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.student))):
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if not student:
        raise HTTPException(404, "Student profile was not found.")
    records = db.execute(
        select(AttendanceRecord, AttendanceSession, Course)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .join(Course, AttendanceSession.course_id == Course.id)
        .where(AttendanceRecord.student_id == student.id)
    ).all()
    attempts = db.execute(
        select(AttendanceAttempt, AttendanceSession, Course)
        .join(AttendanceSession, AttendanceAttempt.session_id == AttendanceSession.id)
        .join(Course, AttendanceSession.course_id == Course.id)
        .where(AttendanceAttempt.student_id == student.id)
    ).all()
    rows = [
        AttendanceHistoryOut(course_code=course.code, course_title=course.title, status=record.status.value, time=record.marked_at, face_match_score=record.face_match_score)
        for record, session, course in records
    ]
    rows.extend(
        AttendanceHistoryOut(course_code=course.code, course_title=course.title, status=attempt.status.value, time=attempt.attempted_at, face_match_score=attempt.face_match_score)
        for attempt, session, course in attempts
    )
    return sorted(rows, key=lambda row: row.time, reverse=True)


def _next_scheduled_start(schedule: ClassSchedule, now):
    """Return the next occurrence of a weekly class in the configured timezone."""
    local_now = now.astimezone(ZoneInfo(settings.timezone))
    days_until = (schedule.day_of_week - local_now.weekday()) % 7
    start = (local_now + timedelta(days=days_until)).replace(
        hour=schedule.start_time.hour,
        minute=schedule.start_time.minute,
        second=0,
        microsecond=0,
    )
    if start <= local_now:
        start += timedelta(days=7)
    return start.astimezone(now.tzinfo)


@app.get("/notifications", response_model=list[NotificationOut])
def notifications(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.student, UserRole.lecturer, UserRole.admin))):
    """Return a small, role-appropriate notification feed from persisted data."""
    sync_scheduled_sessions(db)
    now = utcnow()
    items: list[NotificationOut] = []

    if user.role == UserRole.student:
        student = db.scalar(select(Student).where(Student.user_id == user.id))
        if not student:
            raise HTTPException(404, "Student profile was not found.")
        session_rows = db.execute(
            select(AttendanceSession, Course)
            .join(Course, AttendanceSession.course_id == Course.id)
            .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
            .where(
                CourseEnrollment.student_id == student.id,
                AttendanceSession.status == SessionStatus.open,
                AttendanceSession.ends_at > now,
            )
            .order_by(AttendanceSession.started_at)
        ).all()
        for session, course in session_rows:
            live = as_aware(session.started_at) <= now
            items.append(NotificationOut(
                id=f"session-{session.id}",
                kind="session-live" if live else "session-planned",
                title=f"{course.code} attendance {'is open' if live else 'is scheduled'}",
                detail=("Open Check in to scan the classroom QR code before it closes."
                        if live else f"Opens {as_aware(session.started_at).astimezone(ZoneInfo(settings.timezone)).strftime('%a, %d %b at %I:%M %p')}."),
                occurred_at=session.started_at,
                session_id=session.id,
            ))
        schedule_rows = db.execute(
            select(ClassSchedule, Course)
            .join(Course, ClassSchedule.course_id == Course.id)
            .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
            .where(CourseEnrollment.student_id == student.id)
        ).all()
        for schedule, course in schedule_rows:
            starts_at = _next_scheduled_start(schedule, now)
            items.append(NotificationOut(
                id=f"weekly-{schedule.id}-{starts_at.date().isoformat()}",
                kind="weekly-schedule",
                title=f"{course.code} weekly class",
                detail=f"Attendance is scheduled to open {starts_at.astimezone(ZoneInfo(settings.timezone)).strftime('%a, %d %b at %I:%M %p')}.",
                occurred_at=starts_at,
            ))
        record_rows = db.execute(
            select(AttendanceRecord, Course)
            .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
            .join(Course, AttendanceSession.course_id == Course.id)
            .where(AttendanceRecord.student_id == student.id)
            .order_by(AttendanceRecord.marked_at.desc())
            .limit(10)
        ).all()
        for record, course in record_rows:
            items.append(NotificationOut(
                id=f"attendance-{record.id}",
                kind="attendance-recorded",
                title=f"Attendance recorded for {course.code}",
                detail="Face and QR verification were successful.",
                occurred_at=record.marked_at,
                session_id=record.session_id,
            ))
    elif user.role == UserRole.lecturer:
        session_rows = db.execute(
            select(AttendanceSession, Course)
            .join(Course, AttendanceSession.course_id == Course.id)
            .where(
                AttendanceSession.lecturer_id == user.id,
                AttendanceSession.status == SessionStatus.open,
                AttendanceSession.ends_at > now,
            )
            .order_by(AttendanceSession.started_at)
        ).all()
        for session, course in session_rows:
            live = as_aware(session.started_at) <= now
            items.append(NotificationOut(
                id=f"session-{session.id}",
                kind="session-live" if live else "session-planned",
                title=f"{course.code} attendance {'is live' if live else 'is planned'}",
                detail="Students can check in now." if live else "It will open automatically for enrolled students.",
                occurred_at=session.started_at,
                session_id=session.id,
            ))
        record_rows = db.execute(
            select(AttendanceRecord, Course)
            .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
            .join(Course, AttendanceSession.course_id == Course.id)
            .where(AttendanceSession.lecturer_id == user.id)
            .order_by(AttendanceRecord.marked_at.desc())
            .limit(10)
        ).all()
        for record, course in record_rows:
            items.append(NotificationOut(
                id=f"attendance-{record.id}",
                kind="attendance-recorded",
                title=f"A student checked in to {course.code}",
                detail="Face and QR verification were successful.",
                occurred_at=record.marked_at,
                session_id=record.session_id,
            ))
    else:
        pending = db.scalar(select(func.count(PendingStudent.id)).where(PendingStudent.status == RegistrationStatus.pending)) or 0
        if pending:
            items.append(NotificationOut(
                id="pending-students",
                kind="registration-review",
                title="Student registrations need review",
                detail=f"{pending} registration{'s' if pending != 1 else ''} await approval.",
                occurred_at=now,
            ))

    priority = {"session-live": 0, "attendance-recorded": 1, "session-planned": 2, "weekly-schedule": 3, "registration-review": 0}
    return sorted(items, key=lambda item: (priority.get(item.kind, 9), item.occurred_at), reverse=False)[:20]


def get_or_create_course(db: Session, code: str, title: str, lecturer: User) -> Course:
    course = db.scalar(select(Course).where(Course.code == code))
    if not course:
        course = Course(code=code, title=title, lecturer_id=lecturer.id)
        db.add(course)
        db.flush()
    elif course.lecturer_id != lecturer.id:
        raise HTTPException(403, "This course is assigned to another lecturer.")
    return course


@app.get("/admin/overview", response_model=AdminOverviewOut)
def admin_overview(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    return AdminOverviewOut(
        registered_students=db.scalar(select(func.count()).select_from(Student)) or 0,
        active_courses=db.scalar(select(func.count()).select_from(Course)) or 0,
        pending_registrations=db.scalar(select(func.count()).select_from(PendingStudent).where(PendingStudent.status == RegistrationStatus.pending)) or 0,
    )


@app.get("/roster", response_model=list[RosterCourseOut])
def lecturer_roster(db: Session = Depends(get_db), lecturer: User = Depends(require_roles(UserRole.lecturer))):
    courses = db.scalars(select(Course).where(Course.lecturer_id == lecturer.id).order_by(Course.code)).all()
    result = []
    for course in courses:
        rows = db.execute(
            select(Student, User)
            .join(CourseEnrollment, CourseEnrollment.student_id == Student.id)
            .join(User, Student.user_id == User.id)
            .where(CourseEnrollment.course_id == course.id)
            .order_by(User.name)
        ).all()
        result.append(
            RosterCourseOut(
                course_code=course.code,
                course_title=course.title,
                students=[RosterStudentOut(name=user.name, matric_no=student.matric_no, department=student.department, level=student.level) for student, user in rows],
            )
        )
    return result


@app.get("/courses", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.lecturer, UserRole.admin))):
    query = select(Course)
    if user.role == UserRole.lecturer:
        query = query.where(Course.lecturer_id == user.id)
    courses = db.scalars(query.order_by(Course.code)).all()
    return [CourseOut(id=c.id, code=c.code, title=c.title) for c in courses]


def managed_course(course_id: str, db: Session, user: User) -> Course:
    course = db.get(Course, course_id)
    if not course or (user.role == UserRole.lecturer and course.lecturer_id != user.id):
        raise HTTPException(404, "Course was not found.")
    return course


@app.get("/courses/{course_id}/enrollments", response_model=list[CourseEnrollmentOut])
def list_course_enrollments(course_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.lecturer, UserRole.admin))):
    course = managed_course(course_id, db, user)
    rows = db.execute(
        select(Student, User)
        .join(CourseEnrollment, CourseEnrollment.student_id == Student.id)
        .join(User, Student.user_id == User.id)
        .where(CourseEnrollment.course_id == course.id)
        .order_by(User.name)
    ).all()
    return [
        CourseEnrollmentOut(
            student_id=student.id,
            name=account.name,
            matric_no=student.matric_no,
            department=student.department,
            level=student.level,
        )
        for student, account in rows
    ]


@app.post("/courses/{course_id}/enrollments", response_model=CourseEnrollmentOut, status_code=status.HTTP_201_CREATED)
def add_course_enrollment(course_id: str, payload: CourseEnrollmentCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.lecturer, UserRole.admin))):
    course = managed_course(course_id, db, user)
    student = db.scalar(select(Student).where(Student.matric_no == payload.matric_no))
    if not student:
        raise HTTPException(404, "Student was not found.")
    if db.scalar(select(CourseEnrollment).where(CourseEnrollment.course_id == course.id, CourseEnrollment.student_id == student.id)):
        raise HTTPException(409, "This student is already enrolled in the course.")
    db.add(CourseEnrollment(course_id=course.id, student_id=student.id))
    db.commit()
    account = db.get(User, student.user_id)
    return CourseEnrollmentOut(student_id=student.id, name=account.name, matric_no=student.matric_no, department=student.department, level=student.level)


@app.delete("/courses/{course_id}/enrollments/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_course_enrollment(course_id: str, student_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.lecturer, UserRole.admin))):
    course = managed_course(course_id, db, user)
    enrollment = db.scalar(select(CourseEnrollment).where(CourseEnrollment.course_id == course.id, CourseEnrollment.student_id == student_id))
    if not enrollment:
        raise HTTPException(404, "Course enrollment was not found.")
    db.delete(enrollment)
    db.commit()


@app.post("/schedule", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def add_schedule(payload: ScheduleCreate, db: Session = Depends(get_db), lecturer: User = Depends(require_roles(UserRole.lecturer))):
    course = get_or_create_course(db, payload.course_code, payload.course_title, lecturer)
    entry = ClassSchedule(course_id=course.id, day_of_week=payload.day_of_week, start_time=payload.start_time, duration_minutes=payload.duration_minutes)
    db.add(entry)
    db.commit()
    return ScheduleOut(id=entry.id, course_code=course.code, course_title=course.title, day_of_week=entry.day_of_week, start_time=entry.start_time, duration_minutes=entry.duration_minutes)


@app.get("/schedule", response_model=list[ScheduleOut])
def list_schedule(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.lecturer, UserRole.admin))):
    query = select(ClassSchedule, Course).join(Course, ClassSchedule.course_id == Course.id)
    if user.role == UserRole.lecturer:
        query = query.where(Course.lecturer_id == user.id)
    rows = db.execute(query.order_by(ClassSchedule.day_of_week, ClassSchedule.start_time)).all()
    return [ScheduleOut(id=entry.id, course_code=course.code, course_title=course.title, day_of_week=entry.day_of_week, start_time=entry.start_time, duration_minutes=entry.duration_minutes) for entry, course in rows]


@app.delete("/schedule/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.lecturer, UserRole.admin))):
    row = db.execute(select(ClassSchedule, Course).join(Course, ClassSchedule.course_id == Course.id).where(ClassSchedule.id == schedule_id)).first()
    if not row:
        raise HTTPException(404, "Schedule entry was not found.")
    entry, course = row
    if user.role == UserRole.lecturer and course.lecturer_id != user.id:
        raise HTTPException(404, "Schedule entry was not found.")
    db.delete(entry)
    db.commit()


@app.get("/sessions/current", response_model=SessionOut | None)
def current_session(db: Session = Depends(get_db), lecturer: User = Depends(require_roles(UserRole.lecturer))):
    sync_scheduled_sessions(db)
    now = utcnow()
    row = db.execute(
        select(AttendanceSession, Course)
        .join(Course, AttendanceSession.course_id == Course.id)
        .where(
            AttendanceSession.lecturer_id == lecturer.id,
            AttendanceSession.status == SessionStatus.open,
            AttendanceSession.started_at <= now,
            AttendanceSession.ends_at > now,
        )
        .order_by(AttendanceSession.started_at.desc())
    ).first()
    if not row:
        return None
    session, course = row
    return SessionOut(session_id=session.id, course_code=course.code, status=session.status.value, starts_at=session.started_at, ends_at=session.ends_at)


def _next_schedule_occurrence(schedule: ClassSchedule, now):
    local_now = now.astimezone(ZoneInfo(settings.timezone))
    days_until = (schedule.day_of_week - local_now.weekday()) % 7
    starts_at = (local_now + timedelta(days=days_until)).replace(
        hour=schedule.start_time.hour,
        minute=schedule.start_time.minute,
        second=0,
        microsecond=0,
    )
    if starts_at <= local_now:
        starts_at += timedelta(days=7)
    starts_at = starts_at.astimezone(now.tzinfo)
    return starts_at, starts_at + timedelta(minutes=schedule.duration_minutes)


@app.get("/lecturer/dashboard", response_model=LecturerDashboardOut)
def lecturer_dashboard(db: Session = Depends(get_db), lecturer: User = Depends(require_roles(UserRole.lecturer))):
    """Live lecturer dashboard data sourced only from persisted sessions and records."""
    sync_scheduled_sessions(db)
    now = utcnow()
    local_now = now.astimezone(ZoneInfo(settings.timezone))
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(now.tzinfo)
    day_end = day_start + timedelta(days=1)
    today_sessions = db.scalar(
        select(func.count(AttendanceSession.id)).where(
            AttendanceSession.lecturer_id == lecturer.id,
            AttendanceSession.started_at >= day_start,
            AttendanceSession.started_at < day_end,
        )
    ) or 0
    completed_sessions = db.scalar(
        select(func.count(AttendanceSession.id)).where(
            AttendanceSession.lecturer_id == lecturer.id,
            AttendanceSession.started_at >= day_start,
            AttendanceSession.started_at < day_end,
            AttendanceSession.status == SessionStatus.closed,
        )
    ) or 0
    current = db.execute(
        select(AttendanceSession, Course)
        .join(Course, AttendanceSession.course_id == Course.id)
        .where(
            AttendanceSession.lecturer_id == lecturer.id,
            AttendanceSession.status == SessionStatus.open,
            AttendanceSession.started_at <= now,
            AttendanceSession.ends_at > now,
        )
        .order_by(AttendanceSession.started_at.desc())
    ).first()
    live_session = None
    if current:
        session, course = current
        enrolled_students = db.scalar(select(func.count(CourseEnrollment.id)).where(CourseEnrollment.course_id == course.id)) or 0
        records = db.execute(
            select(AttendanceRecord, Student, User)
            .join(Student, AttendanceRecord.student_id == Student.id)
            .join(User, Student.user_id == User.id)
            .where(AttendanceRecord.session_id == session.id)
            .order_by(AttendanceRecord.marked_at.desc())
        ).all()
        rows = [
            LecturerAttendanceRowOut(
                id=student.matric_no,
                name=account.name,
                time=record.marked_at,
                status=record.status.value,
                face_match_score=record.face_match_score,
            )
            for record, student, account in records
        ]
        present_students = len(rows)
        live_session = LecturerLiveSessionOut(
            session_id=session.id,
            course_code=course.code,
            course_title=course.title,
            starts_at=session.started_at,
            ends_at=session.ends_at,
            enrolled_students=enrolled_students,
            present_students=present_students,
            face_verified=present_students,
            qr_verified=present_students,
            records=rows,
        )

    candidates = []
    future_sessions = db.execute(
        select(AttendanceSession, Course)
        .join(Course, AttendanceSession.course_id == Course.id)
        .where(
            AttendanceSession.lecturer_id == lecturer.id,
            AttendanceSession.status == SessionStatus.open,
            AttendanceSession.started_at > now,
        )
    ).all()
    candidates.extend((as_aware(session.started_at), as_aware(session.ends_at), course) for session, course in future_sessions)
    schedules = db.execute(
        select(ClassSchedule, Course)
        .join(Course, ClassSchedule.course_id == Course.id)
        .where(Course.lecturer_id == lecturer.id)
    ).all()
    candidates.extend((*_next_schedule_occurrence(schedule, now), course) for schedule, course in schedules)
    candidates.sort(key=lambda candidate: candidate[0])
    next_session = None
    if candidates:
        starts_at, ends_at, course = candidates[0]
        next_session = LecturerNextSessionOut(course_code=course.code, course_title=course.title, starts_at=starts_at, ends_at=ends_at)
    return LecturerDashboardOut(
        todays_sessions=today_sessions,
        completed_sessions=completed_sessions,
        live_session=live_session,
        next_session=next_session,
    )


@app.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: Session = Depends(get_db), lecturer: User = Depends(require_roles(UserRole.lecturer))):
    course = get_or_create_course(db, payload.course_code, payload.course_title, lecturer)
    now = utcnow()
    starts_at = as_aware(payload.starts_at) if payload.starts_at else now
    if starts_at < now:
        raise HTTPException(422, "A planned session must start in the future. Choose 'Start now' for immediate attendance.")
    if starts_at > now + timedelta(days=31):
        raise HTTPException(422, "Attendance can be planned no more than one month (31 days) ahead.")
    session = AttendanceSession(
        course_id=course.id,
        lecturer_id=lecturer.id,
        started_at=starts_at,
        ends_at=starts_at + timedelta(minutes=payload.duration_minutes),
        status=SessionStatus.open,
    )
    db.add(session)
    if settings.demo_mode:
        demo_student_user = db.scalar(select(User).where(User.email == "student@smartattend.local"))
        demo_student = db.scalar(select(Student).where(Student.user_id == demo_student_user.id)) if demo_student_user else None
        if demo_student and not db.scalar(select(CourseEnrollment).where(CourseEnrollment.course_id == course.id, CourseEnrollment.student_id == demo_student.id)):
            db.add(CourseEnrollment(course_id=course.id, student_id=demo_student.id))
    db.commit()
    session_status = "scheduled" if starts_at > now else session.status.value
    return SessionOut(session_id=session.id, course_code=course.code, status=session_status, starts_at=session.started_at, ends_at=session.ends_at)


@app.get("/sessions/planned", response_model=list[SessionOut])
def list_planned_sessions(db: Session = Depends(get_db), lecturer: User = Depends(require_roles(UserRole.lecturer))):
    """List this lecturer's current and upcoming one-time attendance sessions."""
    sync_scheduled_sessions(db)
    now = utcnow()
    rows = db.execute(
        select(AttendanceSession, Course)
        .join(Course, AttendanceSession.course_id == Course.id)
        .where(
            AttendanceSession.lecturer_id == lecturer.id,
            AttendanceSession.status == SessionStatus.open,
            AttendanceSession.ends_at > now,
        )
        .order_by(AttendanceSession.started_at)
    ).all()
    return [
        SessionOut(
            session_id=session.id,
            course_code=course.code,
            status="scheduled" if as_aware(session.started_at) > now else session.status.value,
            starts_at=session.started_at,
            ends_at=session.ends_at,
        )
        for session, course in rows
    ]


@app.get("/sessions/open")
def list_open_sessions(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.student))):
    sync_scheduled_sessions(db)
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if not student:
        raise HTTPException(404, "Student profile was not found.")
    now = utcnow()
    rows = db.execute(
        select(AttendanceSession, Course)
        .join(Course, AttendanceSession.course_id == Course.id)
        .where(
            AttendanceSession.status == SessionStatus.open,
            AttendanceSession.started_at <= now,
            AttendanceSession.ends_at > now,
        )
        .order_by(AttendanceSession.ends_at)
    ).all()
    return [
        {
            "session_id": session.id,
            "course_code": course.code,
            "course_title": course.title,
            "starts_at": session.started_at,
            "ends_at": session.ends_at,
        }
        for session, course in rows
    ]


@app.post("/sessions/{session_id}/qr", response_model=QRTokenOut)
def rotate_qr(session_id: str, request: Request, db: Session = Depends(get_db), lecturer: User = Depends(require_roles(UserRole.lecturer))):
    sync_scheduled_sessions(db)
    session = db.get(AttendanceSession, session_id)
    now = utcnow()
    if not session or session.lecturer_id != lecturer.id or session.status != SessionStatus.open or as_aware(session.started_at) > now or as_aware(session.ends_at) <= now:
        raise HTTPException(409, "Session is closed or expired.")
    expires_at = min(now + timedelta(seconds=settings.qr_ttl_seconds), as_aware(session.ends_at))
    raw = new_qr_token(session_id, expires_at)
    row = QRToken(session_id=session_id, token_hash=token_hash(raw), issued_at=now, expires_at=expires_at)
    db.add(row)
    db.commit()
    # The signed token is scanned only inside a signed-in student check-in.
    # QR possession alone can never record attendance without a live face match.
    qr_image = qrcode.make(raw)
    buffer = io.BytesIO()
    qr_image.save(buffer, format="PNG")
    qr_data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
    return QRTokenOut(token=raw, qr_data_url=qr_data_url, expires_at=expires_at, expires_in=settings.qr_ttl_seconds)


@app.post("/sessions/{session_id}/close")
def close_session(session_id: str, db: Session = Depends(get_db), lecturer: User = Depends(require_roles(UserRole.lecturer))):
    session = db.get(AttendanceSession, session_id)
    if not session or session.lecturer_id != lecturer.id:
        raise HTTPException(404, "Attendance session was not found.")
    session.status = SessionStatus.closed
    db.commit()
    return {"session_id": session.id, "status": session.status.value}


@app.get("/sessions/{session_id}/attendance")
def session_attendance(session_id: str, db: Session = Depends(get_db), lecturer: User = Depends(require_roles(UserRole.lecturer))):
    session = db.get(AttendanceSession, session_id)
    if not session or session.lecturer_id != lecturer.id:
        raise HTTPException(404, "Attendance session was not found.")
    records = db.execute(
        select(AttendanceRecord, Student, User)
        .join(Student, AttendanceRecord.student_id == Student.id)
        .join(User, Student.user_id == User.id)
        .where(AttendanceRecord.session_id == session.id)
        .order_by(AttendanceRecord.marked_at)
    ).all()
    attempts = db.execute(
        select(AttendanceAttempt, Student, User)
        .join(Student, AttendanceAttempt.student_id == Student.id)
        .join(User, Student.user_id == User.id)
        .where(AttendanceAttempt.session_id == session.id)
        .order_by(AttendanceAttempt.attempted_at)
    ).all()
    rows = [
        {
            "id": student.matric_no,
            "name": user.name,
            "time": record.marked_at,
            "status": record.status.value,
            "face_match_score": record.face_match_score,
        }
        for record, student, user in records
    ]
    rows.extend(
        {
            "id": student.matric_no,
            "name": user.name,
            "time": attempt.attempted_at,
            "status": attempt.status.value,
            "face_match_score": attempt.face_match_score,
        }
        for attempt, student, user in attempts
    )
    return sorted(rows, key=lambda row: row["time"])


def _capture_component(value: str) -> str:
    """Create a readable but filesystem-safe directory component."""
    result = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return result[:80] or "student"


def attendance_capture(*, frame: str, student: Student, student_name: str, marked_at, attendance_id: str) -> tuple[str, bytes]:
    """Return a private logical path and image bytes for a verified check-in."""
    try:
        encoded = frame.split(",", 1)[-1]
        image = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise HTTPException(422, "The attendance photo could not be stored.")
    # Browser capture is resized/compressed before upload. Keeping each image
    # bounded protects the database from an accidental oversized upload.
    if not image or len(image) > 1024 * 1024:
        raise HTTPException(422, "The attendance photo is invalid or too large.")

    local_time = marked_at.astimezone(ZoneInfo(settings.timezone))
    student_folder = f"{_capture_component(student_name)}-{_capture_component(student.matric_no)}"
    relative_dir = f"{student_folder}/{local_time.strftime('%Y-%m-%d')}"
    filename = f"{local_time.strftime('%H-%M-%S')}_{attendance_id}.jpg"
    return f"{relative_dir}/{filename}", image


@app.post("/attendance/qr-verify", response_model=QRVerifyOut)
@limiter.limit("10/minute")
def verify_qr(request: Request, payload: QRVerify, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.student))):
    """Verify a QR immediately and preserve that result for the face step."""
    sync_scheduled_sessions(db)
    now = utcnow()
    session = db.get(AttendanceSession, payload.session_id)
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    qr = db.scalar(select(QRToken).where(QRToken.token_hash == token_hash(payload.qr_token), QRToken.session_id == payload.session_id))
    if not session or session.status != SessionStatus.open or as_aware(session.started_at) > now or as_aware(session.ends_at) <= now:
        raise HTTPException(409, "Attendance session is not open.")
    if not student:
        raise HTTPException(404, "Student profile was not found.")
    if not qr or not signature_is_valid(payload.qr_token) or as_aware(qr.expires_at) < now:
        raise HTTPException(422, "QR expired or invalid. Ask the lecturer to refresh it.")
    expires_at = min(now + timedelta(minutes=2), as_aware(session.ends_at))
    return QRVerifyOut(
        receipt=new_qr_receipt(session.id, student.id, expires_at),
        expires_at=expires_at,
    )


@app.post("/attendance/checkin", response_model=CheckInOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def check_in(request: Request, payload: CheckIn, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.student))):
    sync_scheduled_sessions(db)
    now = utcnow()
    session = db.get(AttendanceSession, payload.session_id)
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    qr = db.scalar(select(QRToken).where(QRToken.token_hash == token_hash(payload.qr_token), QRToken.session_id == payload.session_id))
    if not session or session.status != SessionStatus.open or as_aware(session.started_at) > now or as_aware(session.ends_at) <= now:
        raise HTTPException(409, "Attendance session is not open.")
    if not student:
        raise HTTPException(404, "Student profile was not found.")
    qr_valid = bool(
        qr
        and (
            qr_receipt_is_valid(payload.qr_receipt, session.id, student.id)
            if payload.qr_receipt
            else signature_is_valid(payload.qr_token) and as_aware(qr.expires_at) >= now
        )
    )
    if not qr_valid:
        raise HTTPException(422, "QR expired or invalid. Ask the lecturer to refresh it.")
    face_template = db.scalar(select(FaceEmbedding).where(FaceEmbedding.student_id == student.id))
    if not face_template:
        raise HTTPException(422, "No enrolled face template was found for this student.")
    try:
        response = httpx.post(
            f"{settings.face_service_url}/verify",
            json={"enrolled_embedding": face_template.embedding, "frame_a": payload.frame_a, "frame_b": payload.frame_b},
            timeout=settings.face_service_timeout_seconds,
        )
        face_result = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "Face verification service is unavailable. Please try again.")
    face_valid = response.is_success and bool(face_result.get("matched"))
    face_score = float(face_result.get("score", 0.0))
    if not face_valid:
        db.add(
            AttendanceAttempt(
                session_id=session.id,
                student_id=student.id,
                face_match_score=face_score,
                qr_token_id=qr.id,
                attempted_at=now,
                status=AttendanceStatus.flagged,
            )
        )
        db.commit()
        raise HTTPException(
            422,
            "Face not recognized or liveness check failed. The attempt was flagged for lecturer review; you may try again.",
        )

    if db.scalar(
        select(AttendanceRecord.id).where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.student_id == student.id,
        )
    ):
        raise HTTPException(409, "Attendance has already been recorded for this session.")

    record = AttendanceRecord(
        id=uid(),
        session_id=session.id,
        student_id=student.id,
        face_match_score=face_score,
        qr_token_id=qr.id,
        marked_at=now,
        status=AttendanceStatus.present,
    )
    record.capture_path, record.capture_image = attendance_capture(
        frame=payload.frame_a,
        student=student,
        student_name=user.name,
        marked_at=now,
        attendance_id=record.id,
    )
    # The authenticated student's profile supplies the course membership. It
    # is saved only after the QR and face checks have both passed, so a student
    # never needs to type a matriculation number to access a live session.
    if not db.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == session.course_id,
            CourseEnrollment.student_id == student.id,
        )
    ):
        db.add(CourseEnrollment(course_id=session.course_id, student_id=student.id))
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Attendance has already been recorded for this session.")
    return CheckInOut(attendance_id=record.id, status=record.status.value, face_match_score=record.face_match_score, marked_at=record.marked_at, message="Face and QR verified. Attendance marked present.")
