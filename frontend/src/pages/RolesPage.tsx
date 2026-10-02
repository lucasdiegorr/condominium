import { useState } from "react";
import { scopedApi, type AssociationView, type RoleOverview, type UnitView, type PersonView } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { perm } from "../auth/permissions";
import { t } from "../i18n";
import { ErrorNote, Field, InlineForm, Loading, PageHeader, errorText, useScopedData } from "../components/ui";

const FUNCTION_ROLES = ["sindico", "conselho"] as const;
const LINK_ROLES = ["condomino", "inquilino"] as const;

export default function RolesPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission(perm.ROLES_MANAGE);
  const overview = useScopedData<RoleOverview>(() => scopedApi.roleOverview());
  const residents = useScopedData<PersonView[]>(
    () => (canManage ? scopedApi.listResidents() : Promise.resolve([])),
    [canManage],
  );
  const units = useScopedData<UnitView[]>(() => scopedApi.listUnits());

  const [personId, setPersonId] = useState("");
  const [unitId, setUnitId] = useState("");
  const [role, setRole] = useState<string>("condomino");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function addLink() {
    if (!personId || !unitId) {
      setError(t("common.requiredField"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await scopedApi.addUnitLink(Number(personId), { role, unit_id: Number(unitId) });
      setPersonId("");
      setUnitId("");
      overview.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function removeLink(linkId: number) {
    setBusy(true);
    setError(null);
    try {
      await scopedApi.removeUnitLink(linkId);
      overview.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const data = overview.data;

  return (
    <div>
      <PageHeader title={t("admin.roles.title")} subtitle={t("admin.roles.subtitle")} />
      {error ? <ErrorNote>{error}</ErrorNote> : null}

      {overview.loading ? (
        <Loading />
      ) : overview.error ? (
        <ErrorNote>{overview.error}</ErrorNote>
      ) : data ? (
        <>
          <section className="card">
            <h3>{t("admin.roles.memberships")}</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t("admin.associations.email")}</th>
                  <th>{t("admin.associations.person")}</th>
                  <th>{t("admin.roles.functions")}</th>
                </tr>
              </thead>
              <tbody>
                {data.memberships.map((membership) => (
                  <MembershipRow
                    key={membership.user_id}
                    membership={membership}
                    canManage={canManage}
                    onChanged={overview.reload}
                    onError={setError}
                  />
                ))}
              </tbody>
            </table>
          </section>

          <section className="card">
            <h3>{t("admin.roles.unitLinks")}</h3>
            {data.unit_links.length === 0 ? (
              <p className="muted">{t("common.none")}</p>
            ) : (
              <ul className="flat-list">
                {data.unit_links.map((link) => (
                  <li key={link.id}>
                    <span>
                      {link.person_name ?? t("common.none")} · {link.unit_code ?? link.unit_id} ·{" "}
                      {t(`role.${link.role}`)}
                    </span>
                    {canManage ? (
                      <button type="button" onClick={() => void removeLink(link.id)}>
                        {t("admin.roles.removeLink")}
                      </button>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
            {canManage ? (
              <InlineForm onSubmit={() => void addLink()} busy={busy} submitLabel={t("admin.roles.addLink")}>
                <Field label={t("admin.roles.person")}>
                  <select value={personId} onChange={(e) => setPersonId(e.target.value)}>
                    <option value="">{t("common.none")}</option>
                    {(residents.data ?? []).map((person) => (
                      <option key={person.id} value={person.id}>
                        {person.name}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={t("admin.roles.unit")}>
                  <select value={unitId} onChange={(e) => setUnitId(e.target.value)}>
                    <option value="">{t("common.none")}</option>
                    {(units.data ?? []).map((unit) => (
                      <option key={unit.id} value={unit.id}>
                        {unit.code}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={t("admin.roles.linkRole")}>
                  <select value={role} onChange={(e) => setRole(e.target.value)}>
                    {LINK_ROLES.map((value) => (
                      <option key={value} value={value}>
                        {t(`role.${value}`)}
                      </option>
                    ))}
                  </select>
                </Field>
              </InlineForm>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  );
}

function MembershipRow({
  membership,
  canManage,
  onChanged,
  onError,
}: {
  membership: AssociationView;
  canManage: boolean;
  onChanged: () => void;
  onError: (message: string | null) => void;
}) {
  const [busy, setBusy] = useState(false);

  async function toggleFunction(roleCode: string, checked: boolean) {
    const next = checked
      ? [...membership.functions, roleCode]
      : membership.functions.filter((value) => value !== roleCode);
    setBusy(true);
    onError(null);
    try {
      await scopedApi.putFunctions(membership.user_id, next);
      onChanged();
    } catch (err) {
      onError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr>
      <td>{membership.email ?? t("common.none")}</td>
      <td>{membership.person_name ?? t("common.none")}</td>
      <td>
        {canManage ? (
          <span className="check-group">
            {FUNCTION_ROLES.map((code) => (
              <label key={code} className="check">
                <input
                  type="checkbox"
                  checked={membership.functions.includes(code)}
                  disabled={busy}
                  onChange={(e) => void toggleFunction(code, e.target.checked)}
                />
                {t(`role.${code}`)}
              </label>
            ))}
          </span>
        ) : (
          <span>
            {membership.functions.length === 0
              ? t("common.none")
              : membership.functions.map((code) => t(`role.${code}`)).join(", ")}
          </span>
        )}
      </td>
    </tr>
  );
}
