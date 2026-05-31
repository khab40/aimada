export function AgentFeed({ events = [] }: { events?: unknown[] }) {
  return (
    <section>
      <h2>Agent Feed</h2>
      <pre>{JSON.stringify(events.slice(-10), null, 2)}</pre>
    </section>
  );
}
