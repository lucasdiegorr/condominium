import { useState } from "react";
import { scopedApi, type PersonView, type UnitView } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { perm } from "../auth/permissions";
import { t } from "../i18n";
import { ErrorNote, Field, InlineForm, Loading, PageHeader, errorText, useScopedData } from "../components/ui";

export default function ResidentsPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission(perm.RESIDENTS_MANAGE);
  const canCreateAccount = hasPermission(perm.USERS_MANAGE);
  const residents = useScopedData(() => scopedApi.listResidents());
  const units = useScopedData<UnitView[]>(() => scopedApi.listUnits());

  const [name, setName] = useState("");
  const [cpf, setCpf] = useState("");
  const [phone, setPhone] = useState("");
  const [emailContact, setEmailContact] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accountFor, setAccountFor] = useState<PersonView | null>(null);

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      await scopedApi.createResident({
        name,
        cpf,
        phone: phone || null,
        email_contact: emailContact || null,
      });
      setName("");
      setCpf("");
      setPhone("");
      setEmailContact("");
      residents.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title={t("residents.title")} subtitle={t("residents.subtitle")} />
      {error ? <ErrorNote>{error}</ErrorNote> : null}

      {canManage ? (
        <section className="card">
          <h3>{t("residents.addResident")}</h3>
          <InlineForm onSubmit={() => void handleCreate()} busy={busy} submitLabel={t("common.save")}>
            <Field label={t("residents.name")}>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </Field>
            <Field label={t("residents.cpf")}>
              <input
                value={cpf}
                onChange={(e) => setCpf(e.target.value.replace(/\D/g, "").slice(0, 11))}
                inputMode="numeric"
                required
              />
            </Field>
            <Field label={t("residents.phone")}>
              <input value={phone} onChange={(e) => setPhone(e.target.value)} />
            </Field>
            <Field label={t("residents.emailContact")}>
              <input
                type="email"
                value={emailContact}
                onChange={(e) => setEmailContact(e.target.value)}
              />
            </Field>
          </InlineForm>
        </section>
      ) : null}

      {residents.loading || units.loading ? (
        <Loading />
      ) : residents.error ? (
        <ErrorNote>{residents.error}</ErrorNote>
      ) : (
        <ul className="card-list">
          {(residents.data ?? []).map((person) => (
            <li key={person.id} className="card">
              <div className="row-head">
                <strong>{person.name}</strong>
                <span className={`badge ${person.has_account ? "ok" : "muted"}`}>
                  {person.has_account ? t("residents.hasAccount") : t("common.inactive")}
                </span>
                {canCreateAccount && !person.has_account ? (
                  <button type="button" onClick={() => setAccountFor(accountFor?.id === person.id ? null : person)}>
                    {t("residents.createAccount")}
                  </button>
                ) : null}
              </div>
              <p className="muted">
                {t("residents.cpf")} {person.cpf}
              </p>
              {accountFor?.id === person.id ? (
                <AccountForm person={person} onDone={() => { setAccountFor(null); residents.reload(); }} />
              ) : null}
              <ResidentLinks
                person={person}
                units={units.data ?? []}
                canManage={canManage}
                onChanged={residents.reload}
                onError={setError}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ResidentLinks({
  person,
  units,
  canManage,
  onChanged,
  onError,
}: {
  person: PersonView;
  units: UnitView[];
  canManage: boolean;
  onChanged: () => void;
  onError: (message: string | null) => void;
}) {
  const [unitId, setUnitId] = useState("");
  const [role, setRole] = useState("condomino");
  const [busy, setBusy] = useState(false);

  async function addLink() {
    if (!unitId) return;
    setBusy(true);
    onError(null);
    try {
      await scopedApi.addResidentLink(person.id, { role, unit_id: Number(unitId) });
      setUnitId("");
      onChanged();
    } catch (err) {
      onError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function removeLink(linkId: number) {
    setBusy(true);
    onError(null);
    try {
      await scopedApi.removeResidentLink(person.id, linkId);
      onChanged();
    } catch (err) {
      onError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sub-section">
      <strong>{t("residents.links")}</strong>
      <ul>
        {person.links.map((link) => (
          <li key={link.id}>
            {link.unit_code ?? link.unit_id} · {t(`residents.${link.role}`)}
            {canManage ? (
              <button type="button" onClick={() => void removeLink(link.id)}>
                {t("residents.removeLink")}
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      {canManage ? (
        <InlineForm
          onSubmit={() => void addLink()}
          busy={busy}
          submitLabel={t("residents.addLink")}
        >
          <label>
            {t("admin.roles.linkRole")}
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="condomino">{t("residents.condomino")}</option>
              <option value="inquilino">{t("residents.inquilino")}</option>
            </select>
          </label>
          <label>
            {t("vehicles.unit")}
            <select value={unitId} onChange={(e) => setUnitId(e.target.value)}>
              <option value="">{t("common.none")}</option>
              {units.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.code}
                </option>
              ))}
            </select>
          </label>
        </InlineForm>
      ) : null}
    </div>
  );
}

function AccountForm({ person, onDone }: { person: PersonView; onDone: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState(false);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await scopedApi.createAccount(person.id, { email, password });
      setCreated(true);
      onDone();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sub-section">
      <strong>{t("residents.createAccount")}</strong>
      <InlineForm onSubmit={() => void submit()} busy={busy} submitLabel={t("common.save")}>
        <Field label={t("residents.accountEmail")}>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label={t("residents.accountPassword")}>
          <input
            type="password"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>
      </InlineForm>
      {created ? <p className="ok-note">{t("residents.accountCreated")}</p> : null}
      {error ? <ErrorNote>{error}</ErrorNote> : null}
    </div>
  );
}
