import json
from pathlib import Path
from typing import get_args

from models.repair import StopReason

I18N = Path(__file__).parents[3] / "web" / "src" / "i18n"


def test_every_stop_reason_has_its_own_text_in_all_five_languages():
    for lang in ("en", "hi", "te", "ta", "bn"):
        stop = json.loads((I18N / f"{lang}.json").read_text())["repair"]["stop"]
        for reason in get_args(StopReason):
            assert stop.get(reason), f"{lang}: repair.stop.{reason}"
