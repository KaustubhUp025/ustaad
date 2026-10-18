"""request_media's rules (SPEC §6, BUILD-GUIDE T17): judge a checked photo, ask for a retake with a reason in the
worker's language, give up after MAX_RETAKES, and list the photo on the job. Pure: the vision call is the caller's.
A gate photo is not judged here: the gate check in tools/repair.py decides, and it has no retake limit."""

from models.repair import JobMedia, MediaKind, MediaReason, Observation, RepairJob
from models.tools import ManualPage, MediaCheck, RequestMediaIn, RequestMediaOut

MIN_MEDIA_CONFIDENCE = 0.6
MAX_RETAKES = 2

# Shown on the camera sheet (media_result.retake_reason), so they are in the worker's language.
RETAKE: dict[str, dict[str, str]] = {
    "hi": {
        "blurry": "फ़ोटो धुंधली है। थोड़ा पास से लो, फ़्लैश ऑन करो।",
        "dark": "फ़ोटो में अंधेरा है। फ़्लैश ऑन करके दोबारा लो।",
        "not_visible": "जो माँगा था वो फ़ोटो में नहीं दिख रहा। पूरा हिस्सा फ़्रेम में लेकर दोबारा लो।",
        "illegible": "पेज पढ़ा नहीं जा रहा। पूरा पेज सीधा, रोशनी में रखकर दोबारा फ़ोटो लो।",
    },
    "te": {
        "blurry": "ఫోటో మసకగా ఉంది. కొంచెం దగ్గరగా తీయండి, ఫ్లాష్ ఆన్ చేయండి.",
        "dark": "ఫోటో చీకటిగా ఉంది. ఫ్లాష్ ఆన్ చేసి మళ్ళీ తీయండి.",
        "not_visible": "నేను అడిగినది ఫోటోలో కనిపించడం లేదు. ఆ భాగం మొత్తం ఫ్రేమ్‌లో వచ్చేలా మళ్ళీ తీయండి.",
        "illegible": "పేజీ చదవలేకపోతున్నాను. పేజీ మొత్తం నేరుగా, వెలుతురులో ఉంచి మళ్ళీ ఫోటో తీయండి.",
    },
    "ta": {
        "blurry": "புகைப்படம் மங்கலாக உள்ளது. கொஞ்சம் அருகில் சென்று, ஃபிளாஷ் ஆன் செய்து எடுங்கள்.",
        "dark": "புகைப்படம் இருட்டாக உள்ளது. ஃபிளாஷ் ஆன் செய்து மீண்டும் எடுங்கள்.",
        "not_visible": "நான் கேட்ட பகுதி புகைப்படத்தில் தெரியவில்லை. அந்தப் பகுதி முழுவதும் தெரியும்படி மீண்டும் எடுங்கள்.",
        "illegible": "பக்கத்தைப் படிக்க முடியவில்லை. முழுப் பக்கத்தையும் நேராக, வெளிச்சத்தில் வைத்து மீண்டும் புகைப்படம் எடுங்கள்.",
    },
    "bn": {
        "blurry": "ছবিটা ঝাপসা। একটু কাছ থেকে, ফ্ল্যাশ অন করে তুলুন।",
        "dark": "ছবিটা খুব অন্ধকার। ফ্ল্যাশ অন করে আবার তুলুন।",
        "not_visible": "যেটা চেয়েছিলাম সেটা ছবিতে দেখা যাচ্ছে না। পুরো অংশটা ফ্রেমে রেখে আবার তুলুন।",
        "illegible": "পাতাটা পড়া যাচ্ছে না। পুরো পাতাটা সোজা করে, আলোয় রেখে আবার ছবি তুলুন।",
    },
    "en": {
        "blurry": "Photo is blurry. Move a little closer and turn the flash on.",
        "dark": "Photo is too dark. Turn the flash on and take it again.",
        "not_visible": "I can't see what I asked for. Get the whole part in the frame and take it again.",
        "illegible": "I can't read the page. Hold the whole page straight, in good light, and take it again.",
    },
}
# A failed gate photo, on the camera sheet. Same rule as docs/SAFETY.md "On fail"; the model gets the check's reason.
GATE_RETAKE: dict[str, dict[str, str]] = {
    "hi": {
        "G_MAINS_OFF": "MCB की OFF वाली स्थिति या निकला हुआ प्लग साफ़ नहीं दिखा। पास से, फ़्लैश ऑन करके फिर फ़ोटो लो।",
        "G_CAP_DISCHARGE": "कैपेसिटर डिस्चार्ज नहीं दिखा। इंसुलेटेड टूल से सुरक्षित डिस्चार्ज करो, फिर मीटर की रीडिंग की फ़ोटो लो।",
    },
    "te": {
        "G_MAINS_OFF": "MCB OFF స్థితి లేదా తీసిన ప్లగ్ స్పష్టంగా కనిపించలేదు. దగ్గరగా, ఫ్లాష్ ఆన్ చేసి మళ్ళీ ఫోటో తీయండి.",
        "G_CAP_DISCHARGE": "కెపాసిటర్ డిశ్చార్జ్ అయినట్లు కనిపించలేదు. ఇన్సులేటెడ్ టూల్‌తో సురక్షితంగా డిశ్చార్జ్ చేసి, మళ్ళీ కొలిచి మీటర్ ఫోటో తీయండి.",
    },
    "ta": {
        "G_MAINS_OFF": "MCB OFF நிலை அல்லது பிடுங்கிய பிளக் தெளிவாகத் தெரியவில்லை. அருகில் சென்று, ஃபிளாஷ் ஆன் செய்து மீண்டும் எடுங்கள்.",
        "G_CAP_DISCHARGE": "கெபாசிட்டர் டிஸ்சார்ஜ் ஆனதாகத் தெரியவில்லை. இன்சுலேட்டட் கருவியால் பாதுகாப்பாக டிஸ்சார்ஜ் செய்து, மீண்டும் அளந்து மீட்டரின் புகைப்படம் எடுங்கள்.",
    },
    "bn": {
        "G_MAINS_OFF": "MCB-র OFF অবস্থা বা খোলা প্লাগ স্পষ্ট দেখা যাচ্ছে না। কাছ থেকে, ফ্ল্যাশ অন করে আবার ছবি তুলুন।",
        "G_CAP_DISCHARGE": "ক্যাপাসিটর ডিসচার্জ হয়েছে বলে দেখা যাচ্ছে না। ইনসুলেটেড টুল দিয়ে নিরাপদে ডিসচার্জ করে আবার মেপে মিটারের ছবি তুলুন।",
    },
    "en": {
        "G_MAINS_OFF": "The MCB in the OFF position, or the pulled-out plug, isn't clearly visible. Take it again from closer with the flash on.",
        "G_CAP_DISCHARGE": "The capacitor isn't shown discharged. Discharge it safely with an insulated tool, measure again and photograph the meter.",
    },
}
# The photo could not be checked (quota, network, a hung call); the request stays open.
NOT_CHECKED: dict[str, str] = {
    "hi": "फ़ोटो चेक नहीं हो पाई। दोबारा भेजो।",
    "te": "ఫోటో చెక్ చేయలేకపోయాను. మళ్ళీ పంపండి.",
    "ta": "புகைப்படத்தைச் சரிபார்க்க முடியவில்லை. மீண்டும் அனுப்புங்கள்.",
    "bn": "ছবিটা যাচাই করা গেল না। আবার পাঠান।",
    "en": "Couldn't check the photo. Send it again.",
}
# For the model only.
GAVE_UP = "The photo is still unclear after the retakes. Do not ask for it again; ask him what he sees."
CANCELLED = "He did not send the photo. Do not ask again unless he offers; ask him what he sees."


# The photo of a manual page or wiring sticker (BUILD-GUIDE §9.3): copied, never recalled.
PAGE_QUESTION = (
    "A repair technician photographed a page of an appliance manual or a wiring-diagram sticker. Copy only what is "
    "printed, exactly; never add anything from memory. legible: false if you cannot read the page clearly, and then "
    "leave every other field empty or null. confidence: 0 to 1, how sure you are of your reading. brand, model and "
    "page_title as printed, else null. error_codes: each printed code with its printed meaning. steps: each printed "
    "repair or check instruction in order, with instruction as printed and summary_en one line of English saying "
    "the same. warnings: each printed caution or warning."
)


def question(inp: RequestMediaIn) -> str:
    if not inp.target:  # he sent it on his own, so there is nothing to match: judge only whether it is readable
        return (
            "A repair technician sent this photo of an appliance. matches_expected: true if it is clear enough to see "
            "what it shows. confidence: 0 to 1. problem: 'blurry', 'dark', 'not_visible' (nothing recognisable), or "
            "null. findings: what you can read or see that matters for repairing it, each {label, value, confidence}. "
            "Do not guess text you cannot read."
        )
    return (
        f"This photo should show: {inp.target}. matches_expected: true only if it clearly shows that. "
        "confidence: 0 to 1, how sure you are. problem: 'blurry', 'dark', 'not_visible' (missing or cut off), or "
        "null. findings: what you can read or see that matters for repairing it, each {label, value, confidence}. "
        "Do not guess text you cannot read."
    )


def judge(check: MediaCheck, uri: str, retakes: int, lang: str, own: bool = False) -> tuple[RequestMediaOut, bool]:
    """`retakes` is how many retakes he has already sent. Returns the answer and whether to ask for another.
    `own`: he sent it himself, so nothing was asked for; only a blurry or dark photo is retaken, and Ustaad asks
    about anything he does not recognise."""
    if own:
        good = check.problem not in ("blurry", "dark")
    else:
        # Flash can answer "matches" and still name a problem (blurred PCB sample, Oct 18): the problem wins.
        good = check.matches_expected and check.confidence >= MIN_MEDIA_CONFIDENCE and check.problem is None
    retake = not good and retakes < MAX_RETAKES
    if good:
        follow_up = None
    elif retake:
        follow_up = RETAKE[lang][check.problem or "blurry"]
    else:
        follow_up = GAVE_UP
    out = RequestMediaOut(
        media_uri=uri,
        findings=check.findings,
        matches_expected=good,
        confidence=check.confidence,
        follow_up=follow_up,
        retaking=retake,
    )
    return out, retake


def judge_page(page: ManualPage, uri: str, retakes: int, lang: str, brand: str | None) -> tuple[RequestMediaOut, bool]:
    """Like `judge`, for a manual page. `brand`: the identified appliance's, if any. A page of another brand is not
    used and not retaken: he may not have the right one, so Ustaad asks."""
    other_brand = bool(page.brand and brand) and page.brand.strip().casefold() != brand.strip().casefold()
    retake = not page.legible and retakes < MAX_RETAKES
    if other_brand:
        follow_up = (
            f"This page is for {page.brand}, but the appliance is {brand.strip()}. Do not use it; tell him it looks "
            "like another brand's page and ask for the right one."
        )
    elif retake:
        follow_up = RETAKE[lang]["illegible"]
    elif not page.legible:
        follow_up = GAVE_UP
    else:
        follow_up = None
    findings = [{"label": c.code, "value": c.meaning, "confidence": page.confidence} for c in page.error_codes]
    out = RequestMediaOut(
        media_uri=uri,
        findings=findings,
        matches_expected=page.legible and not other_brand,
        confidence=page.confidence,
        follow_up=follow_up,
        retaking=retake,
    )
    return out, retake


def record(
    job: RepairJob,
    request_id: str,
    kind: MediaKind,
    uri: str,
    findings: list[Observation],
    confidence: float,
    reason: MediaReason = "requested",
) -> RepairJob:
    entry = JobMedia(request_id=request_id, uri=uri, kind=kind, findings=findings, confidence=confidence, reason=reason)
    return job.model_copy(update={"media": [*job.media, entry]})
