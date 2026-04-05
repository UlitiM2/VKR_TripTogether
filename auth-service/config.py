from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "TripPlanner Auth Service"
    DEBUG: bool = True
    
    DATABASE_URL: str = "postgresql://postgres:postgres@postgres/tripplanner"
    
    SECRET_KEY: str = "" # тут ключ
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8000"
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    #class Config:
        #env_file = ".env"

settings = Settings()