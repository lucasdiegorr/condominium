import { useState } from "react";
import { scopedApi, type PersonView, type UnitView, type VehicleView } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { perm } from "../auth/permissions";
import { t } from "../i18n";
import { ErrorNote, Field, InlineForm, Loading, PageHeader, errorText, useScopedData } from "../components/ui";

export default function VehiclesPage() {
  const { hasPermission, unitLinks } = useAuth();
  const canManage = hasPermission(perm.VEHICLES_MANAGE);
  const canSelf = hasPermission(perm.VEHICLES_SELF);

  const vehicles = useScopedData(() => scopedApi.listVehicles());
  const residents = useScopedData<PersonView[]>(
    () => (canManage ? scopedApi.listResidents() : Promise.resolve([])),
    [canManage],
  );
  const units = useScopedData<UnitView[]>(() => scopedApi.listUnits());

  const [plate, setPlate] = useState("");
  const [model, setModel] = useState("");
  const [color, setColor] = useState("");
  const [residentId, setResidentId] = useState("");
  const [unitId, setUnitId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Units this user may register vehicles under (own linked units in self-service).
  const myUnitIds = new Set(unitLinks.map((link) => link.unit_id));

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      await scopedApi.createVehicle({
        plate,
        model,
        color: color || null,
        unit_id: Number(unitId),
        resident_id: canManage ? Number(residentId) : null,
      });
      setPlate("");
      setModel("");
      setColor("");
      setUnitId("");
      setResidentId("");
      vehicles.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const writable = canManage || canSelf;
  const shownUnits = (units.data ?? []).filter((unit) => canManage || myUnitIds.has(unit.id));

  return (
    <div>
      <PageHeader title={t("vehicles.title")} subtitle={t("vehicles.subtitle")} />
      {error ? <ErrorNote>{error}</ErrorNote> : null}

      {writable ? (
        <section className="card">
          <h3>{t("vehicles.addVehicle")}</h3>
          {!canManage ? <p className="hint">{t("vehicles.selfHint")}</p> : null}
          <InlineForm onSubmit={() => void handleCreate()} busy={busy} submitLabel={t("common.save")}>
            <Field label={t("vehicles.plate")}>
              <input
                value={plate}
                onChange={(e) => setPlate(e.target.value.toUpperCase())}
                minLength={7}
                maxLength={10}
                required
              />
            </Field>
            <Field label={t("vehicles.model")}>
              <input value={model} onChange={(e) => setModel(e.target.value)} required />
            </Field>
            <Field label={t("vehicles.color")}>
              <input value={color} onChange={(e) => setColor(e.target.value)} />
            </Field>
            {canManage ? (
              <Field label={t("vehicles.resident")}>
                <select value={residentId} onChange={(e) => setResidentId(e.target.value)} required>
                  <option value="">{t("common.none")}</option>
                  {(residents.data ?? []).map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.name}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            <Field label={t("vehicles.unit")}>
              <select value={unitId} onChange={(e) => setUnitId(e.target.value)} required>
                <option value="">{t("common.none")}</option>
                {shownUnits.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.code}
                  </option>
                ))}
              </select>
            </Field>
          </InlineForm>
        </section>
      ) : null}

      {vehicles.loading ? (
        <Loading />
      ) : vehicles.error ? (
        <ErrorNote>{vehicles.error}</ErrorNote>
      ) : (
        <ul className="card-list">
          {(vehicles.data ?? []).map((vehicle) => (
            <VehicleRow
              key={vehicle.id}
              vehicle={vehicle}
              writable={writable || canManage}
              onChanged={vehicles.reload}
              onError={setError}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function VehicleRow({
  vehicle,
  writable,
  onChanged,
  onError,
}: {
  vehicle: VehicleView;
  writable: boolean;
  onChanged: () => void;
  onError: (message: string | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [model, setModel] = useState(vehicle.model);
  const [color, setColor] = useState(vehicle.color ?? "");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    onError(null);
    try {
      await scopedApi.updateVehicle(vehicle.id, { model, color: color || null });
      setEditing(false);
      onChanged();
    } catch (err) {
      onError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(t("common.confirmDelete"))) return;
    setBusy(true);
    onError(null);
    try {
      await scopedApi.deleteVehicle(vehicle.id);
      onChanged();
    } catch (err) {
      onError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="card">
      <div className="row-head">
        <strong>{vehicle.plate}</strong>
        <span className="muted">
          {vehicle.model} · {vehicle.color ?? t("common.none")} · {vehicle.unit_code ?? vehicle.unit_id}
        </span>
        {writable ? (
          <span className="row-actions">
            <button type="button" onClick={() => setEditing(!editing)}>
              {t("common.edit")}
            </button>
            <button type="button" onClick={() => void remove()}>
              {t("common.delete")}
            </button>
          </span>
        ) : null}
      </div>
      <p className="muted">{vehicle.resident_name}</p>
      {editing ? (
        <InlineForm onSubmit={() => void save()} busy={busy} submitLabel={t("common.save")}>
          <Field label={t("vehicles.model")}>
            <input value={model} onChange={(e) => setModel(e.target.value)} required />
          </Field>
          <Field label={t("vehicles.color")}>
            <input value={color} onChange={(e) => setColor(e.target.value)} />
          </Field>
        </InlineForm>
      ) : null}
    </li>
  );
}
