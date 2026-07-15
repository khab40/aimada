import { createAuditTrail, demoUser, type AuditTrailEntry, type CaseStatus } from "@/platform/identity";

type AuditTrailCardProps = {
  events?: AuditTrailEntry[];
  status?: CaseStatus;
  targetId?: string;
  title?: string;
};

export function AuditTrailCard({
  events,
  status = "investigating",
  targetId = "demo-investigation",
  title = "Audit Trail"
}: AuditTrailCardProps) {
  const rows = sortEvents(events?.length ? events : createAuditTrail(demoUser, targetId, status));

  return (
    <section className="audit-trail-card" aria-label={title}>
      <div className="audit-trail-card-header">
        <span>{title}</span>
        <strong>{rows.length} events</strong>
      </div>
      <div className="audit-trail-list">
        {rows.map((entry) => (
          <article key={entry.id}>
            <time dateTime={entry.timestamp}>{formatAuditTimestamp(entry.timestamp)}</time>
            <div>
              <strong>{entry.action_type}</strong>
              <span>{entry.user_name} · {entry.role} · {entry.target_type}:{entry.target_id}</span>
              <p>{entry.description}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function sortEvents(events: AuditTrailEntry[]) {
  return [...events].sort((left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp));
}

function formatAuditTimestamp(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short"
  }).format(parsed);
}
