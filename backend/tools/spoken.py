"""Does a caption say a stored repair step? Hindi speech is captioned in Devanagari while a card step may be stored in
Hinglish or English, so each word becomes a rough consonant skeleton ("देखो" and "dekho" are both "dk"). Telugu,
Tamil and Bengali speech is compared with steps in the same script, word for word. Keyword rules only, no model."""

import re

DEVANAGARI = {
    "क": "k",
    "ख": "kh",
    "ग": "g",
    "घ": "gh",
    "ङ": "n",
    "च": "ch",
    "छ": "chh",
    "ज": "j",
    "झ": "jh",
    "ञ": "n",
    "ट": "t",
    "ठ": "th",
    "ड": "d",
    "ढ": "dh",
    "ण": "n",
    "त": "t",
    "थ": "th",
    "द": "d",
    "ध": "dh",
    "न": "n",
    "प": "p",
    "फ": "ph",
    "ब": "b",
    "भ": "bh",
    "म": "m",
    "य": "y",
    "र": "r",
    "ल": "l",
    "ळ": "l",
    "व": "v",
    "श": "sh",
    "ष": "sh",
    "स": "s",
    "ह": "h",
    "ऋ": "ri",
    "ृ": "ri",
    "ं": "n",
    "क़": "q",
    "ख़": "kh",
    "ग़": "g",
    "ज़": "z",
    "ड़": "r",
    "ढ़": "rh",
    "फ़": "f",
    "य़": "y",
    **{chr(0x0966 + d): str(d) for d in range(10)},
}  # vowels, matras, virama and the other signs drop out: a skeleton has no vowels
NUKTA = {"क़": "क़", "ख़": "ख़", "ग़": "ग़", "ज़": "ज़", "ड़": "ड़", "ढ़": "ढ़", "फ़": "फ़", "य़": "य़"}
# A spelled-out abbreviation sounds like its letter names: "PCB" is said "पीसीबी".
LETTER_NAMES = dict(
    zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "a b s d e f j ec i j k l m n o p k r s t u v dbl ks v jd".split())  # noqa: SIM905
)
SPLIT = re.compile(r"[\s.,!?।॥;:'\"()\[\]\-–—/]+")
# A step is said when its words are: at least this many of them (or all, for a shorter step) and this share.
MIN_MATCHED = 3
MIN_SHARE = 0.6


def _skeleton(latin: str) -> str:
    s = latin.lower().replace("ch", "C").replace("sh", "s").replace("ph", "f")
    s = re.sub(r"c(?=[eiy])", "s", s).replace("c", "k").replace("C", "c")
    s = s.replace("h", "").replace("w", "v").replace("z", "j").replace("q", "k").replace("x", "ks")
    s = re.sub(r"[aeiouy]", "", s)
    return re.sub(r"(.)\1+", r"\1", s)


def _word(token: str) -> str:
    if re.fullmatch(r"[A-Z]{2,5}", token):
        return _skeleton("".join(LETTER_NAMES[c] for c in token))
    if re.search(r"[ऀ-ॿ]", token):
        for pair, letter in NUKTA.items():
            token = token.replace(pair, letter)
        return _skeleton("".join(DEVANAGARI.get(c, "a" if "ऀ" <= c <= "ॿ" else c) for c in token))
    if re.fullmatch(r"[A-Za-z0-9]+", token):
        return _skeleton(token)
    return token.lower()


# The little words every sentence has, in Hindi, Hinglish and English.
FILLER = {
    _word(w)
    for w in (  # noqa: SIM905
        "करें करो कर करना करते करके करनी सकते सकता सकती हैं है था थी नहीं हाँ अब फिर पहले यह वह इस उस इसे उसे आप हम मैं मेरे मुझे आपको उसकी उसके क्या कोई कुछ एक भी तो ही और या लिए साथ बाद जब तब कहीं जैसे वाला वाली होगा रहा रही "
        "karo kare karein kar karna karte sakte hai hain nahi ab phir pehle yeh woh aap hum mein kya koi kuch bhi toh aur ya liye the and or is are to of in on at it this that you your with for please now then"
    ).split()
}


def words(text: str) -> set[str]:
    """The text's words as skeletons, without the little words and without one-letter skeletons."""
    out = {_word(t) for t in SPLIT.split(text) if t}
    return {w for w in out if len(w) >= 2 and w not in FILLER}


def says(said: set[str], step: set[str]) -> bool:
    """Whether a caption's words (`words`) say a step's words."""
    if not step:
        return False
    matched = len(said & step)
    return matched >= min(MIN_MATCHED, len(step)) and matched >= MIN_SHARE * len(step)
