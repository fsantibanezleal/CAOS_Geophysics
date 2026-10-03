"""FastAPI Users integration. Passwords and sessions are library managed."""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from typing import Awaitable, Callable
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, CookieTransport
from fastapi_users.authentication.strategy.db import DatabaseStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.exceptions import InvalidPasswordException
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import AccessToken, User
from app.schemas import UserCreate, UserRead


MailSender = Callable[[str, str, str], Awaitable[None]]


def smtp_sender(settings: Settings) -> MailSender:
    if not all((settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_from)):
        raise RuntimeError("SMTP configuration is required for account verification and reset")

    async def send(email: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = email
        message["Subject"] = subject
        message.set_content(body)

        def deliver() -> None:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
                client.starttls(context=ssl.create_default_context())
                client.login(settings.smtp_username, settings.smtp_password)
                client.send_message(message)

        await asyncio.to_thread(deliver)

    return send


def install_auth(app: FastAPI, settings: Settings, sender: MailSender | None = None):
    mail = sender or smtp_sender(settings)

    async def get_session(request: Request):
        async with request.app.state.sessions() as session:
            yield session

    async def get_user_db(session: AsyncSession = Depends(get_session)):
        yield SQLAlchemyUserDatabase(session, User)

    class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
        reset_password_token_secret = settings.auth_secret
        verification_token_secret = settings.auth_secret

        async def validate_password(self, password: str, user: UserCreate | User) -> None:
            if len(password) < 12:
                raise InvalidPasswordException(reason="Password must contain at least 12 characters")
            if user.email.lower() in password.lower():
                raise InvalidPasswordException(reason="Password must not contain the account email")

        async def on_after_register(self, user: User, request: Request | None = None) -> None:
            await self.request_verify(user, request)

        async def on_after_request_verify(self, user: User, token: str, request: Request | None = None) -> None:
            await mail(
                user.email,
                "Verify your geophysics account",
                f"Verification token: {token}\nSubmit it to POST /api/auth/verify/verify.\n",
            )

        async def on_after_forgot_password(self, user: User, token: str, request: Request | None = None) -> None:
            await mail(
                user.email,
                "Reset your geophysics password",
                f"Password reset token: {token}\nSubmit it with a new password to POST /api/auth/reset-password/reset-password.\n",
            )

        async def on_after_reset_password(self, user: User, request: Request | None = None) -> None:
            async with app.state.sessions() as session:
                await session.execute(delete(AccessToken).where(AccessToken.user_id == user.id))
                await session.commit()

    async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
        yield UserManager(user_db)

    async def get_access_token_db(session: AsyncSession = Depends(get_session)):
        yield SQLAlchemyAccessTokenDatabase(session, AccessToken)

    async def get_strategy(access_token_db: SQLAlchemyAccessTokenDatabase = Depends(get_access_token_db)):
        return DatabaseStrategy(access_token_db, lifetime_seconds=12 * 60 * 60)

    transport = CookieTransport(
        cookie_name="__Host-geophysics_session" if settings.cookie_secure else "geophysics_session",
        cookie_max_age=12 * 60 * 60,
        cookie_secure=settings.cookie_secure,
        cookie_httponly=True,
        cookie_samesite="strict",
        cookie_path="/",
    )
    backend = AuthenticationBackend(name="cookie", transport=transport, get_strategy=get_strategy)
    users = FastAPIUsers[User, UUID](get_user_manager, [backend])
    app.include_router(users.get_auth_router(backend, requires_verification=True), prefix="/api/auth/cookie")
    app.include_router(users.get_register_router(UserRead, UserCreate), prefix="/api/auth")
    app.include_router(users.get_verify_router(UserRead), prefix="/api/auth/verify")
    app.include_router(users.get_reset_password_router(), prefix="/api/auth/reset-password")

    current_user = users.current_user(active=True, verified=True)

    @app.get("/api/auth/me", response_model=UserRead)
    async def me(user: User = Depends(current_user)):
        return user

    return current_user, get_session
