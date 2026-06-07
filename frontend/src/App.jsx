import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker, Polyline, GeoJSON } from 'react-leaflet';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

import SearchPanel from './components/SearchPanel';

let DefaultIcon = L.icon({
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

function App() {
  const [dangerZones, setDangerZones] = useState([]);
  const [airports, setAirports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeRouteParams, setActiveRouteParams] = useState(null);
  const [calculatedRoute, setCalculatedRoute] = useState(null);

  // 1. Initial Data Engine Load
  useEffect(() => {
    Promise.all([
      axios.get('http://localhost:8000/api/airports'),
      axios.get('http://localhost:8000/api/danger-zones')
    ])
    .then(([airportsResponse, zonesResponse]) => {
      if (airportsResponse.data && airportsResponse.data.airports) {
        setAirports(airportsResponse.data.airports);
      }
      if (zonesResponse.data && zonesResponse.data.zones) {
        setDangerZones(zonesResponse.data.zones);
      }
    })
    .catch(err => {
      console.error("Initialization network connection failed:", err);
    })
    .finally(() => {
      setLoading(false);
    });
  }, []);

  // 2. Automated Routing Engine Hook
  useEffect(() => {
    if (activeRouteParams) {
      axios.post('http://localhost:8000/api/route/calculate', {
        origin: activeRouteParams.origin,
        destination: activeRouteParams.destination
      })
      .then(response => {
        setCalculatedRoute(response.data);
      })
      .catch(err => {
        console.error("Path calculation engine failed:", err);
        alert("No clear path could be mapped out between these coordinates.");
      });
    }
  }, [activeRouteParams]);

  if (loading) {
    return (
      <div style={{ padding: '40px', fontFamily: 'system-ui', background: '#111', color: '#fff', height: '100vh' }}>
        <h2>Initializing Global Risk Aggregator Engine...</h2>
        <p style={{ color: '#888' }}>Assembling live aviation spatial networks and mapping conflict indexes...</p>
      </div>
    );
  }

  // Convert Dijkstra node response arrays to Leaflet map point coordinate sets
  const flightPathCoordinates = calculatedRoute && calculatedRoute.path
    ? calculatedRoute.path.map(iata => {
        const airport = airports.find(a => a.iata_code === iata);
        return airport ? [airport.lat, airport.lon] : null;
      }).filter(coord => coord !== null)
    : [];

  const visibleAirports = calculatedRoute && calculatedRoute.path
    ? airports.filter(a => calculatedRoute.path.includes(a.iata_code))
    : airports;

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', position: 'relative', background: '#121212' }}>
      <header style={{ padding: '15px 20px', background: '#1a1a1a', color: 'white', borderBottom: '3px solid #0066ff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0, fontSize: '1.4rem', fontFamily: 'system-ui', fontWeight: '700', letterSpacing: '-0.5px' }}>
          Travel Risk Aggregator <span style={{ fontSize: '0.8rem', color: '#0066ff', background: 'rgba(0,102,255,0.15)', padding: '3px 8px', borderRadius: '12px', marginLeft: '10px' }}>v2.0-Spatial</span>
        </h1>
      </header>
      
      {airports.length > 0 && (
        <SearchPanel 
          airports={airports} 
          onRouteSelect={(orig, dest) => setActiveRouteParams({ origin: orig, destination: dest })} 
        />
      )}

      <div style={{ flex: 1, width: '100%', height: '100%', zIndex: 1 }}>
        <MapContainer center={[19.0, 66.0]} zoom={4} style={{ width: '100%', height: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CartoDB</a>'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png"
            noWrap={true}
          />

          {/* A. Geopolitical Danger Polygons */}
          {dangerZones.map((zone) => (
            <GeoJSON 
              key={zone.id} 
              data={zone.boundary} 
              style={{
                color: '#ff3333',
                weight: 2,
                fillColor: '#ff3333',
                fillOpacity: 0.25,
                dashArray: '6, 6'
              }}
            >
              <Popup>
                <div style={{ fontFamily: 'system-ui' }}>
                  <strong style={{ color: '#ff3333', fontSize: '1rem' }}>🚨 ACTIVE AIRSPACE WAR ZONE</strong><br/>
                  <hr style={{ margin: '5px 0', border: '0', borderTop: '1px solid #eee' }}/>
                  <b>Source Ingestion:</b> {zone.source}<br/>
                  <b>Threat intel:</b> {zone.description}
                </div>
              </Popup>
            </GeoJSON>
          ))}

          {/* B. Dynamic Air Waypoint Pathing */}
          {flightPathCoordinates.length > 0 && (
            <Polyline 
              positions={flightPathCoordinates} 
              color="#0066ff" 
              weight={4} 
              opacity={0.9}
            />
          )}

          {/* C. Terminal Node Infrastructure */}
          {visibleAirports.map((airport) => {
            const isHighRisk = airport.risk_level === 'High';
            const riskColor = isHighRisk ? '#ff3333' : (airport.risk_level === 'Medium' ? '#ffaa00' : '#33cc33');

            return (
              <div key={airport.id}>
                <CircleMarker
                  center={[airport.lat, airport.lon]}
                  pathOptions={{ color: riskColor, fillColor: riskColor, fillOpacity: 0.15 }}
                  radius={isHighRisk ? 35 : 20}
                />
                <Marker position={[airport.lat, airport.lon]}>
                  <Popup>
                    <div style={{ fontFamily: 'system-ui' }}>
                      <div style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{airport.name} ({airport.iata_code})</div>
                      <div style={{ 
                        background: riskColor, color: 'white', padding: '3px 8px', 
                        borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', margin: '6px 0', fontSize: '0.8rem'
                      }}>
                        {airport.risk_level} Perimeter Risk
                      </div>
                      <div style={{ fontSize: '0.9rem', color: '#555' }}>
                        {airport.risk_description}
                      </div>
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