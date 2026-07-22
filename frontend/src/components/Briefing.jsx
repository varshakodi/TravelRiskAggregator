const OFFLINE_PREFIX = '[SIMULATED AI]: ';

// The backend labels offline-generated briefings with a text prefix; we keep
// that honesty but present it as a quiet chip instead of shouting in the copy.
export default function Briefing({ briefing, thinking }) {
  const offline = briefing?.startsWith(OFFLINE_PREFIX);
  const text = offline ? briefing.slice(OFFLINE_PREFIX.length) : briefing;

  return (
    <div className="card">
      <h4 className="card-title">
        Route briefing
        <span className="chip">{offline ? 'offline model' : 'AI'}</span>
      </h4>
      {thinking ? (
        <div className="skeleton-pulse" style={{ height: 44 }} />
      ) : (
        <div className="briefing-body">{text || 'Select a route to generate a briefing.'}</div>
      )}
    </div>
  );
}
