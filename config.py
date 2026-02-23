from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional, Set

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    BOT_TOKEN: str
    WEBHOOK_BASE: str  # https://your-domain
    MONGO_URI: str
    ENCRYPTION_KEY: str

    REQUIRED_CHANNEL_ID: int

    PROOF_CHANNEL_PUBLIC: int
    PROOF_CHANNEL_DATA: int

    ADMIN_IDS: str = ""

    REDIS_URL: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    @field_validator("WEBHOOK_BASE")
    @classmethod
    def _strip_slash(cls, v: str):
        return v.rstrip("/")

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
