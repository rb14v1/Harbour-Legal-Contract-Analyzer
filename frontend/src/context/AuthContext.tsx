import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, clearTokens, setTokens } from "../api/client";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadMe() {
    try {
      const response = await api.get<User>("/auth/me/");
      setUser(response.data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (localStorage.getItem("access_token")) {
      loadMe();
    } else {
      setLoading(false);
    }
  }, []);

  async function login(email: string, password: string) {
    const response = await api.post("/auth/login/", { email, password });
    setTokens(response.data.access, response.data.refresh);
    setUser(response.data.user);
  }

  async function register(email: string, password: string, fullName: string) {
    await api.post("/auth/register/", { email, password, full_name: fullName });
    await login(email, password);
  }

  function logout() {
    clearTokens();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
