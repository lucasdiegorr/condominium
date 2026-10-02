import { useAuth } from "../auth/AuthContext";
import { t } from "../i18n";

export default function HomePage() {
  const { condominium, roles } = useAuth();

  return (
    <div>
      <div className="page-header">
        <h2>{t("home.welcome")}</h2>
        <p className="muted">
          {t("home.condominium")}: <strong>{condominium?.name}</strong>
        </p>
      </div>
      <section className="card">
        <h3>{t("home.yourRoles")}</h3>
        {roles.length === 0 ? (
          <p className="muted">{t("common.none")}</p>
        ) : (
          <span className="check-group">
            {roles.map((role) => (
              <span key={role} className="badge">
                {t(`role.${role}`)}
              </span>
            ))}
          </span>
        )}
      </section>
    </div>
  );
}
