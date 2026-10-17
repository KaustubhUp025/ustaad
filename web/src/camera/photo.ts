// Turns a captured photo into the upload: a JPEG at most 1600 px on its long side (enough to read a nameplate,
// small enough for 4G; canvas re-encoding also turns an iPhone HEIC into JPEG), plus the phone-side check.
import { type Measure, measure, photoProblem } from './quality'

const MAX_SIDE = 1600
const CHECK_WIDTH = 320 // the check needs edges, not detail; small keeps it to a few milliseconds
const QUALITY = 0.85

export async function prepare(photo: Blob): Promise<{ jpeg: Blob; problem: ReturnType<typeof photoProblem>; measured: Measure }> {
  const image = await createImageBitmap(photo)
  const scale = Math.min(1, MAX_SIDE / Math.max(image.width, image.height))
  const full = new OffscreenCanvas(Math.round(image.width * scale), Math.round(image.height * scale))
  full.getContext('2d')!.drawImage(image, 0, 0, full.width, full.height)

  const small = new OffscreenCanvas(CHECK_WIDTH, Math.round((image.height / image.width) * CHECK_WIDTH))
  const ctx = small.getContext('2d')!
  ctx.drawImage(image, 0, 0, small.width, small.height)
  const measured = measure(ctx.getImageData(0, 0, small.width, small.height))

  const jpeg = await full.convertToBlob({ type: 'image/jpeg', quality: QUALITY })
  return { jpeg, problem: photoProblem(measured), measured }
}

// A photo the browser cannot decode (a broken file, or a gallery format it does not read) rejects in prepare; the
// sheet shows its failed state instead of an unhandled rejection that leaves it looking ready (PR #44 review).
export async function tryPrepare(photo: Blob, prep = prepare): Promise<Awaited<ReturnType<typeof prepare>> | null> {
  try {
    return await prep(photo)
  } catch {
    return null
  }
}
