import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  completeGoogleLogin,
  getCurrentAuthSession,
  logoutAuthSession,
  saveAuthSession,
  updateAuthRole,
  type ArenaRole,
  type AuthSession,
  type AuthUser
} from "@/api/client";
import { AuthContext, type AuthState } from "@/auth/authState";
const STORAGE_KEY = "aimada.auth.session";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [role, setLocalRole] = useState<ArenaRole>("observer");
  const [session, setSession] = useState<AuthSession | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);

  const applyAuthResponse = useCallback((response: { user: AuthUser; session: AuthSession; restored_history?: Record<string, unknown> | null }, fallbackMessage: string) => {
    setUser(response.user);
    setSession(response.session);
    setLocalRole(response.session.role);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ session_id: response.session.session_id }));
    const restore = response.restored_history?.restore;
    if (restore && typeof restore === "object") {
      const restored = restore as { restored_artifacts?: number; restored_ticks?: number };
      setLastMessage(`Restored ${restored.restored_artifacts ?? 0} artifacts and ${restored.restored_ticks ?? 0} ticks.`);
    } else {
      setLastMessage(fallbackMessage);
    }
  }, []);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return;
    }
    void (async () => {
      try {
        const parsed = JSON.parse(stored) as { session_id?: string };
        if (!parsed.session_id) {
          return;
        }
        const response = await getCurrentAuthSession(parsed.session_id);
        applyAuthResponse(response, "Restored login session.");
      } catch {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    })();
  }, [applyAuthResponse]);

  useEffect(() => {
    if (!session) {
      return;
    }
    const sessionId = session.session_id;
    function handleBeforeUnload() {
      void saveAuthSession(sessionId, true).catch(() => undefined);
    }
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [session]);

  const loginWithGoogle = useCallback(async (nextRole: ArenaRole = role) => {
    setBusy(true);
    setError(null);
    try {
      const response = await completeGoogleLogin(nextRole);
      applyAuthResponse(response, "Logged in with Google stub. Real Google verification can be attached at the backend seam.");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  }, [applyAuthResponse, role]);

  const setRole = useCallback(async (nextRole: ArenaRole) => {
    setLocalRole(nextRole);
    if (!session) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await updateAuthRole(session.session_id, nextRole);
      applyAuthResponse(response, `Role set to ${nextRole}.`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Role update failed.");
    } finally {
      setBusy(false);
    }
  }, [applyAuthResponse, session]);

  const saveNow = useCallback(async () => {
    if (!session) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await saveAuthSession(session.session_id);
      const snapshot = response.snapshot;
      const history = snapshot && typeof snapshot === "object" ? (snapshot.history as { tick_count?: number; artifact_count?: number } | undefined) : undefined;
      setLastMessage(`Saved ${history?.artifact_count ?? 0} artifacts and ${history?.tick_count ?? 0} ticks.`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Session save failed.");
    } finally {
      setBusy(false);
    }
  }, [session]);

  const logout = useCallback(async () => {
    if (!session) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await logoutAuthSession(session.session_id);
      setLastMessage("History saved on logout.");
      setSession(null);
      setUser(null);
      window.localStorage.removeItem(STORAGE_KEY);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Logout failed.");
    } finally {
      setBusy(false);
    }
  }, [session]);

  const value = useMemo<AuthState>(() => ({
    busy,
    error,
    lastMessage,
    loginWithGoogle,
    logout,
    role,
    saveNow,
    session,
    setRole,
    user
  }), [busy, error, lastMessage, loginWithGoogle, logout, role, saveNow, session, setRole, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
