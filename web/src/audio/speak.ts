// SAFETY.md Enforcement 6: while a gate is open the server plays none of Ustaad's speech, and the gate screen's fixed
// text is the only instruction. The phone plays a recorded clip of that text (audio/gateClips.json); this browser voice
// is the fallback for a language with no clip.
const VOICE_LANG: Record<string, string> = { hi: 'hi-IN', te: 'te-IN', ta: 'ta-IN', bn: 'bn-IN', en: 'en-IN' }

export function pickVoice(voices: SpeechSynthesisVoice[], lang: string): SpeechSynthesisVoice | null {
  const tag = (VOICE_LANG[lang] ?? lang).toLowerCase()
  const norm = (v: SpeechSynthesisVoice) => v.lang.replace('_', '-').toLowerCase()
  return voices.find((v) => norm(v) === tag) ?? voices.find((v) => norm(v).startsWith(`${lang}-`)) ?? null
}

// Returns false when the phone has no voice for his language: Hindi text read by an English voice is worse than none.
export function speak(text: string, lang: string): boolean {
  if (!('speechSynthesis' in window)) return false
  const voices = speechSynthesis.getVoices()
  const voice = pickVoice(voices, lang)
  // Some browsers list no voices until later; then the language tag alone picks one.
  if (voices.length > 0 && !voice) return false
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = voice?.lang ?? VOICE_LANG[lang] ?? lang
  if (voice) utterance.voice = voice
  // Chrome drops an utterance spoken straight after cancel(), so cancel only when something is playing.
  if (speechSynthesis.speaking || speechSynthesis.pending) speechSynthesis.cancel()
  speechSynthesis.speak(utterance)
  return true
}
