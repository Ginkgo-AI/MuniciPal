import type { Locale } from "@/i18n/routing";

/**
 * Common Spanish words/phrases for lightweight detection.
 * Requires at least 2 matches to avoid false positives on
 * shared words like "como" or "no".
 */
const SPANISH_MARKERS = new Set([
  "hola", "gracias", "por", "favor", "como", "esta", "estas",
  "necesito", "ayuda", "donde", "puedo", "quiero", "tengo",
  "permiso", "solicitud", "ciudad", "servicio", "servicios",
  "pregunta", "buenos", "dias", "buenas", "tardes", "noches",
  "permisos", "licencia", "pagar", "cuanto", "cuando",
  "que", "para", "una", "con", "del", "los", "las", "mas",
  "informacion", "sobre", "cual", "puede", "hacer", "tiene",
]);

const MIN_WORD_COUNT = 3;
const MIN_SPANISH_MATCHES = 2;

export function detectLanguage(text: string): Locale | null {
  const words = text
    .toLowerCase()
    .replace(/[¿?¡!.,;:]/g, "")
    .split(/\s+/)
    .filter(Boolean);

  if (words.length < MIN_WORD_COUNT) return null;

  let spanishHits = 0;
  for (const word of words) {
    if (SPANISH_MARKERS.has(word)) {
      spanishHits++;
    }
  }

  if (spanishHits >= MIN_SPANISH_MATCHES) return "es";

  // Not confident enough to determine language — don't switch
  return null;
}
