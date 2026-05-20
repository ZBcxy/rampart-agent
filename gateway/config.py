from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    网关配置
    """

    # 服务器配置
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    debug: bool = False

    # 认证配置
    jwt_secret: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    token_expire_hours: int = 24

    # 限流配置
    rate_limit_user: int = 100  # 每分钟请求数
    rate_limit_agent: int = 50  # 每分钟请求数
    rate_limit_system: int = 1000  # 每秒请求数

    # LLM配置
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # 数据库配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # CORS配置
    cors_allow_origins: List[str] = ["*"]
    allowed_origins: List[str] = ["*"]

    class Config:
        env_file = ".env"


settings = Settings()
