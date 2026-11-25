import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./swifthub.db")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    MODEL_DIR: str = os.getenv(
        "MODEL_DIR",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml", "artifacts"),
    )
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "swifthub-jwt-secret-key-change-in-production-2026",
    )
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))


settings = Settings()
