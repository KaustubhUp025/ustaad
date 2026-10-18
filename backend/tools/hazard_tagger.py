"""Hazard tagger (docs/SAFETY.md): reads a step's one-line English summary against one rules table and gives the
step's hazard, raised but never lowered, or the hard stop it hits. Plain text in, so the import pipeline can call
it on card steps later."""

import re
from typing import get_args

from models.repair import Hazard, StopReason

# One row per outcome: a stop reason or a hazard level, and the keyword groups that match it. A group matches when
# all its words are in the summary. Stop rows come first: a stop wins over any hazard level.
RULES: list[tuple[StopReason | Hazard, list[set[str]]]] = [
    (
        "refrigerant",
        [{"refrigerant"}, {"gas"}, {"recharge"}, {"recharging"}, {"brazing"}, {"braze"}, {"nitrogen"}, {"manifold"}],
    ),
    (
        "microwave_hv",
        [
            {"magnetron"},
            {"microwave", "capacitor"},
            {"microwave", "transformer"},
            {"microwave", "diode"},
            {"microwave", "cover"},
            {"microwave", "cabinet"},
            {"microwave", "inside"},
        ],
    ),
    ("crt", [{"crt"}, {"picture", "tube"}, {"flyback"}, {"cathode"}, {"anode"}]),
    (
        "geyser_open",
        [{"geyser", word} for word in ("open", "inside", "cover", "panel", "lid", "tank", "element", "thermostat")],
    ),
    ("capacitor", [{"capacitor"}]),
    (
        "HV",
        [
            {word}
            for word in (
                "pcb", "board", "terminal", "wiring", "wire", "mains", "live", "socket", "connector", "relay",
                "fuse", "compressor", "motor", "transformer", "element", "thermostat", "voltage",
            )
        ],
    ),
]
LEVELS: list[Hazard] = ["none", "HV", "capacitor"]
# General steps never need the power on (SAFETY.md). Kept out of RULES: card and manual steps may need it, and the
# speech backstop must not stop the power-on diagnosis that happens in conversation before start_repair. Phrases, not
# single words: "water supply", a continuity tester and "with the power off" are power-off steps.
POWER_ON = re.compile(
    r"\bvolt(age)?s?\b|\blive\b|\benergi[sz]ed\b"
    r"|\b(power|mains|electric|electrical|electricity)\s+supply\b|\bsupply\s+volt"
    r"|\bsupply\b.*\b(socket|mcb)\b|\b(socket|mcb)\b.*\bsupply\b"
    r"|\b(line|voltage|neon)\s+tester\b"
    r"|\b(power|powered|switch|switched|turn|turned)\s+(\w+\s+){0,2}?on\b|\bplug(ged)?\s+(it\s+)?in\b"
)


def _words(text: str) -> set[str]:
    # Plurals count as the singular ("terminals" matches "terminal"); short words like "gas" are left alone.
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", text.lower())}


def tag(summary_en: str, hazard: Hazard) -> tuple[Hazard, StopReason | None]:
    """The step's hazard after tagging and the stop reason it hits, if any. A `refrigerant` hazard is a stop."""
    if hazard == "refrigerant":
        return hazard, "refrigerant"
    words = _words(summary_en)
    matched = [outcome for outcome, groups in RULES if any(group <= words for group in groups)]
    stop = next((m for m in matched if m in get_args(StopReason)), None)
    if stop:
        return hazard, stop
    return max([hazard, *matched], key=LEVELS.index), None


def needs_power_on(summary_en: str) -> bool:
    return bool(POWER_ON.search(summary_en.lower()))


# Speech (the backstop in app/live_events.py) is captioned in the worker's script, so each stop row also has word
# prefixes in Devanagari, Telugu, Tamil and Bengali. A group matches when every prefix starts some word ("खोल" for
# खोलकर, खोलें). Gas and the microwave need an action word: naming them is ordinary diagnosis talk ("गैस कम हो सकती
# है"), opening, filling or touching the parts is the stop.
SPEECH_RULES: list[tuple[StopReason, list[tuple[str, ...]]]] = [
    (
        "refrigerant",
        [
            ("रेफ्रिजरेंट",),
            ("ब्रेज",),
            ("नाइट्रोजन",),
            ("मैनिफोल्ड",),
            ("రిఫ్రిజిరెంట",),
            ("నైట్రోజన",),
            ("బ్రేజ",),
            ("நைட்ரஜன",),
            ("பிரேசி",),
            ("রেফ্রিজারেন্ট",),
            ("নাইট্রোজেন",),
            ("ব্রেজ",),
        ]
        + [(gas, act) for gas in ("गैस", "गेस") for act in ("भर", "डाल", "चार्ज", "रिचार्ज", "रीचार्ज")]
        + [("గ్యాస", act) for act in ("నింప", "ఫిల్", "చార్జ", "రీఛార్జ", "రీచార్జ")]
        + [(gas, act) for gas in ("கேஸ", "காஸ") for act in ("நிரப்ப", "ஃபில்", "சார்ஜ", "ரீசார்ஜ")]
        + [("গ্যাস", act) for act in ("ভর", "ভরা", "ফিল", "চার্জ", "রিচার্জ")],
    ),
    (
        "microwave_hv",
        [("मैग्नेट्र",), ("మ్యాగ్నెట్ర",), ("மேக்னட்ர",), ("மேக்னெட்ர",), ("ম্যাগনেট্র",)]
        + [("माइक्रोवेव", part) for part in ("कैपे", "कपै", "ट्रांसफ", "डायोड")]
        + [("माइक्रोवेव", cover, "खोल") for cover in ("कवर", "कैबिनेट", "बॉडी", "ढक्कन")]
        + [("మైక్రోవేవ", part) for part in ("కెపాసిట", "కపాసిట", "ట్రాన్స్ఫార్మ", "డయోడ")]
        + [("మైక్రోవేవ", "కవర", "తెర")]
        + [("மைக்ரோவேவ", part) for part in ("கெபாசிட்ட", "கேபாசிட்ட", "டிரான்ஸ்ஃபார்ம", "டையோட")]
        + [("மைக்ரோவேவ", "கவர", "திற")]
        + [("মাইক্রোওয়েভ", part) for part in ("ক্যাপাসিট", "ট্রান্সফরম", "ডায়োড")]
        + [("মাইক্রোওয়েভ", "কভার", op) for op in ("খোল", "খুল")],
    ),
    (
        "crt",
        [
            ("पिक्चर", "ट्यूब"),
            ("सीआरटी",),
            ("फ्लाईबैक",),
            ("फ्लायबैक",),
            ("పిక్చర", "ట్యూబ"),
            ("సీఆర్టీ",),
            ("பிக்சர", "டியூப"),
            ("சிஆர்டி",),
            ("পিকচার", "টিউব"),
            ("সিআরটি",),
        ],
    ),
    (
        "geyser_open",
        [(g, part) for g in ("गीज", "गिज") for part in ("खोल", "पैनल", "कवर", "ढक्कन", "टैंक", "एलिमेंट", "थर्मोस्टे")]
        + [("గీజర", part) for part in ("తెర", "ప్యానె", "కవర", "ట్యాంక", "ఎలిమెంట", "థర్మోస్టా")]
        + [
            (g, part)
            for g in ("கீச", "கீஸ", "கீஷ")
            for part in ("திற", "பேனல", "கவர", "டேங்க", "எலிமென்ட", "தெர்மோஸ்டா")
        ]
        + [
            (g, part)
            for g in ("গিজা", "গীজা")
            for part in ("খোল", "খুল", "প্যানেল", "কভার", "ট্যাংক", "এলিমেন্ট", "থার্মোস্ট")
        ],
    ),
]
SPEECH_SPLIT = re.compile(r"[\s.,!?।॥;:'\"()\[\]\-–—/]+")


def speech_stop(said: str) -> StopReason | None:
    """The stop a caption hits, in any of the five languages: the English rules first, then the script prefixes."""
    _, stop = tag(said, "none")
    if stop:
        return stop
    spoken = [w for w in SPEECH_SPLIT.split(said) if w]
    for reason, groups in SPEECH_RULES:
        if any(all(any(w.startswith(p) for w in spoken) for p in group) for group in groups):
            return reason
    return None
