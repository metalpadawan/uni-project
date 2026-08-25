from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./smart_attendance.db"
    qr_signing_secret: str = "development-only-change-me"
    qr_ttl_seconds: int = 30
    face_distance_threshold: float = 0.6
    face_service_url: str = "http://127.0.0.1:8001"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    jwt_secret: str = "development-jwt-secret-change-before-deploy"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    demo_mode: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
