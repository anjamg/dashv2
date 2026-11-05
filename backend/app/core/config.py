from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://user:password@localhost:3306/vita?charset=utf8mb4"
    SECRET_KEY: str = "change-me-super-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60*8
    class Config:
        env_file = ".env"

settings = Settings()
