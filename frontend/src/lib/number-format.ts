/** Locale-aware formatting for values shown to people. Never use this for
 * scientific state, calculations, request payloads, or exported data. */
export type NumberFormatLocale = "en-US" | "es-CL";

export function formatNumber(
  value: number,
  locale: NumberFormatLocale,
  options: Intl.NumberFormatOptions = {},
): string {
  if (!Number.isFinite(value)) return String(value);
  const precision: Intl.NumberFormatOptions =
    "maximumFractionDigits" in options || "maximumSignificantDigits" in options
      ? {}
      : { maximumSignificantDigits: 8 };
  return new Intl.NumberFormat(locale, {
    useGrouping: false,
    ...precision,
    ...options,
  }).format(value);
}

export function formatCount(value: number, locale: NumberFormatLocale): string {
  return formatNumber(value, locale, { maximumFractionDigits: 0, useGrouping: true });
}

/** Use the active document language for components that do not receive a
 * language prop. The application maps Spanish UI language to es-CL. */
export function formatForCurrentLocale(value: number, options: Intl.NumberFormatOptions = {}): string {
  const language = typeof document === "undefined" ? "en" : document.documentElement.lang;
  return formatNumber(value, language.toLowerCase().startsWith("es") ? "es-CL" : "en-US", options);
}
