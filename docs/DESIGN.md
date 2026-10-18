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
That is the one orchestrated motion in the app. It says "Ustaad sees what you see."
Everything else stays quiet.

## Layout

Worker app, job screen (single column, left-aligned text, thumb zone at the bottom):

```
┌───────────────────────────────┐
│ ▓▓  E6   Voltas 183V · 1.5T    │  ← code readout (Graphite strip, LED Cyan digits)
├───────────────────────────────┤
│ Ustaad: Pehle outdoor unit ki  │  ← live captions, bounded history (up to 100), 20px,
│ PCB dekhte hain…               │     worker's lines indented with a thin Solder Green rule
│   Raju: haan, khol diya        │
│ [▶ Ramesh · May 2025]          │  ← source chip (Solder Green outline)
├───────────────────────────────┤
│ Step 3 of 6                    │  ← step card shaped like a service tag
│ Capacitor ke terminals par     │     (4px radius, one punched-hole notch at left)
│ meter lagao. 0V aana chahiye.  │
│ [Photo bhejo]   [Ho gaya]      │
├───────────────────────────────┤
│        ( ●  MIC  )             │  ← Meter Yellow round button, 88px, bottom centre
│  Stock   Jobs   Ustaad   Me    │
└───────────────────────────────┘
```

Safety stop: the whole screen turns Fault Red with one sentence in the worker's language, a
photo button, and nothing else. Camera sheet: slides up from the bottom (20px top radius) with
Ustaad's request as the title and a framing outline drawn over the viewfinder hint.

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

## Quality floor (every screen)
Works at 360px wide; 48px touch targets; visible focus rings; `prefers-reduced-motion` turns the
blink into a single fade; all five scripts render without fallback boxes; tested in sunlight.
