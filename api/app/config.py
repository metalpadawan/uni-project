from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_DEFAULT_JWT_SECRET = "development-jwt-secret-change-before-deploy"
DEV_DEFAULT_QR_SIGNING_SECRET = "development-only-change-me"


class Settings(BaseSettings):
    database_url: str = "sqlite:///./smart_attendance.db"
    qr_signing_secret: str = DEV_DEFAULT_QR_SIGNING_SECRET
    qr_ttl_seconds: int = 30
    face_distance_threshold: float = 1.128
    face_service_url: str = "http://127.0.0.1:8001"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    jwt_secret: str = DEV_DEFAULT_JWT_SECRET
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    demo_mode: bool = False
    timezone: str = "Africa/Lagos"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

if not settings.demo_mode and (
    settings.jwt_secret == DEV_DEFAULT_JWT_SECRET
    or settings.qr_signing_secret == DEV_DEFAULT_QR_SIGNING_SECRET
):
    raise RuntimeError(
        "JWT_SECRET and QR_SIGNING_SECRET are still set to their development "
        "defaults. Set both to real random values before running with "
        "DEMO_MODE=false — refusing to start with a forgeable secret outside "
        "of demo/dev mode."
    )
