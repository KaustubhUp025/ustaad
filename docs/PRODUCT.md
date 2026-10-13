# Ustaad — what we're building and why

Read this once at the start of any task that touches behaviour, copy or UI. It explains the aim; SPEC.md says
exactly what to build.

## One sentence
Ustaad is the senior technician in every repair worker's pocket: it turns a technician group's buried WhatsApp
voice notes into a spoken, cited answer, in the worker's language, while he stands in front of the broken machine.

## The user
**Raju, 34, independent AC and appliance technician in Lucknow.** Hindi-first, reads some English, Class 10.
Cracked Android phone, patchy 4G indoors, hands dirty and busy. In peak summer he does 6–8 jobs a day.
He belongs to technician WhatsApp groups with hundreds of unplayed voice notes. When stuck, he calls a senior
who is usually up a ladder at another job.
Also: the senior ("Ustaad-ji") whose knowledge we capture and credit; the shop owner who sees the dashboard;
parts vendors who receive structured quote requests on WhatsApp.

## The four moments (each is a demo beat)
| Moment | Today | With Ustaad |
| --- | --- | --- |
| Before the job | Complaint arrives with no model number; wrong parts packed | Likely causes and parts to carry, checked against his stock (S6) |
| Stuck at the door | Blinking E6; senior unreachable; scrolling 400 voice notes | Photo + Hinglish question → spoken step-by-step help, citing "Ramesh, May 2025" (M2–M5) |
| Missing a part | Rides to market shop to shop | Stock checked, 3 nearby shops asked on WhatsApp, one tap to approve (M7–M8) |
| After the job | Fix never written down | Ustaad asks two questions and writes a new fault card; area view spots repeats (M9, S2) |

## What makes it different (lead with these in UI copy, README, deck)
1. Voice notes become knowledge: a WhatsApp export becomes cited fault cards.
2. The agent learns the worker (memory) and every closed job teaches it.
3. It acts: sources parts while he keeps working.
4. It sees what no single worker sees: same model failing across nearby pincodes.

## The hackathon (how we're judged)
Google Cloud AI Builder Cup 2026, theme **Future of Work & Enterprise Productivity**. Judges see a 3-minute video,
a deck, the public repo and a live link (they may try it on their phone).
| Criterion | Weight | What earns it here |
| --- | --- | --- |
| Technical merit & Gen AI | 40% | Real Live voice in 4 languages, vision, transcription, cited retrieval, memory, safety gates in code, measured numbers |
| Problem alignment & impact | 25% | The four moments, real recordings, CEEW evidence (57% of technicians untrained in 5+ years) |
| Innovation | 25% | Voice notes → knowledge; agent asks to see; cross-pincode clusters; agent sources parts |
| UX | 10% | One thumb, voice-first, captions, safety stops, the error-code readout |

## What "done" looks like for a judge (2 minutes)
Open the link on a phone → Try the demo → hold the mic, ask "E6 aa raha hai, kya karun?" → hear and read a cited
answer → Ustaad asks for a photo → safety stop → next step. On a laptop, `/d/import` shows a WhatsApp export
turning into cards live. Nothing needs a login, a WhatsApp number or an AC.

## Non-goals
Payments, native app, real auth, other trades, continuous camera streaming, on-device models, reading WhatsApp
groups directly. Don't build towards them; don't add hooks "for later".

## Principles every change must respect
- **Safety beats helpfulness.** Never show a hazardous step before its gate; never give refrigerant handling steps.
- **Cite, or say it is general guidance.** Advice with no card or manual behind it is labelled general, aloud and
  on the step card, and never includes an error-code meaning.
- **The worker's language, his words.** Hinglish is normal; never correct him.
- **Honest demo.** Seeded or synthetic data is always labelled. Error-code meanings come from real manuals.
- **Prototype, not platform.** The smallest thing that makes the demo real and robust.
