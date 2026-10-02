import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  decodeScopedToken,
  setCurrentScope,
  setScopedToken,
  setUnauthorizedHandler,
  type ScopedUnitLink,
} from "../api/client";
import { rolesGrant, type Permission } from "./permissions";

export interface CondominiumRef {
  id: number;
  name: string;
}

export interface AuthState {
  identityToken: string | null;
  scopedToken: string | null;
  condominium: CondominiumRef | null;
  roles: string[];
  unitLinks: ScopedUnitLink[];
  personId: number | null;
}

export interface AuthContextValue extends AuthState {
  signIn: (identityToken: string) => void;
  selectCondominium: (condominium: CondominiumRef, scopedToken: string) => void;
  signOut: () => void;
  /** True when the current roles grant the permission (client-side matrix). */
  hasPermission: (permission: Permission) => boolean;
}

const emptyState: AuthState = {
  identityToken: null,
  scopedToken: null,
  condominium: null,
  roles: [],
  unitLinks: [],
  personId: null,
};

const STORAGE_KEY = "condominium.auth";

function loadState(): AuthState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyState;
    const parsed = JSON.parse(raw) as Partial<AuthState>;
    return { ...emptyState, ...parsed };
  } catch {
    return emptyState;
  }
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Restore the persisted session and sync the HTTP layer synchronously: child
  // effects that issue scoped requests run BEFORE this component's own effect
  // on mount, so an effect-only sync would let them read a null `currentScope`
  // (regression: crashed on full page reloads of /app/* with a stored session).
  const [state, setState] = useState<AuthState>(() => {
    const initial = loadState();
    setScopedToken(initial.scopedToken);
    setCurrentScope(
      initial.scopedToken && initial.condominium
        ? { condominium_id: initial.condominium.id }
        : null,
    );
    return initial;
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    // Keep the HTTP layer in sync with the active scoped token/condominium.
    setScopedToken(state.scopedToken);
    setCurrentScope(
      state.scopedToken && state.condominium ? { condominium_id: state.condominium.id } : null,
    );
  }, [state]);

  const signIn = useCallback((identityToken: string) => {
    setState((prev) => ({
      ...prev,
      identityToken,
      scopedToken: null,
      condominium: null,
      roles: [],
      unitLinks: [],
      personId: null,
    }));
  }, []);

  const selectCondominium = useCallback((condominium: CondominiumRef, scopedToken: string) => {
    const claims = decodeScopedToken(scopedToken);
    setState((prev) => ({
      ...prev,
      condominium,
      scopedToken,
      roles: claims?.roles ?? [],
      unitLinks: claims?.unit_links ?? [],
      personId: claims?.person_id ?? null,
    }));
  }, []);

  const signOut = useCallback(() => {
    setState(emptyState);
  }, []);

  // Expired/no-scope scoped tokens (401) clear the session → routes redirect
  // to login/selection automatically (task 11.6).
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setState(emptyState);
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const hasPermission = useCallback(
    (permission: Permission) => rolesGrant(state.roles, permission),
    [state.roles],
  );

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, signIn, selectCondominium, signOut, hasPermission }),
    [state, signIn, selectCondominium, signOut, hasPermission],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
