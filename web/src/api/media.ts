// Photo upload for the camera sheet: shrink on the phone, then PUT straight to Storage with a signed URL
// (POST /api/media/upload-url, shared/contracts/rest.md). The API never streams the bytes.
const API_URL = import.meta.env.VITE_API_URL ?? ''
const MAX_SIDE = 1600 // big enough to read a nameplate, small enough for 4G
const QUALITY = 0.85

// Canvas re-encoding also turns an iPhone HEIC into JPEG.
async function toJpeg(file: File): Promise<Blob> {
  const image = await createImageBitmap(file)
  const scale = Math.min(1, MAX_SIDE / Math.max(image.width, image.height))
  const canvas = new OffscreenCanvas(Math.round(image.width * scale), Math.round(image.height * scale))
  canvas.getContext('2d')!.drawImage(image, 0, 0, canvas.width, canvas.height)
  return canvas.convertToBlob({ type: 'image/jpeg', quality: QUALITY })
}

// Returns the gs:// URI to send in media_ready.
export async function uploadPhoto(file: File, jobId: string, requestId: string): Promise<string> {
  const body = await toJpeg(file)
  const res = await fetch(`${API_URL}/api/media/upload-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind: 'photo', content_type: 'image/jpeg', job_id: jobId, filename: `${requestId}.jpg` }),
  })
  if (!res.ok) throw new Error(`upload-url ${res.status}`)
  const signed: { upload_url: string; uri: string; headers: Record<string, string> } = await res.json()
  const put = await fetch(signed.upload_url, { method: 'PUT', headers: signed.headers, body })
  if (!put.ok) throw new Error(`upload ${put.status}`)
  return signed.uri
}
