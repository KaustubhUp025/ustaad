// What the job screen shows for a repair: the current step, an open safety gate, or a safety stop
// (docs/SAFETY.md). Defence in depth: a hazardous step_card that arrives while a gate is open is dropped.
import type { ServerFrame } from './liveClient'

type Of<T extends ServerFrame['type']> = Extract<ServerFrame, { type: T }>

export type RepairView = {
  step: Of<'step_card'> | null
  gate: Of<'safety_gate'> | null
  failReason: string | null
  stop: Of<'safety_stop'> | null
}

export const noRepair: RepairView = { step: null, gate: null, failReason: null, stop: null }

export function repairReducer(view: RepairView, frame: ServerFrame): RepairView {
  switch (frame.type) {
    case 'safety_gate':
      return { ...view, gate: frame, failReason: null }
    case 'gate_result':
      if (frame.gate_id !== view.gate?.gate_id) return view
      return frame.passed ? { ...view, gate: null, failReason: null } : { ...view, failReason: frame.reason }
    case 'safety_stop':
      return { ...view, stop: frame }
    case 'step_card':
      if (view.gate && frame.hazard !== 'none') return view
      return { ...view, step: frame, stop: null }
    default:
      return view
  }
}
