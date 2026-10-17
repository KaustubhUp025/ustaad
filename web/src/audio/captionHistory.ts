export type CaptionLine = { who: 'user' | 'ustaad'; text: string; final: boolean }

type CaptionFrame = CaptionLine

// Bounded session history lets a worker review the conversation without unbounded browser memory growth.
export const CAPTION_HISTORY_LIMIT = 100

export function addCaption(lines: CaptionLine[], { who, text, final }: CaptionFrame): CaptionLine[] {
  const open = lines.findLastIndex((line) => line.who === who && !line.final)
  const next = open === -1 ? [...lines, { who, text, final }] : lines.with(open, { who, text, final })
  return next.slice(-CAPTION_HISTORY_LIMIT)
}
