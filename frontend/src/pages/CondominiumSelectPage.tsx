import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { identityApi } from "../api/client";
import { useAuth, type CondominiumRef } from "../auth/AuthContext";
import { t } from "../i18n";

/**
 * Condominium selection screen.
 *
 * Lists the condominiums associated with the current identity and issues a
 * scoped token on selection. Completed in the auth chapter (11.x).
 */
export default function CondominiumSelectPage() {
  const { identityToken } = useAuth();
  const navigate = useNavigate();

  const [condominiums, setCondominiums] = useState<CondominiumRef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selecting, setSelecting] = useState<CondominiumRef | null>(null);

  useEffect(() => {
    if (!identityToken) return;
    let cancelled = false;
    identityApi
      .listCondominiums(identityToken)
      .then((list) => {
        if (!cancelled) setCondominiums(list);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [identityToken]);

  // Scope selection is finalized in task 11.1; this placeholder records the
  // choice locally until the scoped-token endpoint call is wired up.
  async function handleSelect(condominium: CondominiumRef) {
    if (!identityToken) return;
    setSelecting(condominium);
    try {
      const scoped = await identityApi.selectCondominium(identityToken, condominium.id);
      localStorage.setItem("condominium.scoped", JSON.stringify(scoped));
      setSelecting(null);
    } catch {
      setError(true);
      setSelecting(null);
    }
  }

  return (
    <main className="selection-page">
      <h1>{t("selection.title")}</h1>
      {loading ? (
        <p>{t("app.loading")}</p>
      ) : error ? (
        <p className="form-error">{t("app.error")}</p>
      ) : condominiums.length === 0 ? (
        <p>{t("selection.empty")}</p>
      ) : (
        <ul className="condominium-list">
          {condominiums.map((condominium) => (
            <li key={condominium.id}>
              <span>{condominium.name}</span>
              <button
                type="button"
                onClick={() => void handleSelect(condominium)}
                disabled={selecting?.id === condominium.id}
              >
                {t("selection.select")}
              </button>
            </li>
          ))}
        </ul>
      )}
      <button type="button" onClick={() => navigate("/login", { replace: true })}>
        {t("app.logout")}
      </button>
    </main>
  );
}
