"""Sets required env vars to test-only dummy values before any app module
is imported, since libs/db.py, libs/auth/jwt.py, and apps/api/main.py all
read required env vars (no insecure defaults) at import time by design."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("SESSION_SECRET", "test-session-secret-not-for-production")
