# Ustaad — design brief and token system

Read this before any UI work, whichever coding agent or model you use. It was written with a
plan → review-against-generic-defaults → build → critique method (see `docs/playbooks/ui-pass.md`),
so every tool produces the same look.

## The brief in one paragraph

**Subject:** a repair technician's working day — blinking AC error displays, multimeters, PCBs,
copper pipe, insulation tape, a toolbag on a two-wheeler. **Audience:** Raju, 34, Hindi-first,
cracked Android screen, dirty hands, standing in sunlight at a customer's door. **The app's single
job:** get him from "the AC is blinking E6" to "fixed" by talking, with his hands mostly busy.
The dashboard's job: show a shop owner (and judges) that the team's knowledge is being captured.

## Colour (from the toolbag, not from a template)

| Name | Hex | Where it comes from | Use |
| --- | --- | --- | --- |
| Housing White | `#EEF1EF` | the cool white plastic of an indoor AC unit | app background (light) |
| Graphite | `#1D2327` | multimeter body, PCB shadow | text; dark-mode background is `#182024` |
| Meter Yellow | `#F6BE00` | the multimeter casing | the mic and primary actions only; text on it is Graphite |
| Solder Green | `#0B6B4F` | PCB solder mask | in stock, verified, source chips |
| Copper | `#A9592D` | copper refrigerant pipe | parts, prices, vendor quotes |
| Fault Red | `#D1263A` | the red LED on a fault | safety stops only; never decoration |
| LED Cyan | `#36D1E0` | the 7-segment display | only inside the error-code readout, on Graphite |

Icon discs on Home take a role colour: Solder Green for the WhatsApp import, Copper for stock, and
the text colour (inverted) for the rest, so they stay visible in dark mode.

Contrast: Graphite on Housing White and Graphite on Meter Yellow both pass WCAG AA for body text.
Never put white text on Meter Yellow.

## Type

| Role | Face | Notes |
| --- | --- | --- |
| Display (Latin headings, numbers) | **Archivo** (variable width; use 85–100% width) | Feels like equipment labelling, not a magazine. Used with restraint: screen titles, part numbers, prices. |
| Body and all Indian scripts | **Noto Sans**, **Noto Sans Devanagari / Telugu / Tamil / Bengali** | One family across five scripts, so Hindi and Telugu captions sit at the same weight and size as English. |
| Error-code readout only | **DSEG7 Classic** (OFL) | The 7-segment face of the AC display itself. Used in exactly one component. |

Scale (mobile): 14 / 18 (body) / 20 (captions) / 24 / 32 / 48 (code readout). Line height 1.45 for
Latin, 1.6 for Indian scripts. Sentence case everywhere. No all-caps labels, no eyebrow text above
headings, no monospace for small data, no "→" appended to buttons.

## The signature: the error-code readout

At the top of the job screen sits a Graphite strip with the appliance's code in LED Cyan
7-segment digits — `E6` exactly as the AC shows it — and the model next to it in Archivo.
When Ustaad identifies the photo, the readout blinks twice like the real unit, then holds steady.
That is the one orchestrated motion in the app. On a laptop, Home shows the same readout under the
first question, so the screen ends on what the job screen will show. It says "Ustaad sees what you see."
Everything else stays quiet.

## Two rules for every screen (phone test, Oct 18)

1. **Every screen explains itself.** A first-time visitor (a judge, or Raju on his first day) can
   tell from the screen alone what it is for and what to do next: one line of purpose under the
   title, an empty state that says what to do and offers it (a button, a question to tap), and a
   way back home. "No parts yet" alone is not an empty state.
2. **No dead space.** No band of empty background between pieces of content. Content sits at the
   top and grows down; the only free space is above the mic, where the conversation will grow.
   On wide screens, columns don't stretch to each other's height, and a single column is never
   a thin strip in the middle of a laptop screen.

## Layout

Every worker screen starts with the same Graphite header: the logo lockup (44px tall, so उस्ताद
stays readable), a back arrow everywhere except Home, and a status pill on the right (dot + word:
Live, Checking, Offline).

**Home** (phone: one column; laptop: two columns, the hero not stretched):

```
┌───────────────────────────────┐
│ [logo] Ustaad          ● Live  │  ← header
│ Repair help you can talk to    │  ← hero continues the header's Graphite
│ One paragraph: what it does    │
│ [ 🎙 Try in English         ]  │  ← Meter Yellow, the one primary action
│ [   हिंदी में आज़माएँ        ]  │
│ ▌Try saying "Voltas AC, E6…"   │  ← the first question, so nobody stares at a mic
├───────────────────────────────┤
│ How a job goes                 │  ← a real sequence, so numbered 1-2-3
│ ① Ask by voice ② Show a photo  │
│ ③ Fix it safely                │
│ More in Ustaad                 │  ← one list of rows, not cards:
│ (●) Import a WhatsApp group  › │     Solder Green chat icon
│ (●) Your stock               › │     Copper box icon
│ (●) Knowledge cards          › │
│ (●) Set up a profile         › │
│ No login. Demo data labelled.  │
└───────────────────────────────┘
```

**Job screen** (single column, left-aligned text, thumb zone at the bottom):

```
┌───────────────────────────────┐
│ ←  [logo] Ustaad       ● Live  │
│ ▓▓  E6   Voltas · 183V CZQ     │  ← code readout, once a photo is read
├───────────────────────────────┤
│ Step 1 of 2                    │  ← step card first: what to do now. Shaped like a
│ [▶ Ramesh · May 2025]          │     service tag (4px radius, punched-hole notch);
│ Outdoor unit ka PCB dikhao     │     source chip in Solder Green
│ [ ✓ Done, next step         ]  │
│   ▌E6 aa raha hai, kya karun?  │  ← captions under it, last 3 turns, 20px; the worker's
│ Ramesh ne May 2025 mein…       │     lines indented with a thin Solder Green rule
│                                │  ← the only free space: the conversation grows here
│ [Photo]    ( ● MIC )  [Manual] │  ← Meter Yellow round mic, 88px, bottom centre
└───────────────────────────────┘
```

Empty job: a guidance panel in place of the captions: the mic icon, "Hold the yellow mic and say
what's wrong", three example questions he can tap (sent as a text turn, shown as his line), and a
line pointing at the photo and manual buttons. Closed job: a Solder Green panel, "Job closed",
with "Start a new job" and "Home".

Safety gate: Graphite, a Meter Yellow shield and "Safety check first", the fixed instruction, the
photo it needs, one line on why Ustaad waits, then "Send photo" (primary) and "Hear it again".
The server mutes Ustaad while a gate is open (SAFETY.md, Enforcement 6), so the phone plays a
recorded clip of the same fixed text when the gate opens (`make gate-clips`); the browser's speech
voice is the fallback, and with no voice for his language it stays silent rather than read Hindi in
an English voice. Safety stop: the whole screen turns Fault Red with one sentence in the worker's
language, no audio, and only the way out: "Start a new job" and "Home" (the stopped job ends there). Camera sheet: slides up from the bottom (20px top radius) with Ustaad's request as the
title and a framing outline drawn over the viewfinder hint.

**Stock**: title, a "Demo data" label in Copper text (a label, never a bordered box that looks
like a button), one line on why the list matters ("Ustaad checks this before asking shops"), the
parts as rows with − and +, and how to change counts by voice. Empty: a Copper box icon, what to
say, and a way back.

Dashboard (desktop): left rail navigation; the knowledge base is a list of fault "tags" in rows
(brand · code · symptom · source · confidence), not a grid of identical cards. The import page
shows voice notes as a vertical waveform list that turns into tags as cards are extracted.
Area map: Housing White map tiles desaturated, hotspots in Copper.

## Shape and spacing

8px grid. Radii carry meaning: 4px for tags and step cards (things you'd stick on a unit),
12px for sheets and inputs, fully round only for the mic. No drop shadows except the camera sheet
(it floats above the job). No gradients.

## Words

- Write as a senior technician talks: short, direct, Hinglish where the worker uses it.
- Buttons say what happens: "Photo bhejo", "Ho gaya", "Teen dukaan se poochho", "Approve quote".
- The same action keeps its name across the flow ("Approve quote" → toast "Quote approved").
- Errors say what went wrong and what to do: "Photo dhundhli hai. Thoda paas se lo, flash on karo."
- Seeded or synthetic data is always labelled "Demo data" or "Synthetic".

## Review against generic defaults (done before building)

| Default it risked | What we changed |
| --- | --- |
| Warm cream background with a terracotta accent (our first plan used #F7F4EE + #E8590C) | Cool AC-housing white with multimeter yellow, both taken from the technician's tools |
| Near-black with one acid accent | Dark mode is Graphite, and its accent comes from the LED readout, used in one place only |
| Identical rounded SaaS cards | Tags and rows with radii that mean something; one floating sheet |
| Monospace for data labels | Archivo with tabular figures for part numbers and prices |
| Scattered fade-in animations | One motion: the code readout blink |
| A bare mic on an empty screen (phone test, Oct 18) | The empty job says what to do and offers questions to tap |
| Feature tiles in a grid | "More in Ustaad" is one list of rows, each with what it is for |
| Content pinned to the bottom, empty band in the middle | Content top-aligned; free space only above the mic |

## Quality floor (every screen)
Works at 360px wide; 48px touch targets; visible focus rings; `prefers-reduced-motion` turns the
blink into a single fade; all five scripts render without fallback boxes; tested in sunlight.
