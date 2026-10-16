"""identify_appliance as the Live agent calls it: Flash vision reads a photo from this job's folder, tools/identify.py
normalises the reading, and the phone gets the `identified` frame for its code readout."""

import asyncio
import logging
from typing import get_args

from google.adk.tools import FunctionTool
from google.genai import types

from agent.media_tools import VISION_TIMEOUT_S, MediaDesk, ReadPhoto
from models.repair import ApplianceType
from models.tools import IdentifyOut, NameplateRead
from models.ws import Identified
from tools.identify import identify

logger = logging.getLogger(__name__)

QUESTION = (
    "Read the appliance's nameplate (rating plate) or its error display in this photo. Copy only what is printed or "
    "shown; null for anything not legible, never a guess. brand as printed; model number exactly as printed; series "
    f"if printed; type: one of {', '.join(get_args(ApplianceType))}; error_code exactly as shown on the display "
    "(for example E6), null if no code is shown. confidence 0-1: how sure you are of these fields. observations: "
    "other legible facts that help a repair (capacity, refrigerant, voltage, damage, burn marks). Never say what a "
    "code means."
)
NOTHING = IdentifyOut(brand=None, model=None, series=None, type=None, error_code=None, confidence=0)


def identify_tools(desk: MediaDesk, read_photo: ReadPhoto) -> list[FunctionTool]:
    async def identify_appliance(media_uri: str) -> dict:
        """Reads the brand, model, appliance type and error code from a photo he sent of the nameplate or the error
        display: pass the `media_uri` request_media gave you. When `readable` is false, ask for a clearer photo
        instead of using the reading. This never says what a code means: look that up with search_fault_cards."""
        if not desk.owns(media_uri):
            return NOTHING.model_dump(mode="json")
        try:
            read = await asyncio.wait_for(read_photo(QUESTION, media_uri, NameplateRead), VISION_TIMEOUT_S)
        except Exception:  # quota, network or a hung call: nothing read, so he is asked for the photo again
            logger.exception("identify failed")
            return NOTHING.model_dump(mode="json")
        out = identify(read)
        await desk.show(Identified(brand=out.brand, model=out.model, error_code=out.error_code, confidence=out.confidence))
        return out.model_dump(mode="json")

    tool = FunctionTool(identify_appliance)
    tool.behavior = types.Behavior.BLOCKING
    return [tool]
