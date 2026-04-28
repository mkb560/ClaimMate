import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react';
import { AuthUser, getMe, loginUser, registerUser } from '@/api/client';
import { clearToken, getToken, setToken } from '@/auth/tokenStore';

type AuthContextValue = {
  token: string | null;
  user: AuthUser | null;
  booting: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [tokenState, setTokenState] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    let active = true;
    async function restore() {
      const storedToken = await getToken();
      if (!active) return;
      setTokenState(storedToken);
      if (!storedToken) {
        setBooting(false);
        return;
      }
      try {
        const restoredUser = await getMe();
        if (active) setUser(restoredUser);
      } catch {
        await clearToken();
        if (active) {
          setTokenState(null);
          setUser(null);
        }
      } finally {
        if (active) setBooting(false);
      }
    }
    restore();
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    token: tokenState,
    user,
    booting,
    async login(email: string, password: string) {
      const data = await loginUser(email, password);
      await setToken(data.access_token);
      setTokenState(data.access_token);
      setUser(data.user);
    },
    async register(email: string, password: string, displayName?: string) {
      const data = await registerUser(email, password, displayName);
      await setToken(data.access_token);
      setTokenState(data.access_token);
      setUser(data.user);
    },
    async logout() {
      await clearToken();
      setTokenState(null);
      setUser(null);
    },
  }), [booting, tokenState, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
