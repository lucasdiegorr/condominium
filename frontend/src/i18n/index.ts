/**
 * Lightweight i18n layer.
 *
 * UI strings ALWAYS come from the translation catalog — never hardcode
 * user-visible text in components. English is the default language;
 * Brazilian Portuguese lives only in the pt-BR catalog.
 */

import en from "./en.json";
import ptBR from "./pt-BR.json";

export type Locale = "en" | "pt-BR";

type CatalogValue = string | { [key: string]: CatalogValue };
type Catalog = Record<string, string>;

const STORAGE_KEY = "condominium.locale";

function flattenCatalog(value: CatalogValue, prefix = ""): Catalog {
  const flat: Catalog = {};
  for (const [key, entry] of Object.entries(value)) {
    const dotted = prefix ? `${prefix}.${key}` : key;
    if (typeof entry === "string") {
      flat[dotted] = entry;
    } else {
      Object.assign(flat, flattenCatalog(entry, dotted));
    }
  }
  return flat;
}

const catalogs: Record<Locale, Catalog> = {
  en: flattenCatalog(en as CatalogValue),
  "pt-BR": flattenCatalog(ptBR as CatalogValue),
};

export function getLocale(): Locale {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "en" || stored === "pt-BR") return stored;
  return "en";
}

export function setLocale(locale: Locale): void {
  localStorage.setItem(STORAGE_KEY, locale);
}

/** Translate a dot-notation key, e.g. t("login.title"). Supports {param} interpolation. */
export function t(key: string, params?: Record<string, string | number>): string {
  const catalog = catalogs[getLocale()];
  let value = catalog[key] ?? catalogs.en[key] ?? key;
  if (params) {
    for (const [name, val] of Object.entries(params)) {
      value = value.replaceAll(`{${name}}`, String(val));
    }
  }
  return value;
}
