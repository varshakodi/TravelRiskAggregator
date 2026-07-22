import { useState } from 'react';

export default function SearchPanel({ airports, onRouteSelect, busy }) {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');

  const same = origin && origin === destination;
  const ready = origin && destination && !same && !busy;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (ready) onRouteSelect(origin, destination);
  };

  const options = airports.map((a) => (
    <option key={a.id} value={a.iata_code}>
      {a.iata_code} — {a.name}
    </option>
  ));

  return (
    <div className="search-panel">
      <form onSubmit={handleSubmit}>
        <div>
          <label className="field-label" htmlFor="origin-select">Origin</label>
          <div className="select-wrapper">
            <select
              id="origin-select"
              className="dashboard-select"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
            >
              <option value="">Select airport…</option>
              {options}
            </select>
          </div>
        </div>

        <div>
          <label className="field-label" htmlFor="dest-select">Destination</label>
          <div className="select-wrapper">
            <select
              id="dest-select"
              className="dashboard-select"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
            >
              <option value="">Select airport…</option>
              {options}
            </select>
          </div>
        </div>

        {same && <p className="field-error">Origin and destination must differ.</p>}

        <button type="submit" className="compute-btn" disabled={!ready}>
          {busy ? 'Computing…' : 'Compute route'}
        </button>
      </form>
    </div>
  );
}
