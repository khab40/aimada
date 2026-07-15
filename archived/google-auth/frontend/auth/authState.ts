import { createContext } from "react";
import type { ArenaRole, AuthSession, AuthUser } from "@/api/client";
import type { PlatformUser, PlatformWorkspace } from "@/platform/identity";

export type AuthState = {
  busy: boolean;
  clearAuthError: () => void;
  error: string | null;
  lastMessage: string | null;
  role: ArenaRole;
  session: AuthSession | null;
  user: AuthUser | null;
  platformUser: PlatformUser;
  workspace: PlatformWorkspace;
  loginWithGoogle: (role?: ArenaRole) => Promise<void>;
  logout: () => Promise<void>;
  saveNow: () => Promise<void>;
  setRole: (role: ArenaRole) => Promise<void>;
};

export const AuthContext = createContext<AuthState | null>(null);
