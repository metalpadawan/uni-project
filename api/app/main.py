import base64
import io
from datetime import timedelta

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
from .models import AttendanceAttempt, AttendanceRecord, AttendanceSession, AttendanceStatus, ClassSchedule, Course, CourseEnrollment, FaceEmbedding, PendingStudent, QRToken, RegistrationStatus, SessionStatus, Student, User, UserRole
from .schemas import AdminOverviewOut, AttendanceHistoryOut, CheckIn, CheckInOut, CourseOut, LoginRequest, PendingStudentOut, QRTokenOut, RefreshRequest, RegisterRequest, RejectRequest, RosterCourseOut, RosterStudentOut, ScheduleCreate, ScheduleOut, SessionCreate, SessionOut, StudentEnroll, StudentRegisterRequest, StudentRosterOut
from .scheduling import sync_scheduled_sessions
from .security import as_aware, new_qr_token, signature_is_valid, token_hash, utcnow

Base.metadata.create_all(bind=engine)
app = FastAPI(title="SmartAttend API", version="0.1.0")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",")], allow_methods=["*"], allow_headers=["*"])


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


def create_student_account(db: Session, *, name: str, email: str, password_hash: str, matric_no: str, department: str, level: int, face_embedding: list[float]) -> Student:
    if db.scalar(select(Student).where(Student.matric_no == matric_no)):
        raise HTTPException(409, "A student with this matric number already exists.")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")
    user = User(name=name, email=email, password_hash=password_hash, role=UserRole.student, created_at=utcnow())
    db.add(user); db.flush()
    student = Student(user_id=user.id, matric_no=matric_no, department=department, level=level)
    db.add(student); db.flush()
    db.add(FaceEmbedding(student_id=student.id, embedding=face_embedding, enrolled_at=utcnow()))
    return student


@app.post("/students", status_code=status.HTTP_201_CREATED)
def enroll_student(payload: StudentEnroll, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    if not payload.biometric_consent:
        raise HTTPException(422, "Explicit biometric consent is required before face enrolment.")
    student = create_student_account(
        db,
        name=payload.name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.temporary_password),
        matric_no=payload.matric_no,
        department=payload.department,
        level=payload.level,
        face_embedding=payload.face_embedding,
    )
    db.commit()
    return {"id": student.id, "name": payload.name, "matric_no": student.matric_no, "face_enrolled": True}


@app.post("/auth/register-student", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register_student(request: Request, payload: StudentRegisterRequest, db: Session = Depends(get_db)):
    if not payload.biometric_consent:
        raise HTTPException(422, "Explicit biometric consent is required before face enrolment.")
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
        face_embedding=payload.face_embedding,
        biometric_consent=payload.biometric_consent,
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
        face_embedding=pending.face_embedding,
    )
    pending.status = RegistrationStatus.approved
    pending.reviewed_at = utcnow()
    pending.reviewed_by = admin.id
    db.commit()
    return {"id": student.id, "name": pending.name, "matric_no": student.matric_no, "face_enrolled": True}


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
        .where(AttendanceSession.lecturer_id == lecturer.id, AttendanceSession.status == SessionStatus.open, AttendanceSession.ends_at > now)
        .order_by(AttendanceSession.started_at.desc())
    ).first()
    if not row:
        return None
    session, course = row
    return SessionOut(session_id=session.id, course_code=course.code, status=session.status.value, ends_at=session.ends_at)


@app.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: Session = Depends(get_db), lecturer: User = Depends(require_roles(UserRole.lecturer))):
    course = get_or_create_course(db, payload.course_code, payload.course_title, lecturer)
    now = utcnow()
    session = AttendanceSession(course_id=course.id, lecturer_id=lecturer.id, started_at=now, ends_at=now + timedelta(minutes=payload.duration_minutes), status=SessionStatus.open)
    db.add(session)
    if settings.demo_mode:
        demo_student_user = db.scalar(select(User).where(User.email == "student@smartattend.local"))
        demo_student = db.scalar(select(Student).where(Student.user_id == demo_student_user.id)) if demo_student_user else None
        if demo_student and not db.scalar(select(CourseEnrollment).where(CourseEnrollment.course_id == course.id, CourseEnrollment.student_id == demo_student.id)):
            db.add(CourseEnrollment(course_id=course.id, student_id=demo_student.id))
    db.commit()
    return SessionOut(session_id=session.id, course_code=course.code, status=session.status.value, ends_at=session.ends_at)


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
        .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
        .where(
            CourseEnrollment.student_id == student.id,
            AttendanceSession.status == SessionStatus.open,
            AttendanceSession.ends_at > now,
        )
        .order_by(AttendanceSession.ends_at)
    ).all()
    return [{"session_id": session.id, "course_code": course.code, "course_title": course.title, "ends_at": session.ends_at} for session, course in rows]


@app.post("/sessions/{session_id}/qr", response_model=QRTokenOut)
def rotate_qr(session_id: str, db: Session = Depends(get_db), lecturer: User = Depends(require_roles(UserRole.lecturer))):
    session = db.get(AttendanceSession, session_id)
    now = utcnow()
    if not session or session.lecturer_id != lecturer.id or session.status != SessionStatus.open or as_aware(session.ends_at) <= now:
        raise HTTPException(409, "Session is closed or expired.")
    expires_at = min(now + timedelta(seconds=settings.qr_ttl_seconds), as_aware(session.ends_at))
    raw = new_qr_token(session_id, expires_at)
    row = QRToken(session_id=session_id, token_hash=token_hash(raw), issued_at=now, expires_at=expires_at)
    db.add(row)
    db.commit()
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


@app.post("/attendance/checkin", response_model=CheckInOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def check_in(request: Request, payload: CheckIn, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.student))):
    now = utcnow()
    session = db.get(AttendanceSession, payload.session_id)
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    qr = db.scalar(select(QRToken).where(QRToken.token_hash == token_hash(payload.qr_token), QRToken.session_id == payload.session_id))
    if not session or session.status != SessionStatus.open or as_aware(session.ends_at) <= now:
        raise HTTPException(409, "Attendance session is not open.")
    if not student:
        raise HTTPException(404, "Student is not enrolled.")
    if not db.scalar(select(CourseEnrollment).where(CourseEnrollment.course_id == session.course_id, CourseEnrollment.student_id == student.id)):
        raise HTTPException(403, "You are not enrolled in the course for this attendance session.")
    qr_valid = bool(qr and signature_is_valid(payload.qr_token) and as_aware(qr.expires_at) >= now)
    if not qr_valid:
        raise HTTPException(422, "QR expired or invalid. Ask the lecturer to refresh it.")
    face_template = db.scalar(select(FaceEmbedding).where(FaceEmbedding.student_id == student.id))
    if not face_template:
        raise HTTPException(422, "No enrolled face template was found for this student.")
    try:
        response = httpx.post(
            f"{settings.face_service_url}/verify",
            json={"enrolled_embedding": face_template.embedding, "captured_embedding": payload.captured_embedding, "liveness_passed": payload.liveness_passed},
            timeout=5.0,
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

    record = AttendanceRecord(
        session_id=session.id,
        student_id=student.id,
        face_match_score=face_score,
        qr_token_id=qr.id,
        marked_at=now,
        status=AttendanceStatus.present,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Attendance has already been recorded for this session.")
    return CheckInOut(attendance_id=record.id, status=record.status.value, face_match_score=record.face_match_score, marked_at=record.marked_at, message="Face and QR verified. Attendance marked present.")
