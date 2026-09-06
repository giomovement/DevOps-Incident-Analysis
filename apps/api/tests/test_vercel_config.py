from pathlib import Path

import pytest

from app.config import Settings


def test_vercel_uses_temporary_storage_and_secure_cookies(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    settings = Settings(_env_file=None, database_url="postgresql://example.invalid/app")

    assert settings.storage_path == Path("/tmp/dias/uploads")
    assert settings.session_cookie_secure is True


def test_vercel_requires_postgres(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    settings = Settings(_env_file=None, database_url=None)

    with pytest.raises(RuntimeError, match="DIAS_DATABASE_URL is required"):
        settings.ensure_directories()
