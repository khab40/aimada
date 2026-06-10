import { createContext } from "react";
import type { ArenaRole, AuthSession, AuthUser } from "@/api/client";

export type AuthState = {
  busy: boolean;
  error: string | null;
  lastMessage: string | null;
  role: ArenaRole;
  session: AuthSession | null;
  user: AuthUser | null;
  loginWithGoogle: (role?: ArenaRole) => Promise<void>;
  logout: () => Promise<void>;
  saveNow: () => Promise<void>;
  setRole: (role: ArenaRole) => Promise<void>;
};

export const AuthContext = createContext<AuthState | null>(null);
