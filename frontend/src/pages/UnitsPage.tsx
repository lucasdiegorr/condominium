import { useState } from "react";
import { scopedApi, type UnitView } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { perm } from "../auth/permissions";
import { t } from "../i18n";
import { ErrorNote, Field, InlineForm, Loading, PageHeader, errorText, useScopedData } from "../components/ui";

interface ParkingForm {
  identifier: string;
  spot_type: string;
}

export default function UnitsPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission(perm.UNITS_MANAGE);
  const { data: units, loading, error, reload } = useScopedData(() => scopedApi.listUnits());

  const [number, setNumber] = useState("");
  const [block, setBlock] = useState("");
  const [unitType, setUnitType] = useState("apartment");
  const [fraction, setFraction] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [spotFor, setSpotFor] = useState<number | null>(null);
  const [parking, setParking] = useState<ParkingForm>({ identifier: "", spot_type: "uncovered" });

  function resetCreate() {
    setNumber("");
    setBlock("");
    setUnitType("apartment");
    setFraction("");
  }

  async function handleCreate() {
    setBusy(true);
    setFormError(null);
    try {
      await scopedApi.createUnit({ number, block: block || null, unit_type: unitType, fraction });
      resetCreate();
      reload();
    } catch (err) {
      setFormError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleAddSpot(unit: UnitView) {
    setBusy(true);
    setFormError(null);
    try {
      await scopedApi.addParkingSpot(unit.id, parking);
      setSpotFor(null);
      setParking({ identifier: "", spot_type: "uncovered" });
      reload();
    } catch (err) {
      setFormError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(unit: UnitView) {
    if (!window.confirm(t("common.confirmDelete"))) return;
    setFormError(null);
    try {
      await scopedApi.deleteUnit(unit.id);
      reload();
    } catch (err) {
      setFormError(errorText(err));
    }
  }

  async function handleRemoveSpot(spotId: number) {
    setFormError(null);
    try {
      await scopedApi.deleteParkingSpot(spotId);
      reload();
    } catch (err) {
      setFormError(errorText(err));
    }
  }

  return (
    <div>
      <PageHeader title={t("units.title")} subtitle={t("units.subtitle")} />
      {formError ? <ErrorNote>{formError}</ErrorNote> : null}

      {canManage ? (
        <section className="card">
          <h3>{t("units.addUnit")}</h3>
          <InlineForm onSubmit={() => void handleCreate()} busy={busy} submitLabel={t("common.save")}>
            <Field label={t("units.number")}>
              <input value={number} onChange={(e) => setNumber(e.target.value)} required />
            </Field>
            <Field label={t("units.block")}>
              <input value={block} onChange={(e) => setBlock(e.target.value)} />
            </Field>
            <Field label={t("units.unitType")}>
              <select value={unitType} onChange={(e) => setUnitType(e.target.value)}>
                <option value="apartment">{t("units.unitType.apartment")}</option>
                <option value="commercial">{t("units.unitType.commercial")}</option>
                <option value="other">{t("units.unitType.other")}</option>
              </select>
            </Field>
            <Field label={`${t("units.fraction")} *`}>
              <input
                type="number"
                min="0.000001"
                max="100"
                step="any"
                value={fraction}
                onChange={(e) => setFraction(e.target.value)}
                required
              />
            </Field>
            <p className="hint">{t("units.fractionHint")}</p>
          </InlineForm>
        </section>
      ) : null}

      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorNote>{error}</ErrorNote>
      ) : (
        <ul className="card-list">
          {(units ?? []).map((unit) => (
            <li key={unit.id} className="card">
              <div className="row-head">
                <strong>#{unit.code}</strong>
                <span className={`badge ${unit.active ? "ok" : "muted"}`}>
                  {unit.active ? t("common.active") : t("common.inactive")}
                </span>
                {canManage ? (
                  <span className="row-actions">
                    <button type="button" onClick={() => setEditingId(editingId === unit.id ? null : unit.id)}>
                      {t("common.edit")}
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(unit)}
                      disabled={unit.parking_spots.length > 0}
                      title={unit.parking_spots.length > 0 ? t("units.deleteError") : undefined}
                    >
                      {t("common.delete")}
                    </button>
                  </span>
                ) : null}
              </div>
              <p className="muted">
                {unit.number} · {t(`units.unitType.${unit.unit_type}`)} ·{" "}
                {t("units.fraction")} {unit.fraction}
              </p>
              {editingId === unit.id && canManage ? (
                <UnitEditForm unit={unit} onDone={reload} />
              ) : null}
              <div className="sub-section">
                <strong>{t("units.parking")}</strong>
                <ul>
                  {unit.parking_spots.map((spot) => (
                    <li key={spot.id}>
                      {spot.identifier} ({t(`units.spotType.${spot.spot_type}`)})
                      {canManage ? (
                        <button type="button" onClick={() => void handleRemoveSpot(spot.id)}>
                          {t("common.delete")}
                        </button>
                      ) : null}
                    </li>
                  ))}
                </ul>
                {canManage ? (
                  spotFor === unit.id ? (
                    <InlineForm
                      onSubmit={() => void handleAddSpot(unit)}
                      busy={busy}
                      submitLabel={t("common.add")}
                    >
                      <Field label={t("units.spotIdentifier")}>
                        <input
                          value={parking.identifier}
                          onChange={(e) => setParking({ ...parking, identifier: e.target.value })}
                          required
                        />
                      </Field>
                      <Field label={t("units.spotType")}>
                        <select
                          value={parking.spot_type}
                          onChange={(e) => setParking({ ...parking, spot_type: e.target.value })}
                        >
                          <option value="covered">{t("units.spotType.covered")}</option>
                          <option value="uncovered">{t("units.spotType.uncovered")}</option>
                        </select>
                      </Field>
                    </InlineForm>
                  ) : (
                    <button type="button" onClick={() => setSpotFor(unit.id)}>
                      {t("units.addSpot")}
                    </button>
                  )
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function UnitEditForm({ unit, onDone }: { unit: UnitView; onDone: () => void }) {
  const [number, setNumber] = useState(unit.number);
  const [block, setBlock] = useState(unit.block ?? "");
  const [unitType, setUnitType] = useState(unit.unit_type);
  const [fraction, setFraction] = useState(unit.fraction);
  const [active, setActive] = useState(unit.active);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await scopedApi.updateUnit(unit.id, {
        number,
        block: block || null,
        unit_type: unitType,
        fraction,
        active,
      });
      onDone();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <InlineForm onSubmit={() => void submit()} busy={busy} submitLabel={t("common.save")}>
      <Field label={t("units.number")}>
        <input value={number} onChange={(e) => setNumber(e.target.value)} required />
      </Field>
      <Field label={t("units.block")}>
        <input value={block} onChange={(e) => setBlock(e.target.value)} />
      </Field>
      <Field label={t("units.unitType")}>
        <select value={unitType} onChange={(e) => setUnitType(e.target.value)}>
          <option value="apartment">{t("units.unitType.apartment")}</option>
          <option value="commercial">{t("units.unitType.commercial")}</option>
          <option value="other">{t("units.unitType.other")}</option>
        </select>
      </Field>
      <Field label={`${t("units.fraction")} *`}>
        <input
          type="number"
          min="0.000001"
          max="100"
          step="any"
          value={fraction}
          onChange={(e) => setFraction(e.target.value)}
          required
        />
      </Field>
      <Field label={t("units.active")}>
        <label className="check">
          <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
          {unit.code}
        </label>
      </Field>
      {error ? <ErrorNote>{error}</ErrorNote> : null}
    </InlineForm>
  );
}
