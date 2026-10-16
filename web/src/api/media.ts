// Photo upload for the camera sheet: PUT straight to Storage with a signed URL (POST /api/media/upload-url,
// shared/contracts/rest.md). The API never streams the bytes.
const API_URL = import.meta.env.VITE_API_URL ?? ''

// Returns the gs:// URI to send in media_ready.
export async function uploadPhoto(jpeg: Blob, jobId: string, requestId: string): Promise<string> {
  const res = await fetch(`${API_URL}/api/media/upload-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      kind: 'photo',
      content_type: 'image/jpeg',
      job_id: jobId,
      request_id: requestId,
      filename: `${requestId}.jpg`,
    }),
  })
  if (!res.ok) throw new Error(`upload-url ${res.status}`)
  const signed: { upload_url: string; uri: string; headers: Record<string, string> } = await res.json()
  const put = await fetch(signed.upload_url, { method: 'PUT', headers: signed.headers, body: jpeg })
  if (!put.ok) throw new Error(`upload ${put.status}`)
  return signed.uri
}

// The source chip's voice note (POST /api/media/audio-url): a signed GET URL for the import job's FLAC, valid 900 s.
export async function voiceNoteUrl(uri: string, token: string): Promise<string> {
  const res = await fetch(`${API_URL}/api/media/audio-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ uri }),
  })
  if (!res.ok) throw new Error(`audio-url ${res.status}`)
  const signed: { url: string } = await res.json()
  return signed.url
}
