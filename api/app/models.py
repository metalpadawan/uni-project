import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def uid() -> str:
    return str(uuid.uuid4())


class EmbeddingType(TypeDecorator):
    """Use pgvector in PostgreSQL and JSON in the SQLite development fallback."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import VECTOR
            return dialect.type_descriptor(VECTOR(128))
        return dialect.type_descriptor(JSON())


class SessionStatus(str, enum.Enum):
    open = "open"
    closed = "closed"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    flagged = "flagged"


class UserRole(str, enum.Enum):
    admin = "admin"
    lecturer = "lecturer"
    student = "student"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    lecturer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("course_id", "student_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), unique=True)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingType())
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sample_photo_url: Mapped[str | None] = mapped_column(String, nullable=True)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    matric_no: Mapped[str] = mapped_column(String(40), unique=True)
    department: Mapped[str] = mapped_column(String(160))
    level: Mapped[int]


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"))
    lecturer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.open)


class QRToken(Base):
    __tablename__ = "qr_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey("attendance_sessions.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey("attendance_sessions.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    face_match_score: Mapped[float] = mapped_column(Float)
    qr_token_id: Mapped[str] = mapped_column(ForeignKey("qr_tokens.id"))
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus))


class AttendanceAttempt(Base):
    """Audits a failed double-lock check without blocking a later valid retry."""

    __tablename__ = "attendance_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey("attendance_sessions.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    face_match_score: Mapped[float] = mapped_column(Float)
    qr_token_id: Mapped[str] = mapped_column(ForeignKey("qr_tokens.id"))
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus), default=AttendanceStatus.flagged
    )
