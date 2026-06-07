import React, { useState } from 'react';

export default function SearchPanel({ airports, onRouteSelect }) {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');

  const handleSearch = () => {
    if (origin && destination && origin !== destination) {
      onRouteSelect(origin, destination);
    } else {
      alert("Please select both a valid origin and destination.");
    }
  };

  return (
    <div style={{
      position: 'absolute', 
      top: '80px', 
      left: '20px', 
      zIndex: 1000, 
      background: 'white', 
      padding: '20px', 
      borderRadius: '8px',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)', 
      width: '320px',
      fontFamily: 'system-ui'
    }}>
      <h2 style={{ margin: '0 0 15px 0', fontSize: '1.2rem', color: '#1a1a1a' }}>Route Parameters</h2>
      
      <div style={{ marginBottom: '12px' }}>
        <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '5px', fontWeight: 'bold', color: '#555' }}>ORIGIN</label>
        <select 
          style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }} 
          value={origin} 
          onChange={(e) => setOrigin(e.target.value)}
        >
          <option value="">Select Departure...</option>
          {airports.map(a => <option key={`orig-${a.iata_code}`} value={a.iata_code}>{a.name} ({a.iata_code})</option>)}
        </select>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '5px', fontWeight: 'bold', color: '#555' }}>DESTINATION</label>
        <select 
          style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }} 
          value={destination} 
          onChange={(e) => setDestination(e.target.value)}
        >
          <option value="">Select Arrival...</option>
          {airports.map(a => <option key={`dest-${a.iata_code}`} value={a.iata_code}>{a.name} ({a.iata_code})</option>)}
        </select>
      </div>

      <button 
        onClick={handleSearch}
        style={{ 
          width: '100%', padding: '12px', background: '#0066ff', color: 'white', 
          border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' 
        }}
      >
        Analyze Route Risk
      </button>
    </div>
  );
}