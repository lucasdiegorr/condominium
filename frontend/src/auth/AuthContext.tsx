import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export interface CondominiumRef {
  id: string;
  name: string;
}

export interface AuthState {
  identityToken: string | null;
  scopedToken: string | null;
  condominium: CondominiumRef | null;
}

export interface AuthContextValue extends AuthState {
  signIn: (identityToken: string) => void;
  selectCondominium: (condominium: CondominiumRef, scopedToken: string) => void;
  signOut: () => void;
}

const emptyState: AuthState = {
  identityToken: null,
  scopedToken: null,
  condominium: null,
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
  const [state, setState] = useState<AuthState>(loadState);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state]);

  const signIn = useCallback((identityToken: string) => {
    setState((prev) => ({ ...prev, identityToken, scopedToken: null, condominium: null }));
  }, []);

  const selectCondominium = useCallback(
    (condominium: CondominiumRef, scopedToken: string) => {
      setState((prev) => ({ ...prev, condominium, scopedToken }));
    },
    [],
  );

  const signOut = useCallback(() => {
    setState(emptyState);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, signIn, selectCondominium, signOut }),
    [state, signIn, selectCondominium, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
