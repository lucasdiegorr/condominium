import { useState } from "react";
import { ApiError, scopedApi, type BookingView, type CommonAreaView, type PersonView, type UnitView } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { perm } from "../auth/permissions";
import { t } from "../i18n";
import { ErrorNote, Field, InlineForm, Loading, PageHeader, errorText, useScopedData } from "../components/ui";

const DURATIONS = [1, 2, 3] as const;

function localToIso(value: string): string {
  return new Date(value).toISOString();
}

function addHours(iso: string, hours: number): string {
  return new Date(new Date(iso).getTime() + hours * 3_600_000).toISOString();
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

export default function BookingsPage() {
  const { hasPermission, unitLinks, personId: myPersonId } = useAuth();
  const canManage = hasPermission(perm.BOOKINGS_MANAGE);
  const canSelf = hasPermission(perm.BOOKINGS_SELF);

  const bookings = useScopedData(() => scopedApi.listBookings());
  const areas = useScopedData<CommonAreaView[]>(() => scopedApi.listCommonAreas());
  const residents = useScopedData<PersonView[]>(
    () => (canManage ? scopedApi.listResidents() : Promise.resolve([])),
    [canManage],
  );
  const units = useScopedData<UnitView[]>(() => scopedApi.listUnits());

  const [areaId, setAreaId] = useState("");
  const [start, setStart] = useState("");
  const [duration, setDuration] = useState("2");
  const [customEnd, setCustomEnd] = useState("");
  const [unitId, setUnitId] = useState("");
  const [personId, setPersonId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const myUnitIds = new Set(unitLinks.map((link) => link.unit_id));
  const writable = canManage || canSelf;
  const shownUnits = (units.data ?? []).filter((unit) => canManage || myUnitIds.has(unit.id));

  async function handleCreate() {
    if (!start) {
      setError(t("common.requiredField"));
      return;
    }
    const startIso = localToIso(start);
    const endIso =
      duration === "0" ? localToIso(customEnd) : addHours(startIso, Number(duration));
    if (new Date(endIso).getTime() <= new Date(startIso).getTime()) {
      setError(t("bookings.endBeforeStart"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await scopedApi.createBooking({
        area_id: Number(areaId),
        start_at: startIso,
        end_at: endIso,
        unit_id: Number(unitId),
        person_id: canManage ? Number(personId) : null,
      });
      setStart("");
      setCustomEnd("");
      setUnitId("");
      setPersonId("");
      bookings.reload();
    } catch (err) {
      if (err instanceof ApiError && err.isConflict) {
        setError(t("bookings.conflict"));
      } else {
        setError(errorText(err));
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel(booking: BookingView) {
    if (!window.confirm(t("bookings.cancelConfirm"))) return;
    setBusy(true);
    setError(null);
    try {
      await scopedApi.cancelBooking(booking.id);
      bookings.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title={t("bookings.title")} subtitle={t("bookings.subtitle")} />
      {error ? <ErrorNote>{error}</ErrorNote> : null}

      {writable ? (
        <section className="card">
          <h3>{t("bookings.addBooking")}</h3>
          {canManage ? <p className="hint">{t("bookings.manageHint")}</p> : null}
          <InlineForm onSubmit={() => void handleCreate()} busy={busy} submitLabel={t("common.save")}>
            <Field label={t("bookings.area")}>
              <select value={areaId} onChange={(e) => setAreaId(e.target.value)} required>
                <option value="">{t("common.none")}</option>
                {(areas.data ?? []).map((area) => (
                  <option key={area.id} value={area.id}>
                    {area.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={`${t("bookings.start")} *`}>
              <input
                type="datetime-local"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                required
              />
            </Field>
            <Field label={t("bookings.duration")}>
              <select value={duration} onChange={(e) => setDuration(e.target.value)}>
                {DURATIONS.map((hours) => (
                  <option key={hours} value={hours}>
                    {t(`bookings.duration.${hours}h`)}
                  </option>
                ))}
                <option value="0">{t("bookings.duration.custom")}</option>
              </select>
            </Field>
            {duration === "0" ? (
              <Field label={`${t("bookings.end")} *`}>
                <input
                  type="datetime-local"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                  required
                />
              </Field>
            ) : null}
            {canManage ? (
              <Field label={t("bookings.person")}>
                <select value={personId} onChange={(e) => setPersonId(e.target.value)} required>
                  <option value="">{t("common.none")}</option>
                  {(residents.data ?? []).map((res) => (
                    <option key={res.id} value={res.id}>
                      {res.name}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            <Field label={t("bookings.unit")}>
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

      {bookings.loading ? (
        <Loading />
      ) : bookings.error ? (
        <ErrorNote>{bookings.error}</ErrorNote>
      ) : bookings.data?.length === 0 ? (
        <p className="muted">{t("common.none")}</p>
      ) : (
        <ul className="card-list">
          {(bookings.data ?? []).map((booking) => {
            const cancelled = booking.status === "cancelled";
            const canCancel = (canManage || booking.person_id === myPersonId) && !cancelled;
            return (
              <li key={booking.id} className={`card ${cancelled ? "is-muted" : ""}`}>
                <div className="row-head">
                  <strong>{booking.area_name ?? booking.area_id}</strong>
                  <span className={`badge ${cancelled ? "muted" : "ok"}`}>
                    {cancelled ? t("bookings.status.cancelled") : t("bookings.status.reserved")}
                  </span>
                  {canCancel ? (
                    <button type="button" onClick={() => void handleCancel(booking)}>
                      {t("bookings.cancelBooking")}
                    </button>
                  ) : null}
                </div>
                <p className="muted">
                  {formatDateTime(booking.start_at)} → {formatDateTime(booking.end_at)}
                </p>
                <p className="muted">
                  {booking.unit_code ?? t("common.none")} · {booking.person_name ?? t("common.none")}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
