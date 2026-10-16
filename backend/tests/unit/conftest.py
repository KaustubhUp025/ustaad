"""Every test starts with a fresh /ws/live admission: its counts are process-wide state."""

import pytest

from app import admission


@pytest.fixture(autouse=True)
def fresh_admission(monkeypatch):
    monkeypatch.setattr(admission, "ADMISSION", admission.Admission())
