import secrets
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Gateway configuration — all secrets must come from environment variables."""

    server_host: str = "0.0.0.0"
    server_port: int = 8000
    debug: bool = False

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    token_expire_hours: int = 24

    rate_limit_user: int = 100
    rate_limit_agent: int = 50
    rate_limit_system: int = 1000

    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    redis_host: str = "localhost"
    redis_port: int = 6379
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    cors_allow_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    csp_directives: str = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.jwt_secret:
            self.jwt_secret = secrets.token_hex(32)

    class Config:
        env_file = ".env"


settings = Settings()
