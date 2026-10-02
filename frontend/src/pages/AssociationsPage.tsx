import { useState } from "react";
import { scopedApi, type AssociationView } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { perm } from "../auth/permissions";
import { t } from "../i18n";
import { ErrorNote, Loading, PageHeader, errorText, useScopedData } from "../components/ui";

export default function AssociationsPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission(perm.MEMBERSHIPS_MANAGE);
  const associations = useScopedData<AssociationView[]>(() => scopedApi.listAssociations());

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function setActive(membership: AssociationView, active: boolean) {
    setBusy(true);
    setError(null);
    try {
      await scopedApi.setAssociation(membership.user_id, active);
      associations.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(membership: AssociationView) {
    if (!window.confirm(t("admin.associations.removeConfirm"))) return;
    setBusy(true);
    setError(null);
    try {
      await scopedApi.deleteAssociation(membership.user_id);
      associations.reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title={t("admin.associations.title")} subtitle={t("admin.associations.subtitle")} />
      {error ? <ErrorNote>{error}</ErrorNote> : null}

      {associations.loading ? (
        <Loading />
      ) : associations.error ? (
        <ErrorNote>{associations.error}</ErrorNote>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("admin.associations.email")}</th>
              <th>{t("admin.associations.person")}</th>
              <th>{t("admin.roles.functions")}</th>
              <th>{t("admin.associations.active")}</th>
              {canManage ? <th>{t("common.actions")}</th> : null}
            </tr>
          </thead>
          <tbody>
            {(associations.data ?? []).map((membership) => (
              <tr key={membership.user_id}>
                <td>{membership.email ?? t("common.none")}</td>
                <td>{membership.person_name ?? t("common.none")}</td>
                <td>
                  {membership.functions.length === 0
                    ? t("common.none")
                    : membership.functions.map((code) => t(`role.${code}`)).join(", ")}
                </td>
                <td>
                  <span className={`badge ${membership.active ? "ok" : "muted"}`}>
                    {membership.active ? t("common.active") : t("common.inactive")}
                  </span>
                </td>
                {canManage ? (
                  <td>
                    <span className="row-actions">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void setActive(membership, !membership.active)}
                      >
                        {membership.active
                          ? t("admin.associations.deactivate")
                          : t("admin.associations.activate")}
                      </button>
                      <button type="button" disabled={busy} onClick={() => void remove(membership)}>
                        {t("admin.associations.remove")}
                      </button>
                    </span>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
