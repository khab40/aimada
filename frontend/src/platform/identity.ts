import type { AuthUser } from "@/api/client";
import type { ArenaRole } from "@/api/client";

export type PlatformRole = "admin" | "analyst" | "reviewer" | "viewer";
export type WorkspaceOrganizationType = "bank" | "exchange" | "regulator" | "demo";
export type CaseStatus = "open" | "investigating" | "pending_review" | "approved" | "closed";
export type AuditActionType =
  | "AI explanation requested"
  | "case status changed"
  | "detector alert created"
  | "evidence reviewed"
  | "report exported"
  | "reviewer approved"
  | "scenario started";

export type PlatformUser = {
  authProvider: string;
  avatar?: string | null;
  email: string;
  id: string;
  name: string;
};

export type PlatformWorkspace = {
  created_at: string;
  defaultRole: PlatformRole;
  id: string;
  members: PlatformUser[];
  name: string;
  organization_type: WorkspaceOrganizationType;
};

export type CaseOwnership = {
  assignedAnalyst: PlatformUser;
  assigned_analyst_id: string;
  created_by: string;
  lastUpdatedBy: PlatformUser;
  owner: PlatformUser;
  owner_user_id: string;
  reviewer_user_id: string;
  reviewers: PlatformUser[];
  status: CaseStatus;
  updated_at: string;
  updated_by: string;
  workspace_id: string;
};

export type AuditTrailEvent = {
  action_type: AuditActionType;
  description: string;
  id: string;
  role: PlatformRole;
  target_id: string;
  target_type: "case" | "incident" | "report" | "scenario" | "evidence";
  timestamp: string;
  user_id: string;
  user_name: string;
};

export type AuditTrailEntry = AuditTrailEvent & {
  actionType: AuditActionType;
  targetEntity: string;
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
  created_at: "2026-07-03T00:00:00.000Z",
  defaultRole: "analyst",
  id: "aimada-surveillance-desk",
  members: [demoUser, demoReviewer],
  name: "Aimada Surveillance Desk",
  organization_type: "demo"
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
    created_at: "2026-07-03T00:00:00.000Z",
    defaultRole: "analyst",
    id: "workspace-aimada-surveillance",
    members: [user, demoReviewer],
    name: "Aimada Surveillance Desk",
    organization_type: "bank"
  };
}

export function productRoleForArenaRole(role: ArenaRole): PlatformRole {
  if (role === "judge") return "reviewer";
  if (role === "observer") return "viewer";
  return "analyst";
}

export function productRoleLabel(role: ArenaRole) {
  if (role === "attacker") return "Analyst / red-team";
  return productRoleForArenaRole(role).replace("_", " ");
}

export function createCaseOwnership(user: PlatformUser, workspace: PlatformWorkspace, status: CaseStatus): CaseOwnership {
  const reviewer = workspace.members.find((member) => member.id !== user.id) ?? user;
  const timestamp = new Date().toISOString();
  return {
    assignedAnalyst: user,
    assigned_analyst_id: user.id,
    created_by: user.id,
    lastUpdatedBy: user,
    owner: user,
    owner_user_id: user.id,
    reviewer_user_id: reviewer.id,
    reviewers: [reviewer],
    status,
    updated_at: timestamp,
    updated_by: user.id,
    workspace_id: workspace.id
  };
}

export function createAuditTrail(user: PlatformUser, targetEntity: string, status: CaseStatus, actorRole: PlatformRole = "analyst"): AuditTrailEntry[] {
  const timestamp = new Date().toISOString();
  const role: PlatformRole = user.id === demoReviewer.id ? "reviewer" : actorRole;
  function event(actionType: AuditActionType, description: string, index: number): AuditTrailEntry {
    return {
      action_type: actionType,
      actionType,
      description,
      id: `${targetEntity}-${index}-${actionType.toLowerCase().replaceAll(" ", "-")}`,
      role,
      target_id: targetEntity,
      target_type: actionType === "scenario started" ? "scenario" : actionType === "report exported" ? "report" : "case",
      targetEntity,
      timestamp,
      user,
      user_id: user.id,
      user_name: user.name
    };
  }
  const entries: AuditTrailEntry[] = [
    event("scenario started", "Synthetic market scenario associated with this investigation.", 1),
    event("detector alert created", "Detector evidence attached to investigation case.", 2),
    event("AI explanation requested", "Investigation summary prepared for analyst review.", 3),
    event("evidence reviewed", "Evidence artifacts and replay context marked ready for review.", 4),
    event("report exported", "Compliance report metadata prepared for export.", 5),
    event("case status changed", `Case moved to ${status}.`, 6)
  ];
  if (status === "approved" || status === "closed") {
    entries.push(event("reviewer approved", "Reviewer approval placeholder recorded for multiuser workflow.", 7));
  }
  return entries;
}
