export const CAPTION_FOLLOW_THRESHOLD_PX = 64

type ScrollPosition = Pick<HTMLElement, 'clientHeight' | 'scrollHeight' | 'scrollTop'>

export function isNearCaptionBottom({ clientHeight, scrollHeight, scrollTop }: ScrollPosition) {
  return scrollHeight - scrollTop - clientHeight <= CAPTION_FOLLOW_THRESHOLD_PX
}
