"""Tests for WP5: App factory wiring with/without Postgres."""

from __future__ import annotations

from municipal.chat.session import SessionManager
from municipal.core.config import Settings
from municipal.web.app import create_app


def test_create_app_without_db_url():
    """Without a DB URL, in-memory stores are used."""
    settings = Settings()
    app = create_app(settings=settings)
    assert isinstance(app.state.session_manager, SessionManager)


def test_create_app_with_db_url():
    """With a DB URL, Postgres repos are used."""
    from municipal.repositories.postgres.sessions import PostgresSessionRepository

    settings = Settings()
    settings.db.database_url = "postgresql+asyncpg://user:pass@localhost/test"
    app = create_app(settings=settings)
    assert isinstance(app.state.session_manager, PostgresSessionRepository)
    assert hasattr(app.state, "db_manager")


def test_cors_includes_frontend_ports():
    """CORS should include localhost:3000 and :3001 for Next.js apps."""
    app = create_app()
    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls.__name__ == "CORSMiddleware":
            cors_middleware = middleware
            break
    assert cors_middleware is not None
    origins = cors_middleware.kwargs.get("allow_origins", [])
    assert "http://localhost:3000" in origins
    assert "http://localhost:3001" in origins
