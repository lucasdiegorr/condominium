import { useState } from "react";
import { identityApi, scopedApi, type CondominiumView } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { t } from "../i18n";
import { ErrorNote, Field, InlineForm, Loading, PageHeader, errorText, useScopedData } from "../components/ui";

/** Global-administrator screen: manage registered condominiums. */
export default function CondominiumsPage() {
  const { identityToken, condominium } = useAuth();
  // The backend only exposes this administration surface to global admins;
  // gate the section so other roles never attempt the identity-level list.
  const canManage = identityToken !== null; // Any logged‑in user; backend will enforce global‑admin rights

  const list = useScopedData(
    () =>
      canManage && identityToken
        ? identityApi.listAllCondominiums(identityToken)
        : Promise.resolve<CondominiumView[]>([]),
    [identityToken, canManage],
  );

  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  async function create() {
    if (!identityToken) return;
    setBusy(true);
    setError(null);
    try {
      await identityApi.createCondominium(identityToken, { name, address: address || null });
      setName("");
      setAddress("");
      list.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function updateNameAddress(item: CondominiumView, nextName: string, nextAddress: string) {
    if (item.id !== condominium?.id) {
      setError(t("admin.condominiums.scopeHint"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await scopedApi.updateCondominium({ name: nextName, address: nextAddress || null });
      list.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(item: CondominiumView) {
    if (item.id !== condominium?.id) {
      setError(t("admin.condominiums.scopeHint"));
      return;
    }
    if (!window.confirm(t("admin.condominiums.deleteConfirm"))) return;
    setBusy(true);
    setError(null);
    try {
      await scopedApi.deactivateCondominium();
      list.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  if (!canManage) {
    return (
      <div>
        <PageHeader title={t("admin.condominiums.title")} />
        <ErrorNote>{t("errors.forbidden")}</ErrorNote>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title={t("admin.condominiums.title")} subtitle={t("admin.condominiums.subtitle")} />
      <p className="hint">{t("admin.condominiums.scopeHint")}</p>
      {error ? <ErrorNote>{error}</ErrorNote> : null}

      <section className="card">
        <h3>{t("admin.condominiums.add")}</h3>
        <InlineForm onSubmit={() => void create()} busy={busy} submitLabel={t("common.save")}>
          <Field label={`${t("admin.condominiums.name")} *`}>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label={t("admin.condominiums.address")}>
            <input value={address} onChange={(e) => setAddress(e.target.value)} />
          </Field>
        </InlineForm>
      </section>

      {list.loading ? (
        <Loading />
      ) : list.error ? (
        <ErrorNote>{list.error}</ErrorNote>
      ) : (
        <ul className="card-list">
          {(list.data ?? []).map((item) => (
            <li key={item.id} className="card">
              <div className="row-head">
                <strong>{item.name}</strong>
                <span className={`badge ${item.active ? "ok" : "muted"}`}>
                  {item.active ? t("common.active") : t("common.inactive")}
                </span>
              </div>
              <p className="muted">{item.address ?? t("common.none")}</p>
              {editingId === item.id ? (
                <CondominiumEditForm
                  item={item}
                  onSave={updateNameAddress}
                  busy={busy}
                  onDone={() => setEditingId(null)}
                />
              ) : (
                <span className="row-actions">
                  <button type="button" onClick={() => setEditingId(editingId === item.id ? null : item.id)}>
                    {t("common.edit")}
                  </button>
                  <button type="button" onClick={() => void toggleActive(item)} disabled={!item.active}>
                    {t("admin.condominiums.deactivate")}
                  </button>
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CondominiumEditForm({
  item,
  onSave,
  busy,
  onDone,
}: {
  item: CondominiumView;
  onSave: (item: CondominiumView, name: string, address: string) => Promise<void>;
  busy: boolean;
  onDone: () => void;
}) {
  const [name, setName] = useState(item.name);
  const [address, setAddress] = useState(item.address ?? "");
  const [error, setError] = useState<string | null>(null);

  async function save() {
    try {
      await onSave(item, name, address);
      onDone();
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <InlineForm onSubmit={() => void save()} busy={busy} submitLabel={t("common.save")}>
      <Field label={t("admin.condominiums.name")}>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </Field>
      <Field label={t("admin.condominiums.address")}>
        <input value={address} onChange={(e) => setAddress(e.target.value)} />
      </Field>
      {error ? <ErrorNote>{error}</ErrorNote> : null}
    </InlineForm>
  );
}
