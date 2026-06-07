import { useState } from 'react';

export default function SearchPanel({ airports, onRouteSelect }) {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (origin && destination) {
      onRouteSelect(origin, destination);
    }
  };

  return (
    <div className="search-panel">
      <form onSubmit={handleSubmit}>
        <div>
          <label className="field-label" htmlFor="origin-select">Origin Waypoint</label>
          <div className="select-wrapper">
            <select
              id="origin-select"
              className="dashboard-select"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
            >
              <option value="">Select Airport…</option>
              {airports.map((a) => (
                <option key={a.id} value={a.iata_code}>
                  {a.iata_code} — {a.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="field-label" htmlFor="dest-select">Target Destination</label>
          <div className="select-wrapper">
            <select
              id="dest-select"
              className="dashboard-select"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
            >
              <option value="">Select Airport…</option>
              {airports.map((a) => (
                <option key={a.id} value={a.iata_code}>
                  {a.iata_code} — {a.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button type="submit" className="trajectory-btn">
          Compute Optimal Trajectory
        </button>
      </form>
    </div>
  );
}
