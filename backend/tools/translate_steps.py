"""Step-card translation (te/ta/bn): the prompt for one Flash call over all of a job's steps, and the rule for storing
its answer. Display-only: a stored translation never changes a step's hazard, gates, order or source."""

from models.repair import RepairJob

# Languages whose step card gets a translation; English shows instruction_en and Hindi the original words.
TRANSLATED_LANGS = {"te", "ta", "bn"}


def sources(job: RepairJob) -> list[str]:
    """What is translated: each step's English, or its original words when it has none."""
    return [s.instruction_en or s.instruction for s in job.steps]


def prompt(lines: list[str], language_name: str) -> str:
    numbered = "\n".join(f"{n}. {line}" for n, line in enumerate(lines, 1))
    return (
        f"Translate each numbered repair step into {language_name}, for an AC and appliance technician.\n"
        "Keep part names, error codes, numbers and units as they are. Do not add, drop, merge or reorder steps and do "
        f"not add advice. Return exactly {len(lines)} lines in `lines`, in the same order, without the numbers.\n"
        f"{numbered}"
    )


def apply(job: RepairJob, lang: str, asked: list[str], lines: list[str]) -> RepairJob:
    """`asked` is what was sent for translation. Stored only when it is still the job's plan and every step got one
    non-blank line; otherwise the job is unchanged and the card shows the original."""
    clean = [line.strip() for line in lines]
    if asked != sources(job) or len(clean) != len(job.steps) or not all(clean):
        return job
    steps = [s.model_copy(update={"instruction_translated": t}) for s, t in zip(job.steps, clean, strict=True)]
    return job.model_copy(update={"steps": steps, "translation_lang": lang})
