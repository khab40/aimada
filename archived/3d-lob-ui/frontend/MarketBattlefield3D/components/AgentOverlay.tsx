export function AgentOverlay() {
  return (
    <section className="battlefield-agent-overlay panel">
      <div className="section-heading-row">
        <h2>Agent Overlay</h2>
        <span>battlefield roles</span>
      </div>
      <div className="battlefield-agent-grid">
        <article>
          <i className="agent-dot normal" />
          <strong>Normal traders</strong>
          <span>small moving liquidity updates</span>
        </article>
        <article>
          <i className="agent-dot red" />
          <strong>Red agent</strong>
          <span>temporary wall and cancellation burst</span>
        </article>
        <article>
          <i className="agent-dot blue" />
          <strong>Blue detector</strong>
          <span>scanner beam and probability scoring</span>
        </article>
      </div>
    </section>
  );
}
