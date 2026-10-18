// "Try the demo" sample photos (BUILD-GUIDE T27, DECISIONS 2026-10-16): a judge without an AC can still send each
// G2 photo. Every sample shows where it comes from; none is passed off as a photo the team took on a job.
export type Provenance = 'publicPost' | 'ownPhoto' | 'aiGenerated'

// `gate`: the safety gate the sample shows evidence for; a sample without one is for Ustaad's own photo requests.
export type Sample = { src: string; name: string; provenance: Provenance; gate?: string }

const SAMPLES: Sample[] = [
  { src: '/samples/display_e6.jpg', name: 'samples.displayE6', provenance: 'publicPost' },
  { src: '/samples/voltas_label.jpg', name: 'samples.voltasLabel', provenance: 'publicPost' },
  // A's own board, main breaker off (Oct 17); location data stripped. Passed the real gate check 3/3 at 0.95.
  { src: '/samples/mcb_off.jpg', name: 'samples.mcbOff', provenance: 'ownPhoto', gate: 'G_MAINS_OFF' },
  // The G2 retake pair: one public photo of an outdoor board, and the same photo blurred by us so the check asks again.
  { src: '/samples/pcb_clear.jpg', name: 'samples.pcbClear', provenance: 'publicPost' },
  { src: '/samples/pcb_blurry.jpg', name: 'samples.pcbBlurry', provenance: 'publicPost' },
  // AI-generated, reads 5.03 V: above the 5 V limit, so G_CAP_DISCHARGE refuses it (SAFETY.md). It shows the gate
  // holding; it can never open it.
  { src: '/samples/multimeter_5v.jpg', name: 'samples.meterHigh', provenance: 'aiGenerated', gate: 'G_CAP_DISCHARGE' },
]

// A gate's sheet offers only that gate's evidence: an E6 display can never pass the MCB OFF check (phone test, Oct 17).
export function samplesFor(gateId: string | undefined): Sample[] {
  return SAMPLES.filter((s) => s.gate === gateId)
}
