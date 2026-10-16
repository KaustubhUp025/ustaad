"""Every test starts with a fresh /ws/live admission (its counts are process-wide state), and tokens are signed with
a test-only secret, set before any test module mints one at import."""

import os

import pytest

os.environ.setdefault("SESSION_SECRET", "test-only-secret")

from app import admission


@pytest.fixture(autouse=True)
def fresh_admission(monkeypatch):
    monkeypatch.setattr(admission, "ADMISSION", admission.Admission())
