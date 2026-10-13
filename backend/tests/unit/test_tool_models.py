import pytest
from pydantic import ValidationError

from models.tools import IdentifyOut, RequestMediaIn, RequestMediaOut


def obs(label, confidence):
    return {"label": label, "value": "x", "confidence": confidence}


def test_identify_out_allows_unread_fields_and_no_observations():
    out = IdentifyOut(brand="Voltas", model=None, series=None, type=None, error_code="E6", confidence=0.9)
    assert out.model is None
    assert out.observations == []


def test_weak_observations_are_dropped():
    out = IdentifyOut(
        brand=None, model=None, series=None, type=None, error_code=None, confidence=0.2,
        observations=[obs("serial_no", 0.9), obs("guess", 0.59), obs("refrigerant", 0.6)],
    )
    assert [o.label for o in out.observations] == ["serial_no", "refrigerant"]


def test_only_the_six_surest_observations_are_kept():
    many = [obs(f"o{i}", 0.6 + i / 100) for i in range(10)]
    out = RequestMediaOut(
        media_uri="gs://b/j_1/r_1.jpg", findings=many, matches_expected=True, confidence=0.9, follow_up=None
    )
    assert [o.label for o in out.findings] == ["o9", "o8", "o7", "o6", "o5", "o4"]


def test_request_media_kind_is_limited_to_the_contract():
    with pytest.raises(ValidationError):
        RequestMediaIn(kind="audio", target="Outdoor PCB", reason="code E6", framing_tip="Flash on")
