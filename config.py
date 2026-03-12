from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional, Set

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    BOT_TOKEN: str
    WEBHOOK_BASE: Optional[str] = None
    MONGO_URI: str
    ENCRYPTION_KEY: str

    REQUIRED_CHANNEL_ID: int

    PROOF_CHANNEL_PUBLIC: int
    PROOF_CHANNEL_DATA: int

    ADMIN_IDS: str = ""

    REDIS_URL: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

    REPLIT_DEV_DOMAIN: Optional[str] = None

    @field_validator("WEBHOOK_BASE")
    @classmethod
    def _strip_slash(cls, v: str):
        if v is None:
            return v
        from urllib.parse import urlparse
        parsed = urlparse(v)
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    def admin_id_set(self) -> Set[int]:
        ids = set()
        for x in self.ADMIN_IDS.replace(" ", "").split(","):
            if not x:
                continue
            try:
                ids.add(int(x))
            except Exception:
                pass
        return ids

settings = Settings()
