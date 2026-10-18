export type CaptionLine = { id: number; who: 'user' | 'ustaad'; text: string; final: boolean }

type CaptionFrame = Omit<CaptionLine, 'id'>

// Bounded session history lets a worker review the conversation without unbounded browser memory growth.
export const CAPTION_HISTORY_LIMIT = 100

export function addCaption(lines: CaptionLine[], { who, text, final }: CaptionFrame): CaptionLine[] {
  const open = lines.findLastIndex((line) => line.who === who && !line.final)
  const next = open === -1
    ? [...lines, { id: (lines.at(-1)?.id ?? 0) + 1, who, text, final }]
    : lines.with(open, { ...lines[open], text, final })
  return next.slice(-CAPTION_HISTORY_LIMIT)
}
