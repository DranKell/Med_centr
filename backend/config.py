from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    GIGACHAT_CLIENT_ID: str = ''
    GIGACHAT_CLIENT_SECRET: str = ''
    GIGACHAT_SCOPE: str = 'GIGACHAT_API_PERS'
    YANDEX_IAM_TOKEN: str = ''
    YANDEX_FOLDER_ID: str = ''
    YANDEX_MODEL_URI: str = ''
    EXTERNAL_AI_ENABLED: bool = False
    SSL_CERT_FILE: str | None = None
    DATABASE_URL: str = 'sqlite:///./dental.db'
    CORS_ORIGINS: List[str] = ['http://localhost:3000', 'http://127.0.0.1:3000']

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8-sig'
        case_sensitive = True
        extra = 'ignore'

settings = Settings()
