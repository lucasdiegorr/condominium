import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { perm } from "../auth/permissions";
import { setLocale, t, useLocale, type Locale } from "../i18n";

/** Application shell: header with locale switch + role-aware sidebar navigation. */
export default function AppLayout() {
  const { identityToken, condominium, roles, hasPermission, signOut } = useAuth();
  const navigate = useNavigate();
  const locale = useLocale();

  const navItems = [
    { to: "/app", label: t("navigation.home"), show: true, end: true },
    { to: "/app/units", label: t("navigation.units"), show: hasPermission(perm.UNITS_READ) },
    { to: "/app/residents", label: t("navigation.residents"), show: hasPermission(perm.RESIDENTS_READ) },
    {
      to: "/app/vehicles",
      label: t("navigation.vehicles"),
      show: hasPermission(perm.VEHICLES_READ) || hasPermission(perm.VEHICLES_SELF),
    },
    {
      to: "/app/pets",
      label: t("navigation.pets"),
      show: hasPermission(perm.PETS_READ) || hasPermission(perm.PETS_SELF),
    },
    { to: "/app/common-areas", label: t("navigation.commonAreas"), show: hasPermission(perm.COMMON_AREAS_READ) },
    {
      to: "/app/bookings",
      label: t("navigation.bookings"),
      show: hasPermission(perm.BOOKINGS_READ) || hasPermission(perm.BOOKINGS_SELF),
    },
    {
      to: "/app/financial",
      label: t("navigation.financial"),
      show: hasPermission(perm.FINANCIAL_READ) || hasPermission(perm.FINANCIAL_READ_OWN_UNIT),
    },
  ];

  const adminItems = [
    { to: "/app/roles", label: t("navigation.roles"), show: hasPermission(perm.ROLES_MANAGE) },
    { to: "/app/associations", label: t("navigation.associations"), show: hasPermission(perm.MEMBERSHIPS_MANAGE) },
    {
      to: "/app/condominiums",
      label: t("navigation.condominiums"),
      // Global admin can manage condos before any scope exists.
      show: identityToken !== null,
    },
  ];

  function switchLocale(next: Locale) {
    setLocale(next);
  }

  return (
    <div className="app-frame">
      <header className="app-bar">
        <div className="app-bar-brand">
          <strong>{t("app.title")}</strong>
          <span className="muted">
            {condominium?.name ?? t("home.noScope")} ·{" "}
            {roles.map((role) => t(`role.${role}`)).join(", ")}
          </span>
        </div>
        <div className="app-bar-actions">
          <div className="locale-switch" role="group" aria-label="Language">
            <button
              type="button"
              className={locale === "en" ? "is-active" : ""}
              onClick={() => switchLocale("en")}
            >
              EN
            </button>
            <button
              type="button"
              className={locale === "pt-BR" ? "is-active" : ""}
              onClick={() => switchLocale("pt-BR")}
            >
              PT
            </button>
          </div>
          <button type="button" onClick={() => navigate("/select", { replace: true })}>
            {t("app.switchCondo")}
          </button>
          <button type="button" onClick={signOut}>
            {t("app.logout")}
          </button>
        </div>
      </header>
      <div className="app-body">
        <nav className="app-nav">
          <NavLinkSection items={navItems} showLabel={true} />
          {adminItems.some((item) => item.show) ? (
            <>
              <h3 className="nav-section-title">{t("navigation.roles")}</h3>
              <NavLinkSection items={adminItems} />
            </>
          ) : null}
        </nav>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function NavLinkSection({
  items,
  showLabel,
}: {
  items: { to: string; label: string; show: boolean; end?: boolean }[];
  showLabel?: boolean;
}) {
  const visible = items.filter((item) => item.show);
  if (visible.length === 0) return null;
  return (
    <ul className="nav-list">
      {showLabel ? (
        <li className="nav-section-label">
          <span>{t("home.quickAccess")}</span>
        </li>
      ) : null}
      {visible.map((item) => (
        <li key={item.to}>
          <NavLink to={item.to} end={item.end}>
            {item.label}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}
