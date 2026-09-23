"""应用配置：从 backend/.env 读取（pydantic-settings）。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = __file__.rsplit("app", 1)[0]  # backend/


class Settings(BaseSettings):
    # 当前生效的模型供应商：deepseek | siliconflow | zhipu
    llm_provider: str = "deepseek"

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-flash"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_temperature: float = 0.7

    siliconflow_api_key: str = ""
    siliconflow_model: str = "deepseek-ai/DeepSeek-V4-Flash"
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"

    zhipu_api_key: str = ""
    zhipu_model: str = "glm-4.5-flash"
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"

    zhipu_vision_model: str = "glm-4v-flash"  # 图片内容提取用的视觉模型

    embedding_model: str = "BAAI/bge-small-zh-v1.5"

    chroma_persist_dir: str = "./data/chroma"
    sqlite_path: str = "./data/ican.db"
    upload_dir: str = "./data/uploads"

    secret_key: str = ""                      # 可由 .env SECRET_KEY 提供
    secret_file: str = "./data/secret.key"    # 未提供时自动生成并持久化
    token_expire_days: int = 7

    max_upload_mb: int = 20
    max_pdf_pages: int = 300

    cors_origins: str = "http://localhost:5173"

    # Turso 云数据库（可选）：配置后 get_conn() 走云库，账号/会话/消息跨重启持久；
    # 留空则用本地 SQLite 文件（本地开发/测试）。环境变量 TURSO_DATABASE_URL / TURSO_AUTH_TOKEN
    turso_database_url: str = ""
    turso_auth_token: str = ""

    # BYOK 独占模式（线上部署开启）：用户必须自带 Key（X-LLM-* 请求头），
    # 全局 .env 的 Key 不再用于用户对话，未带 Key 一律走演示模式
    byok_only: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def has_api_key(self) -> bool:
        """任一供应商配置了 Key 即视为可用。"""
        return any(
            getattr(self, f"{p}_api_key").strip()
            for p in ("deepseek", "siliconflow", "zhipu")
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
