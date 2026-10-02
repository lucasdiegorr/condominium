import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { identityApi, type CondominiumBrief } from "../api/client";
import { useAuth, type CondominiumRef } from "../auth/AuthContext";
import { t } from "../i18n";
import { ErrorNote } from "../components/ui";

/**
 * Condominium selection screen.
 *
 * Lists the condominiums associated with the current identity, issues a scoped
 * token on selection, decodes the roles and stores the session (task 11.1).
 */
export default function CondominiumSelectPage() {
  const { identityToken, signOut, selectCondominium } = useAuth();
  const navigate = useNavigate();

  const [condominiums, setCondominiums] = useState<CondominiumBrief[]>([]);
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

  async function handleSelect(condominium: CondominiumRef) {
    if (!identityToken) return;
    setSelecting(condominium);
    setError(false);
    try {
      const scoped = await identityApi.selectCondominium(identityToken, condominium.id);
      selectCondominium(condominium, scoped.token);
      navigate("/app", { replace: true });
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
        <ErrorNote>{t("errors.generic")}</ErrorNote>
      ) : condominiums.length === 0 ? (
        <p>{t("selection.empty")}</p>
      ) : (
        <ul className="condominium-list">
          {condominiums.map((condominium) => (
            <li key={condominium.id}>
              <span>
                <strong>{condominium.name}</strong>
                {condominium.address ? <span className="muted"> · {condominium.address}</span> : null}
              </span>
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
      <div className="selection-actions">
        <button type="button" onClick={() => navigate("/app/condominiums")}>
          {t("selection.manageCondo")}
        </button>
        <button type="button" onClick={signOut}>
          {t("app.logout")}
        </button>
      </div>
    </main>
  );
}
