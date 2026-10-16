// "Try the demo" sample photos (BUILD-GUIDE T27, DECISIONS 2026-10-16): a judge without an AC can still send each
// G2 photo. Every sample shows where it comes from; none is passed off as a photo the team took on a job.
export type Provenance = 'publicPost'

export type Sample = { src: string; name: string; provenance: Provenance }

export const SAMPLES: Sample[] = [
  { src: '/samples/display_e6.jpg', name: 'samples.displayE6', provenance: 'publicPost' },
  { src: '/samples/voltas_label.jpg', name: 'samples.voltasLabel', provenance: 'publicPost' },
]
