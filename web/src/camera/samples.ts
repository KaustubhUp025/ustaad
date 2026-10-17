// "Try the demo" sample photos (BUILD-GUIDE T27, DECISIONS 2026-10-16): a judge without an AC can still send each
// G2 photo. Every sample shows where it comes from; none is passed off as a photo the team took on a job.
export type Provenance = 'publicPost'

// `gate`: the safety gate the sample shows evidence for; a sample without one is for Ustaad's own photo requests.
export type Sample = { src: string; name: string; provenance: Provenance; gate?: string }

const SAMPLES: Sample[] = [
  { src: '/samples/display_e6.jpg', name: 'samples.displayE6', provenance: 'publicPost' },
  { src: '/samples/voltas_label.jpg', name: 'samples.voltasLabel', provenance: 'publicPost' },
]

// A gate's sheet offers only that gate's evidence: an E6 display can never pass the MCB OFF check (phone test, Oct 17).
export function samplesFor(gateId: string | undefined): Sample[] {
  return SAMPLES.filter((s) => s.gate === gateId)
}
