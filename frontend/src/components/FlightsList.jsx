const STATUS_DOT = {
  active: 'var(--status-good)',
  scheduled: 'var(--accent)',
  landed: 'var(--ink-3)',
  cancelled: 'var(--status-critical)',
  diverted: 'var(--status-warn)',
};

const t = (iso) =>
  iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '–';

export default function FlightsList({ flights }) {
  if (!flights?.length) return null;
  return (
    <div className="card">
      <h4 className="card-title">Scheduled on this route<span className="chip">{flights.length}</span></h4>
      {flights.slice(0, 6).map((f, i) => (
        <div className="flight-row" key={`${f.flight_number}-${i}`}>
          <div className="flight-main">
            <span className="flight-number">{f.flight_number || '—'}</span>
            <span className="flight-airline">{f.airline}</span>
          </div>
          <span className="flight-times">
            {t(f.dep_scheduled)}–{t(f.arr_scheduled)}
            {(f.dep_delay > 0 || f.arr_delay > 0) && (
              <span className="flight-delay"> +{f.dep_delay || f.arr_delay}m</span>
            )}
          </span>
          <span className="flight-status">
            <span className="dot" style={{ background: STATUS_DOT[f.status] || 'var(--ink-3)' }} />
            {f.status}
          </span>
        </div>
      ))}
    </div>
  );
}
