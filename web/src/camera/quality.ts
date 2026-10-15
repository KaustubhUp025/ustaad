// The phone-side photo check (BUILD-GUIDE T17): a very dark or very blurry photo is caught in a few milliseconds,
// before the upload and the ~5 s vision check. It only catches extremes; the server judges everything else.

// Placeholders: set from synthetic photos on Oct 15 (heavy blur 1.6, light blur 67, sharp 580; dark 45, normal 128).
// Tune from real phone photos of AC parts before trusting them; "send anyway" covers a wrong reject meanwhile.
export const MIN_BRIGHTNESS = 35
export const MIN_SHARPNESS = 15

type Pixels = { data: Uint8ClampedArray; width: number; height: number }
export type Measure = { brightness: number; sharpness: number }

// Brightness: mean luma (0-255). Sharpness: variance of a 3x3 Laplacian; low means few edges, as in a blurred photo.
export function measure({ data, width: w, height: h }: Pixels): Measure {
  const luma = new Float32Array(w * h)
  let sum = 0
  for (let i = 0; i < w * h; i++) {
    luma[i] = 0.299 * data[4 * i] + 0.587 * data[4 * i + 1] + 0.114 * data[4 * i + 2]
    sum += luma[i]
  }
  let mean = 0
  let square = 0
  let n = 0
  for (let y = 1; y < h - 1; y++)
    for (let x = 1; x < w - 1; x++) {
      const i = y * w + x
      const edge = luma[i - w] + luma[i + w] + luma[i - 1] + luma[i + 1] - 4 * luma[i]
      mean += edge
      square += edge * edge
      n++
    }
  return { brightness: sum / (w * h), sharpness: square / n - (mean / n) ** 2 }
}

export function photoProblem({ brightness, sharpness }: Measure): 'dark' | 'blurry' | null {
  if (brightness < MIN_BRIGHTNESS) return 'dark'
  if (sharpness < MIN_SHARPNESS) return 'blurry'
  return null
}
