"""Hazard tagger (docs/SAFETY.md): reads a step's one-line English summary against one rules table and gives the
step's hazard, raised but never lowered, or the hard stop it hits. Plain text in, so the import pipeline can call
it on card steps later."""

import re
from typing import get_args

from models.repair import GateId, Hazard, StopReason

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
        [(g, part) for g in ("गीज", "गिज") for part in ("खोल", "अंदर", "पैनल", "कवर", "ढक्कन", "टैंक", "एलिमेंट", "थर्मोस्टे")]
        + [("గీజర", part) for part in ("తెర", "లోపల", "ప్యానె", "కవర", "ట్యాంక", "ఎలిమెంట", "థర్మోస్టా")]
        + [
            (g, part)
            for g in ("கீச", "கீஸ", "கீஷ")
            for part in ("திற", "உள்ளே", "பேனல", "கவர", "டேங்க", "எலிமென்ட", "தெர்மோஸ்டா")
        ]
        + [
            (g, part)
            for g in ("গিজা", "গীজা")
            for part in ("খোল", "খুল", "ভিতর", "ভেতর", "প্যানেল", "কভার", "ট্যাংক", "এলিমেন্ট", "থার্মোস্ট")
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


# While a gate is open Ustaad may talk only about the gate (app/live_events.releasable). Repair talk is naming a
# mains part or a capacitor (the English HV and capacitor rows, plus these word prefixes in the other scripts and
# Hinglish), or opening a cover or panel.
SPEECH_PARTS: list[tuple[str, ...]] = [
    *[
        (p,)
        for p in (
            "पीसीबी", "बोर्ड", "टर्मिनल", "वायरिंग", "वायर", "कनेक्टर", "रिले", "फ्यूज", "कंप्रेसर", "कम्प्रेसर",
            "मोटर", "ट्रांसफ", "एलिमेंट", "थर्मोस्टे", "वोल्टेज", "कैपेसिटर", "कपैसिटर", "कैपसिटर",
            "పీసీబీ", "బోర్డ", "టెర్మినల", "వైరింగ", "వైర", "కనెక్టర", "రిలే", "ఫ్యూజ", "కంప్రెసర", "మోటార", "మోటర",
            "ట్రాన్స్ఫార్మ", "ఎలిమెంట", "థర్మోస్టా", "వోల్టేజ", "కెపాసిటర", "కపాసిటర",
            "பிசிபி", "போர்ட", "டெர்மினல", "வயரிங", "வயர", "கனெக்டர", "ரிலே", "ஃப்யூஸ", "கம்ப்ரசர", "மோட்டார",
            "டிரான்ஸ்ஃபார்ம", "எலிமென்ட", "தெர்மோஸ்டா", "வோல்டேஜ", "கெபாசிட்ட", "கேபாசிட்ட",
            "পিসিবি", "বোর্ড", "টার্মিনাল", "ওয়্যারিং", "ওয়্যার", "কানেক্টর", "রিলে", "ফিউজ", "কম্প্রেসার", "মোটর",
            "ট্রান্সফরম", "এলিমেন্ট", "থার্মোস্ট", "ভোল্টেজ", "ক্যাপাসিট",
        )
    ],
    ("कवर", "खोल"), ("ढक्कन", "खोल"), ("पैनल", "खोल"), ("cover", "khol"), ("cover", "open"), ("panel", "khol"),
    ("కవర", "తెర"), ("கவர", "திற"), ("কভার", "খোল"), ("কভার", "খুল"),
]
# A gate's own words are gate talk, not repair talk: "plug socket se nikalo" for the mains gate, the meter across
# the capacitor's terminals for the capacitor gate.
GATE_WORDS: dict[GateId, tuple[str, ...]] = {
    "G_MAINS_OFF": ("mcb", "isolator", "plug", "socket", "mains", "सॉकेट", "मेन्स", "सॉकिट"),
    "G_CAP_DISCHARGE": (
        "capacitor", "terminal", "multimeter", "meter", "voltage", "volt", "discharge", "कैपेसिटर", "कपैसिटर",
        "कैपसिटर", "टर्मिनल", "मल्टीमीटर", "मीटर", "वोल्टेज", "डिस्चार्ज", "కెపాసిటర", "కపాసిటర", "టెర్మినల",
        "వోల్టేజ", "கெபாசிட்ட", "கேபாசிட்ட", "டெர்மினல", "வோல்டேஜ", "ক্যাপাসিট", "টার্মিনাল", "ভোল্টেজ",
    ),
}
# Power on, said in the other scripts (the English is POWER_ON): switching on, keeping on, plugging in, voltage,
# live, or the electricity supply. Water supply is not power ("पानी की सप्लाई"), nor is switching the supply off.
SPEECH_POWER_ON = re.compile(
    r"(ऑन|चालू)\s*(कर|रख)|(पावर|पॉवर|स्विच)\s*ऑन|प्लग\s*(इन|लगा)|वोल्टेज|लाइव"
    r"|(पावर|पॉवर|बिजली|इलेक्ट्रिक)\s*(की\s*)?सप्लाई(?!\s*(\S+\s*){0,2}बंद)|बिजली\s*(आ|चालू)"
    r"|ఆన్\s*చే|వోల్టేజ|కరెంట్\s*సప్లై|ஆன்\s*(செய்|பண்ண)|வோல்டேஜ|கரண்ட்\s*சப்ளை"
    r"|(অন|চালু)\s*কর|ভোল্টেজ|(বিদ্যুৎ|কারেন্ট)\s*সাপ্লাই"
)
# Hands-on inspection while powered (the LED TV torch check, Oct 18): a torch, or repair talk.
TORCH = ("टॉर्च", "torch", "flashlight", "టార్చ", "டார்ச", "টর্চ")


def _has(spoken: list[str], groups: list[tuple[str, ...]]) -> bool:
    return any(all(any(w.startswith(p) for w in spoken) for p in group) for group in groups)


def without_gate_words(said: str, gate: GateId) -> str:
    """The caption without the gate's own words, which are gate talk however they sound."""
    return " ".join(w for w in SPEECH_SPLIT.split(said.lower()) if w and not any(w.startswith(g) for g in GATE_WORDS[gate]))


def repair_talk(said: str) -> bool:
    """Whether a caption names a mains part or a capacitor or opens a cover."""
    spoken = [w for w in SPEECH_SPLIT.split(said.lower()) if w]
    hazard, _ = tag(" ".join(spoken), "none")
    return hazard in ("HV", "capacitor") or _has(spoken, SPEECH_PARTS)


def speech_power_on(said: str) -> bool:
    return needs_power_on(said) or bool(SPEECH_POWER_ON.search(said))


def hands_on(said: str) -> bool:
    lower = said.lower()
    return any(t in lower for t in TORCH) or repair_talk(said)
