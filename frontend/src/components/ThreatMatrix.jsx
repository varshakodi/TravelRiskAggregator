// Per-corridor threat composition, computed by the backend from the zones the
// direct path actually crosses (severity-weighted shares). One hue: the row
// label carries identity, the bar carries magnitude.
export default function ThreatMatrix({ breakdown }) {
  return (
    <div className="card">
      <h4 className="card-title">Corridor threat profile</h4>
      {!breakdown?.length ? (
        <div className="matrix-empty">No active threats intersect this corridor.</div>
      ) : (
        breakdown.map((row) => (
          <div className="bar-row" key={row.category}>
            <span className="bar-label">{row.category}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${row.share_pct}%` }} />
            </div>
            <span className="bar-value">{row.share_pct}%</span>
          </div>
        ))
      )}
    </div>
  );
}
