import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  completeGoogleLogin,
  getCurrentAuthSession,
  getGoogleAuthConfig,
  logoutAuthSession,
  saveAuthSession,
  updateAuthRole,
  type ArenaRole,
  type AuthSession,
  type AuthUser
} from "@/api/client";
import { AuthContext, type AuthState } from "@/auth/authState";
import { platformUserFromAuth, workspaceForUser } from "@/platform/identity";
const STORAGE_KEY = "aimada.auth.session";
const AUTO_RESTORE_GOOGLE_SESSION = false;
const GOOGLE_AUTH_TIMEOUT_MS = 120_000;
const GOOGLE_SCRIPT_TIMEOUT_MS = 15_000;

type GoogleCodeClient = {
  requestCode: () => void;
};

type GooglePopupError = {
  error?: string;
  message?: string;
  type?: string;
};

type GoogleIdentityServices = {
  accounts?: {
    oauth2?: {
      initCodeClient: (config: {
        callback: (response: { code?: string; error?: string }) => void;
        client_id: string;
        error_callback?: (response: GooglePopupError) => void;
        scope: string;
        redirect_uri?: string;
        ux_mode: "popup";
      }) => GoogleCodeClient;
    };
  };
};

declare global {
  interface Window {
    google?: GoogleIdentityServices;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [role, setLocalRole] = useState<ArenaRole>("observer");
  const [session, setSession] = useState<AuthSession | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const clearAuthError = useCallback(() => {
    setError(null);
    setLastMessage("Continuing in Local Demo.");
  }, []);

  const applyAuthResponse = useCallback((response: { access_token?: string | null; user: AuthUser; session: AuthSession; restored_history?: Record<string, unknown> | null }, fallbackMessage: string) => {
    setUser(response.user);
    setSession(response.session);
    setLocalRole(response.session.role);
    const existingAccessToken = readStoredAccessToken();
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
      access_token: response.access_token ?? existingAccessToken ?? null,
      session_id: response.session.session_id
    }));
    const restore = response.restored_history?.restore;
    if (restore && typeof restore === "object") {
      const restored = restore as { restored_artifacts?: number; restored_ticks?: number };
      setLastMessage(`Restored ${restored.restored_artifacts ?? 0} artifacts and ${restored.restored_ticks ?? 0} ticks.`);
    } else {
      setLastMessage(fallbackMessage);
    }
  }, []);

  useEffect(() => {
    if (!AUTO_RESTORE_GOOGLE_SESSION) {
      return;
    }
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return;
    }
    void (async () => {
      try {
        const parsed = JSON.parse(stored) as { access_token?: string | null; session_id?: string };
        if (!parsed.session_id) {
          return;
        }
        const response = await getCurrentAuthSession(parsed.session_id, parsed.access_token);
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
      const accessToken = readStoredAccessToken();
      void saveAuthSession(sessionId, true, accessToken).catch(() => undefined);
    }
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [session]);

  const loginWithGoogle = useCallback(async (nextRole: ArenaRole = role) => {
    setBusy(true);
    setError(null);
    try {
      const config = await getGoogleAuthConfig();
      if (config.configured && config.client_id) {
        const redirectUri = window.location.origin;
        const code = await requestGoogleAuthorizationCode(config.client_id, redirectUri);
        const response = await completeGoogleLogin(nextRole, {
          authorization_code: code,
          redirect_uri: redirectUri
        });
        applyAuthResponse(response, "Logged in with Google.");
      } else {
        setError("Google is not configured for this demo.");
        setLastMessage("Continue in Local Demo.");
      }
    } catch (nextError) {
      setError(isFetchFailure(nextError) ? "Google unavailable. Continue in Local Demo." : nextError instanceof Error ? nextError.message : "Google login failed.");
      setLastMessage("Continue in Local Demo.");
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
      const accessToken = readStoredAccessToken();
      const response = await updateAuthRole(session.session_id, nextRole, accessToken);
      applyAuthResponse(response, `Role set to ${nextRole}.`);
    } catch (nextError) {
      if (isFetchFailure(nextError)) {
        setError(null);
        setLastMessage(`Demo persona set to ${nextRole}.`);
      } else {
        setError(nextError instanceof Error ? nextError.message : "Role update failed.");
      }
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
      const accessToken = readStoredAccessToken();
      const response = await saveAuthSession(session.session_id, false, accessToken);
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
      const accessToken = readStoredAccessToken();
      await logoutAuthSession(session.session_id, accessToken);
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

  const platformUser = useMemo(() => platformUserFromAuth(user), [user]);
  const workspace = useMemo(() => workspaceForUser(platformUser), [platformUser]);

  const value = useMemo<AuthState>(() => ({
    busy,
    clearAuthError,
    error,
    lastMessage,
    loginWithGoogle,
    logout,
    platformUser,
    role,
    saveNow,
    session,
    setRole,
    user,
    workspace
  }), [busy, clearAuthError, error, lastMessage, loginWithGoogle, logout, platformUser, role, saveNow, session, setRole, user, workspace]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function readStoredAccessToken() {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (!stored) return null;
  try {
    return (JSON.parse(stored) as { access_token?: string | null }).access_token ?? null;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function isFetchFailure(error: unknown) {
  return error instanceof TypeError && error.message.toLowerCase().includes("fetch");
}

function requestGoogleAuthorizationCode(clientId: string, redirectUri: string): Promise<string> {
  return new Promise((resolve, reject) => {
    let settled = false;
    let timeoutId: number | undefined;
    const finish = (code: string | null, nextError?: Error) => {
      if (settled) {
        return;
      }
      settled = true;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
      if (nextError) {
        reject(nextError);
      } else if (code) {
        resolve(code);
      } else {
        reject(new Error("Google did not return an authorization code."));
      }
    };

    timeoutId = window.setTimeout(
      () => finish(null, new Error("Google sign-in timed out. Check popup blockers and try again.")),
      GOOGLE_AUTH_TIMEOUT_MS
    );

    void loadGoogleIdentityServices()
      .then(() => {
        const initCodeClient = window.google?.accounts?.oauth2?.initCodeClient;
        if (!initCodeClient) {
          finish(null, new Error("Google Identity Services did not initialize."));
          return;
        }
        const client = initCodeClient({
          callback: (response) => {
            if (response.error) {
              finish(null, new Error(response.error));
              return;
            }
            if (!response.code) {
              finish(null, new Error("Google did not return an authorization code."));
              return;
            }
            finish(response.code);
          },
          client_id: clientId,
          error_callback: (response) => {
            finish(null, new Error(googlePopupErrorMessage(response)));
          },
          redirect_uri: redirectUri,
          scope: "openid email profile",
          ux_mode: "popup"
        });
        try {
          client.requestCode();
        } catch (nextError) {
          finish(null, nextError instanceof Error ? nextError : new Error("Google sign-in popup could not open."));
        }
      })
      .catch((nextError) => {
        finish(null, nextError instanceof Error ? nextError : new Error("Google Identity Services failed to load."));
      });
  });
}

function loadGoogleIdentityServices(): Promise<void> {
  if (window.google?.accounts?.oauth2) {
    return Promise.resolve();
  }
  const existing = document.querySelector<HTMLScriptElement>('script[src="https://accounts.google.com/gsi/client"]');
  if (existing) {
    return waitForGoogleIdentityServices(existing);
  }
  const script = document.createElement("script");
  script.async = true;
  script.defer = true;
  script.src = "https://accounts.google.com/gsi/client";
  document.head.appendChild(script);
  return waitForGoogleIdentityServices(script);
}

function waitForGoogleIdentityServices(script: HTMLScriptElement): Promise<void> {
  return new Promise((resolve, reject) => {
    let settled = false;
    let intervalId: number | undefined;
    let timeoutId: number | undefined;
    let onError: () => void = () => undefined;
    const finish = (nextError?: Error) => {
      if (settled) {
        return;
      }
      settled = true;
      if (intervalId !== undefined) {
        window.clearInterval(intervalId);
      }
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
      script.removeEventListener("error", onError);
      if (nextError) {
        reject(nextError);
      } else {
        resolve();
      }
    };
    onError = () => finish(new Error("Failed to load Google Identity Services."));
    intervalId = window.setInterval(() => {
      if (window.google?.accounts?.oauth2) {
        finish();
      }
    }, 50);
    timeoutId = window.setTimeout(
      () => finish(new Error("Timed out loading Google Identity Services.")),
      GOOGLE_SCRIPT_TIMEOUT_MS
    );
    script.addEventListener("error", onError, { once: true });
    if (window.google?.accounts?.oauth2) {
      finish();
    }
  });
}

function googlePopupErrorMessage(response: GooglePopupError): string {
  const code = response.type || response.error;
  if (code === "popup_closed") {
    return "Google sign-in popup was closed before it finished.";
  }
  if (code === "popup_failed_to_open") {
    return "Google sign-in popup could not open. Check popup blockers and try again.";
  }
  if (response.message?.trim()) {
    return response.message.trim();
  }
  return "Google sign-in did not complete.";
}
