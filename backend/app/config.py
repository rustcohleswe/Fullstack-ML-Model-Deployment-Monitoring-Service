"""Environment-driven configuration."""
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    supabase_url: str = ""
    supabase_key: str = ""  # use the *service role* key (server side only)
    cors_origins: tuple = field(default_factory=lambda: ("http://localhost:3000",))

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        return cls(
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_key=os.getenv("SUPABASE_KEY", ""),
            cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        )

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)
