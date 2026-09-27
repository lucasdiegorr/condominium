import { useAuth } from "../auth/AuthContext";
import { t } from "../i18n";

export default function HomePage() {
  const { condominium, signOut } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>{t("app.title")}</h1>
        <button type="button" onClick={signOut}>
          {t("app.logout")}
        </button>
      </header>
      <main>
        <h2>{t("home.welcome")}</h2>
        <p>
          {t("home.condominium")}: <strong>{condominium?.name}</strong>
        </p>
      </main>
    </div>
  );
}
