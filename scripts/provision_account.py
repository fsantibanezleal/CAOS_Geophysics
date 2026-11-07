"""Provision internal accounts without email delivery or command-line passwords."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
from pathlib import Path
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.accounts import AccountProvisionError, provision_account  # noqa: E402
from app.config import WorkerSettings  # noqa: E402
from app.database import make_engine, require_migration_head  # noqa: E402


class SecretSafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, "Invalid command options; use a private --credentials file or the non-echoing prompt\n")


def credential_input(path: Path | None) -> tuple[str, str]:
    if path is None:
        return input("Account identifier: ").strip(), getpass.getpass("Password (not echoed): ")
    if not path.is_file() or path.stat().st_size > 65536:
        raise AccountProvisionError("Credential input must be an existing private JSON file below 64 KiB")

    def unique_pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise AccountProvisionError("Credential file contains duplicate fields")
            value[key] = item
        return value

    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_pairs)
        if not isinstance(value, dict) or not isinstance(value.get("username"), str) or not isinstance(value.get("password"), str):
            raise ValueError
        return value["username"], value["password"]
    except (ValueError, UnicodeError):
        raise AccountProvisionError("Credential JSON must contain string username and password fields") from None


async def run(settings: WorkerSettings, username: str, password: str, rotate_password: bool) -> dict[str, str]:
    if not settings.database_path.is_file():
        raise AccountProvisionError("Database must already exist and be migrated; no database was created")
    engine = make_engine(settings)
    try:
        await require_migration_head(engine)
        return await provision_account(async_sessionmaker(engine, expire_on_commit=False), username, password,
                                       rotate_password=rotate_password)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = SecretSafeParser(description=__doc__)
    parser.add_argument("--credentials", type=Path, help="Private operator JSON file, never a product asset")
    parser.add_argument("--rotate-password", action="store_true", help="Explicitly rotate and revoke this account's sessions")
    args = parser.parse_args(argv)
    try:
        username, password = credential_input(args.credentials)
        result = asyncio.run(run(WorkerSettings.from_env(), username, password, args.rotate_password))
    except AccountProvisionError as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception:
        # Library/database diagnostics can include parameter values. Never echo
        # their repr, stack trace, input file content or a password/hash.
        print("Account operation failed; check the migrated database and operator permissions", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
