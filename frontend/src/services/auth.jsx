import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokenStore } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(tokenStore.get()));

  useEffect(() => {
    if (!tokenStore.get()) return;
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener("roppo:logout", onLogout);
    return () => window.removeEventListener("roppo:logout", onLogout);
  }, []);

  const signIn = useCallback(async (mode, body) => {
    const res = mode === "demo" ? await api.demo() : mode === "register" ? await api.register(body) : await api.login(body);
    tokenStore.set(res.access_token);
    setUser(res.user);
    return res.user;
  }, []);

  const signOut = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, setUser, loading, signIn, signOut }}>{children}</AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
