import pytest


@pytest.fixture(autouse=True)
def keep_automated_tests_off_hosted_databases(monkeypatch):
    """A developer's .env may point at Neon; tests must remain local and disposable."""
    monkeypatch.setenv("DIAS_DATABASE_URL", "")
