/** HTTP client for the Condominium Management API. */

const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }
}

interface RequestOptions extends RequestInit {
  authToken?: string;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (options.authToken) {
    headers.set("Authorization", `Bearer ${options.authToken}`);
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail: unknown = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (body.detail !== undefined) detail = body.detail;
    } catch {
      // Non-JSON error body — keep status text.
    }
    throw new ApiError(response.status, String(detail));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Identity-token scoped calls (login, condominium listing/selection). */
export const identityApi = {
  login(email: string, password: string): Promise<{ token: string }> {
    return request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },
  listCondominiums(identityToken: string): Promise<{ id: string; name: string }[]> {
    return request("/auth/condominiums", { authToken: identityToken });
  },
  selectCondominium(
    identityToken: string,
    condominiumId: string,
  ): Promise<{ token: string }> {
    return request(`/auth/condominiums/${condominiumId}/select`, {
      method: "POST",
      authToken: identityToken,
    });
  },
};

/** Scoped-token calls (all domain data) — added per capability chapter. */
export const scopedApi = {
  // Filled in as domain endpoints land.
};

export default request;
