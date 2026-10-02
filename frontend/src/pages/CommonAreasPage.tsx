import { useState } from "react";
import { scopedApi, type CommonAreaView } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { perm } from "../auth/permissions";
import { t } from "../i18n";
import { ErrorNote, Field, InlineForm, Loading, PageHeader, errorText, useScopedData } from "../components/ui";

export default function CommonAreasPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission(perm.COMMON_AREAS_MANAGE);
  const areas = useScopedData(() => scopedApi.listCommonAreas());

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [capacity, setCapacity] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      await scopedApi.createCommonArea({
        name,
        description: description || null,
        capacity: capacity === "" ? null : Number(capacity),
      });
      setName("");
      setDescription("");
      setCapacity("");
      areas.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(area: CommonAreaView) {
    if (!window.confirm(t("common.confirmDelete"))) return;
    setBusy(true);
    setError(null);
    try {
      await scopedApi.deleteCommonArea(area.id);
      areas.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title={t("areas.title")} subtitle={t("areas.subtitle")} />
      {error ? <ErrorNote>{error}</ErrorNote> : null}

      {canManage ? (
        <section className="card">
          <h3>{t("areas.addArea")}</h3>
          <InlineForm onSubmit={() => void handleCreate()} busy={busy} submitLabel={t("common.save")}>
            <Field label={`${t("areas.name")} *`}>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </Field>
            <Field label={t("areas.description")}>
              <input value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
            <Field label={t("areas.capacity")}>
              <input
                type="number"
                min="0"
                value={capacity}
                onChange={(e) => setCapacity(e.target.value)}
              />
            </Field>
          </InlineForm>
        </section>
      ) : null}

      {areas.loading ? (
        <Loading />
      ) : areas.error ? (
        <ErrorNote>{areas.error}</ErrorNote>
      ) : (
        <ul className="card-list">
          {(areas.data ?? []).map((area) => (
            <li key={area.id} className="card">
              <div className="row-head">
                <strong>{area.name}</strong>
                <span className="muted">
                  {area.capacity !== null ? `${t("areas.capacity")}: ${area.capacity}` : t("common.none")}
                </span>
                {canManage ? (
                  <span className="row-actions">
                    <button type="button" onClick={() => setEditingId(editingId === area.id ? null : area.id)}>
                      {t("common.edit")}
                    </button>
                    <button type="button" onClick={() => void handleDelete(area)}>
                      {t("common.delete")}
                    </button>
                  </span>
                ) : null}
              </div>
              {area.description ? <p className="muted">{area.description}</p> : null}
              {editingId === area.id && canManage ? (
                <AreaEditForm area={area} onDone={areas.reload} onError={setError} />
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function AreaEditForm({
  area,
  onDone,
  onError,
}: {
  area: CommonAreaView;
  onDone: () => void;
  onError: (message: string | null) => void;
}) {
  const [name, setName] = useState(area.name);
  const [description, setDescription] = useState(area.description ?? "");
  const [capacity, setCapacity] = useState(area.capacity === null ? "" : String(area.capacity));
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    onError(null);
    try {
      await scopedApi.updateCommonArea(area.id, {
        name,
        description: description || null,
        capacity: capacity === "" ? null : Number(capacity),
      });
      onDone();
    } catch (err) {
      onError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <InlineForm onSubmit={() => void save()} busy={busy} submitLabel={t("common.save")}>
      <Field label={t("areas.name")}>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </Field>
      <Field label={t("areas.description")}>
        <input value={description} onChange={(e) => setDescription(e.target.value)} />
      </Field>
      <Field label={t("areas.capacity")}>
        <input
          type="number"
          min="0"
          value={capacity}
          onChange={(e) => setCapacity(e.target.value)}
        />
      </Field>
    </InlineForm>
  );
}
