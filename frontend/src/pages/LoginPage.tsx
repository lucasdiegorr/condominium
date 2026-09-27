import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { identityApi } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { t } from "../i18n";

export default function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { token } = await identityApi.login(email, password);
      signIn(token);
      navigate("/select", { replace: true });
    } catch (err) {
      const status = err instanceof Error && "status" in err ? (err as { status: number }).status : 0;
      setError(status === 401 ? t("login.invalidCredentials") : t("login.genericError"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <h1>{t("app.title")}</h1>
      <h2>{t("login.title")}</h2>
      <form onSubmit={handleSubmit}>
        <label>
          {t("login.email")}
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label>
          {t("login.password")}
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button type="submit" disabled={submitting}>
          {t("login.submit")}
        </button>
      </form>
    </main>
  );
}
