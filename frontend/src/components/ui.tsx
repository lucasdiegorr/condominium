/** Shared UI primitives: loading/error rendering, scoped-data hook, small layout helpers. */

import { useEffect, useState, type ReactNode } from "react";
import { ApiError } from "../api/client";
import { t } from "../i18n";

/** Map an unknown error to a human-readable message (i18n-aware). */
export function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.isForbidden && error.message === "forbidden") return t("errors.forbidden");
    if (error.isUnauthorized) return t("errors.generic");
    if (error.message) return error.message;
    if (error.isConflict) return t("errors.conflict");
    return t("errors.generic");
  }
  return t("errors.generic");
}

export function Loading() {
  return <p className="muted">{t("app.loading")}</p>;
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <p className="form-error" role="alert">
      {children}
    </p>
  );
}

export interface ScopedDataState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/** Load scoped data with automatic state handling; call `reload` after mutations. */
export function useScopedData<T>(
  loader: () => Promise<T>,
  deps: readonly unknown[] = [],
): ScopedDataState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    loader()
      .then((value) => {
        if (!cancelled) setData(value);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(errorText(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  return {
    data,
    loading,
    error,
    reload: () => setTick((n) => n + 1),
  };
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="page-header">
      <h2>{title}</h2>
      {subtitle ? <p className="muted">{subtitle}</p> : null}
    </div>
  );
}

/** Simple labelled field wrapper backed by the global CSS `label` style. */
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label>{label}{children}</label>;
}

/** Inline form used by list pages: wraps inputs and a submit button. */
export function InlineForm({
  onSubmit,
  busy,
  submitLabel,
  children,
}: {
  onSubmit: () => void;
  busy: boolean;
  submitLabel: string;
  children: ReactNode;
}) {
  return (
    <form
      className="inline-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      {children}
      <button type="submit" disabled={busy}>
        {busy ? t("common.saving") : submitLabel}
      </button>
    </form>
  );
}
