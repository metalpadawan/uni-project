from datetime import datetime
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    course_code: str = "CSC 421"
    course_title: str = "Artificial Intelligence"
    duration_minutes: int = Field(120, ge=5, le=360)


class SessionOut(BaseModel):
    session_id: str
    course_code: str
    status: str
    ends_at: datetime


class QRTokenOut(BaseModel):
    token: str
    qr_data_url: str
    expires_at: datetime
    expires_in: int


class CheckIn(BaseModel):
    session_id: str
    qr_token: str
    captured_embedding: list[float] = Field(min_length=128, max_length=128)
    liveness_passed: bool


class StudentEnroll(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: str
    temporary_password: str = Field(min_length=8, max_length=128)
    matric_no: str = Field(min_length=5, max_length=40)
    department: str = Field(default="Computer Science", min_length=2, max_length=160)
    level: int = Field(default=400, ge=100, le=900)
    face_embedding: list[float] = Field(min_length=128, max_length=128)
    biometric_consent: bool


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(LoginRequest):
    name: str = Field(min_length=2, max_length=160)
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class CheckInOut(BaseModel):
    attendance_id: str
    status: str
    face_match_score: float
    marked_at: datetime
    message: str
