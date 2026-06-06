import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker, Polyline } from 'react-leaflet';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

function App() {
  const [airports, setAirports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get('http://localhost:8000/api/airports')
      .then(response => {
        setAirports(response.data.airports);
        setLoading(false);
      })
      .catch(err => {
        console.error("Backend connection failed:", err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;

  // Extract just the coordinates to draw our flight path line
  const flightPathCoordinates = airports.map(airport => [airport.lat, airport.lon]);

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ padding: '15px 20px', background: '#1a1a1a', color: 'white', borderBottom: '3px solid #0066ff' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontFamily: 'system-ui' }}>Travel Risk Aggregator</h1>
      </header>
      
      <div style={{ flex: 1, width: '100%', height: '100%' }}>
        <MapContainer center={[19.0, 66.0]} zoom={4} style={{ width: '100%', height: '100%' }}>
          
          {/* Swapped to a clean, modern, English-only map style */}
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CartoDB</a>'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
            noWrap={true} 
          />

          {/* Draw the dashed flight path between all airports in the database */}
          {airports.length > 1 && (
            <Polyline 
              positions={flightPathCoordinates} 
              color="#0066ff" 
              weight={3} 
              dashArray="10, 10" 
              opacity={0.6}
            />
          )}

          {airports.map((airport) => {
            const isHighRisk = airport.risk_level === 'High';
            const riskColor = isHighRisk ? '#ff3333' : '#33cc33';

            return (
              <div key={airport.id}>
                <CircleMarker
                  center={[airport.lat, airport.lon]}
                  pathOptions={{ color: riskColor, fillColor: riskColor, fillOpacity: 0.3 }}
                  radius={isHighRisk ? 40 : 20}
                />
                
                <Marker position={[airport.lat, airport.lon]}>
                  <Popup>
                    <div style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{airport.name}</div>
                    <div style={{ color: '#555', marginBottom: '8px' }}>Code: {airport.iata_code}</div>
                    
                    <div style={{ 
                      background: riskColor, 
                      color: 'white', 
                      padding: '4px 8px', 
                      borderRadius: '4px',
                      fontWeight: 'bold',
                      display: 'inline-block',
                      marginBottom: '8px'
                    }}>
                      {airport.risk_level} Risk
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#333' }}>
                      {airport.risk_description}
                    </div>
                  </Popup>
                </Marker>
              </div>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}

export default App;