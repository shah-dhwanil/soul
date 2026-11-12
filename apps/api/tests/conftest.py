import os

# Tests run against a fixed secret so tokens minted in one module decode in
# another. Set before any test module imports `api.config`.
os.environ["JWT_SECRET"] = "test-secret-for-jwt-signing-0123456789abcdef"

import pytest  # noqa: E402

from api.config import get_auth_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_auth_settings():
    """Drop the cached settings so env changes take effect per test."""
    get_auth_settings.cache_clear()
    yield
    get_auth_settings.cache_clear()
