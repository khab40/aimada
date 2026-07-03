import type { AuthUser } from "@/api/client";

export type PlatformRole = "admin" | "analyst" | "reviewer" | "viewer";

export type PlatformUser = {
  authProvider: string;
  avatar?: string | null;
  email: string;
  id: string;
  name: string;
};

export type PlatformWorkspace = {
  defaultRole: PlatformRole;
  id: string;
  members: PlatformUser[];
  name: string;
};

export type CaseStatus = "open" | "investigating" | "review" | "approved" | "closed";

export type CaseOwnership = {
  assignedAnalyst: PlatformUser;
  lastUpdatedBy: PlatformUser;
  owner: PlatformUser;
  reviewers: PlatformUser[];
  status: CaseStatus;
};

export type AuditTrailEntry = {
  actionType:
    | "AI explanation requested"
    | "case status changed"
    | "detector alert created"
    | "evidence reviewed"
    | "report exported"
    | "reviewer approved"
    | "scenario started";
  description: string;
  targetEntity: string;
  timestamp: string;
  user: PlatformUser;
};

export const demoUser: PlatformUser = {
  authProvider: "local-demo",
  avatar: null,
  email: "demo.analyst@aimada.local",
  id: "demo-analyst",
  name: "Demo Analyst"
};

const demoReviewer: PlatformUser = {
  authProvider: "local-demo",
  avatar: null,
  email: "reviewer@aimada.local",
  id: "demo-reviewer",
  name: "Demo Reviewer"
};

export const demoWorkspace: PlatformWorkspace = {
  defaultRole: "analyst",
  id: "aimada-surveillance-desk",
  members: [demoUser, demoReviewer],
  name: "Aimada Surveillance Desk"
};

export function platformUserFromAuth(user: AuthUser | null): PlatformUser {
  if (!user) return demoUser;
  return {
    authProvider: user.auth_provider ?? user.provider ?? "google",
    avatar: user.avatar_url ?? null,
    email: user.email,
    id: user.id ?? user.user_id,
    name: user.name || user.email
  };
}

export function workspaceForUser(user: PlatformUser): PlatformWorkspace {
  if (user.id === demoUser.id) return demoWorkspace;
  return {
    defaultRole: "analyst",
    id: "workspace-aimada-surveillance",
    members: [user, demoReviewer],
    name: "Aimada Surveillance Desk"
  };
}

export function createCaseOwnership(user: PlatformUser, workspace: PlatformWorkspace, status: CaseStatus): CaseOwnership {
  const reviewer = workspace.members.find((member) => member.id !== user.id) ?? user;
  return {
    assignedAnalyst: user,
    lastUpdatedBy: user,
    owner: user,
    reviewers: [reviewer],
    status
  };
}

export function createAuditTrail(user: PlatformUser, targetEntity: string, status: CaseStatus): AuditTrailEntry[] {
  const timestamp = new Date().toISOString();
  const entries: AuditTrailEntry[] = [
    {
      actionType: "scenario started",
      description: "Synthetic market scenario associated with this investigation.",
      targetEntity,
      timestamp,
      user
    },
    {
      actionType: "detector alert created",
      description: "Detector evidence attached to investigation case.",
      targetEntity,
      timestamp,
      user
    },
    {
      actionType: "AI explanation requested",
      description: "Investigation summary prepared for analyst review.",
      targetEntity,
      timestamp,
      user
    },
    {
      actionType: "evidence reviewed",
      description: "Evidence artifacts and replay context marked ready for review.",
      targetEntity,
      timestamp,
      user
    },
    {
      actionType: "report exported",
      description: "Compliance report metadata prepared for export.",
      targetEntity,
      timestamp,
      user
    },
    {
      actionType: "case status changed",
      description: `Case moved to ${status}.`,
      targetEntity,
      timestamp,
      user
    }
  ];
  if (status === "approved" || status === "closed") {
    entries.push({
      actionType: "reviewer approved",
      description: "Reviewer approval placeholder recorded for multiuser workflow.",
      targetEntity,
      timestamp,
      user
    });
  }
  return entries;
}
