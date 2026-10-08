"""Operator-only local account provisioning, using the installed auth library.

There is no public signup endpoint here. Passwords are never returned; the
existing account/project schema and library session strategy remain unchanged.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.password import PasswordHelper
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import AccessToken, User
from app.schemas import UserCreate


class AccountProvisionError(ValueError):
    """A redacted, operator-actionable provisioning refusal."""


async def provision_account(
    sessions: async_sessionmaker[AsyncSession], username: str, password: str, *, rotate_password: bool = False,
) -> dict[str, str]:
    """Create or explicitly rotate one account; never overwrite by default.

    Rotation and session revocation share one SQLite write transaction. A
    database uniqueness race cannot turn account creation into an update.
    Mailbox verification is intentionally not asserted for local accounts.
    """
    try:
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValueError
        declared = UserCreate(email=username, password=password)
    except ValueError:
        raise AccountProvisionError("Account identifier or password input is invalid") from None
    if len(password) < 8 or len(password) > 1024 or declared.email.lower() in password.lower():
        raise AccountProvisionError("Local password must be 8 to 1024 characters and exclude the account identifier")

    async with sessions() as session:
        await session.execute(text("BEGIN IMMEDIATE"))
        user_db = SQLAlchemyUserDatabase(session, User)
        user = await user_db.get_by_email(declared.email)
        if user is not None and not user.is_active:
            raise AccountProvisionError("Account is inactive; review it rather than implicitly activating it")
        if user is not None and not rotate_password:
            raise AccountProvisionError("Account already exists; explicit password rotation is required to change it")
        if user is None and rotate_password:
            raise AccountProvisionError("Account does not exist; provision it before requesting rotation")
        hashed = await asyncio.to_thread(PasswordHelper().hash, password)
        if user is None:
            user = User(id=uuid4(), email=declared.email, hashed_password=hashed,
                        is_active=True, is_superuser=False, is_verified=False)
            session.add(user)
            verdict = "created"
        else:
            user.hashed_password = hashed
            await session.execute(delete(AccessToken).where(AccessToken.user_id == user.id))
            verdict = "rotated"
        account_id = str(user.id)
        await session.commit()
    return {"verdict": verdict, "account_id": account_id}
