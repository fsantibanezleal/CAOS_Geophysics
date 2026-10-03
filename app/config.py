"""Runtime configuration. Secrets enter through environment only."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


MIB = 1024 * 1024


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    auth_secret: str
    public_origin: str
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    db_path: Path | None = None
    cookie_secure: bool = True
    max_upload_bytes: int = 200 * MIB
    account_quota_bytes: int = 1024 * MIB
    max_dataset_bytes: int = 2 * MIB
    max_dataset_rows: int = 4096
    max_queued_jobs: int = 32
    worker_memory_bytes: int = 2 * 1024 * MIB
    worker_scratch_bytes: int = 1024 * MIB
    worker_wall_seconds: int = 600
    mt_online_enabled: bool = False  # Set only after the actual ML VPS admission receipt.

    def __post_init__(self) -> None:
        if len(self.auth_secret) < 32:
            raise ValueError("GEOPHYSICS_AUTH_SECRET must be at least 32 characters")
        parsed = urlsplit(self.public_origin)
        if (
            parsed.scheme not in ("http", "https") or not parsed.netloc
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or parsed.username or parsed.password
        ):
            raise ValueError("public_origin must be an origin without a path")
        if self.cookie_secure and parsed.scheme != "https":
            raise ValueError("secure cookie requires an HTTPS public origin")
        if self.max_upload_bytes <= 0 or self.account_quota_bytes < self.max_upload_bytes:
            raise ValueError("invalid upload or account quota")
        if (self.max_dataset_bytes <= 0 or self.max_dataset_rows < 4 or self.max_queued_jobs < 1
                or self.worker_memory_bytes <= 0 or self.worker_scratch_bytes <= 0
                or self.worker_wall_seconds <= 0):
            raise ValueError("invalid processing limits")
        if not self.data_dir.is_absolute():
            raise ValueError("data_dir must be absolute")
        if self.db_path is not None and not self.db_path.is_absolute():
            raise ValueError("db_path must be absolute")

    @property
    def database_path(self) -> Path:
        return self.db_path or self.data_dir / "api.sqlite3"

    @property
    def database_url(self) -> str:
        return "sqlite+aiosqlite:///" + self.database_path.as_posix()

    @classmethod
    def from_env(cls) -> "Settings":
        data = Path(os.environ.get("GEOPHYSICS_DATA_DIR", "data/raw/api")).resolve()
        db = os.environ.get("GEOPHYSICS_DB_PATH")
        return cls(
            data_dir=data,
            db_path=Path(db).resolve() if db else None,
            auth_secret=os.environ["GEOPHYSICS_AUTH_SECRET"],
            public_origin=os.environ["GEOPHYSICS_PUBLIC_ORIGIN"].rstrip("/"),
            smtp_host=os.environ["GEOPHYSICS_SMTP_HOST"],
            smtp_port=int(os.environ.get("GEOPHYSICS_SMTP_PORT", "587")),
            smtp_username=os.environ["GEOPHYSICS_SMTP_USERNAME"],
            smtp_password=os.environ["GEOPHYSICS_SMTP_PASSWORD"],
            smtp_from=os.environ["GEOPHYSICS_SMTP_FROM"],
            mt_online_enabled=os.environ.get("GEOPHYSICS_MT_ONLINE_ENABLED") == "1",
        )


@dataclass(frozen=True)
class WorkerSettings:
    """Storage-only worker configuration; no auth or SMTP secret is required."""

    data_dir: Path
    db_path: Path | None = None
    mt_online_enabled: bool = False

    def __post_init__(self) -> None:
        if not self.data_dir.is_absolute() or (self.db_path is not None and not self.db_path.is_absolute()):
            raise ValueError("worker data and database paths must be absolute")

    @property
    def database_path(self) -> Path:
        return self.db_path or self.data_dir / "api.sqlite3"

    @property
    def database_url(self) -> str:
        return "sqlite+aiosqlite:///" + self.database_path.as_posix()

    @classmethod
    def from_env(cls) -> "WorkerSettings":
        data = Path(os.environ.get("GEOPHYSICS_DATA_DIR", "data/raw/api")).resolve()
        db = os.environ.get("GEOPHYSICS_DB_PATH")
        return cls(data_dir=data, db_path=Path(db).resolve() if db else None,
                   mt_online_enabled=os.environ.get("GEOPHYSICS_MT_ONLINE_ENABLED") == "1")
