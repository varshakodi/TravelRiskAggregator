import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Popup, CircleMarker, Polyline, GeoJSON } from 'react-leaflet';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import SearchPanel from './components/SearchPanel';

const DefaultIcon = L.icon({
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

export default function App() {
  const [dangerZones, setDangerZones] = useState([]);
  const [airports, setAirports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeRouteParams, setActiveRouteParams] = useState(null);
  const [routeData, setRouteData] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiBriefing, setAiBriefing] = useState(null);
  const [isAiThinking, setIsAiThinking] = useState(false);

  useEffect(() => {
    Promise.all([
      axios.get('http://localhost:8000/api/airports'),
      axios.get('http://localhost:8000/api/danger-zones'),
    ])
      .then(([airportsRes, zonesRes]) => {
        if (airportsRes.data?.airports) setAirports(airportsRes.data.airports);
        if (zonesRes.data?.zones) setDangerZones(zonesRes.data.zones);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!activeRouteParams) return;

    setIsAnalyzing(true);
    setRouteData(null);
    setAiBriefing(null);

    const timer = setTimeout(() => {
      axios
        .post('http://localhost:8000/api/route/calculate', activeRouteParams)
        .then((response) => {
          setRouteData(response.data);

          setIsAiThinking(true);
          axios
            .post('http://localhost:8000/api/route/briefing', {
              origin: activeRouteParams.origin,
              destination: activeRouteParams.destination,
              standard_route: response.data.standard_route.path,
              safe_route: response.data.safe_route.path,
              is_rerouted: response.data.is_rerouted,
            })
            .then((aiRes) => setAiBriefing(aiRes.data.briefing))
            .catch((err) => console.error('AI Error:', err))
            .finally(() => setIsAiThinking(false));
        })
        .catch(() => alert('No clear path mapped.'))
        .finally(() => setIsAnalyzing(false));
    }, 800);

    return () => clearTimeout(timer);
  }, [activeRouteParams]);

  if (loading) {
    return <div className="app-loading">Initializing threat matrix…</div>;
  }

  const getCoordinates = (pathArray) =>
    pathArray
      ?.map((iata) => {
        const apt = airports.find((a) => a.iata_code === iata);
        return apt ? [apt.lat, apt.lon] : null;
      })
      .filter((c) => c !== null) || [];

  const standardPathCoords = routeData ? getCoordinates(routeData.standard_route?.path) : [];
  const safePathCoords = routeData ? getCoordinates(routeData.safe_route?.path) : [];

  return (
    <div className="app-container" style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden' }}>
      <aside className="sidebar" style={{ width: '380px', height: '100vh', overflowY: 'auto', background: '#141414', borderRight: '1px solid #333' }}>
        <header className="sidebar-header" style={{ padding: '20px', borderBottom: '1px solid #333' }}>
          <h1 style={{ margin: 0, fontSize: '1.2rem', color: '#fff' }}>
            Risk Aggregator <span className="version" style={{ color: '#3b82f6' }}>v2.5</span>
          </h1>
          <p style={{ margin: '5px 0 0', fontSize: '0.8rem', color: '#888' }}>Global Threat &amp; Routing Engine</p>
        </header>

        <div className="sidebar-body" style={{ padding: '20px' }}>
          {airports.length > 0 && (
            <SearchPanel
              airports={airports}
              onRouteSelect={(orig, dest) => setActiveRouteParams({ origin: orig, destination: dest })}
            />
          )}

          {isAnalyzing && (
            <div className="analyzing-block" style={{ marginTop: '30px' }}>
              <div className="skeleton-pulse" style={{ height: '20px', width: '60%', marginBottom: '10px', background: '#2a2a2a', borderRadius: '4px' }} />
              <div className="skeleton-pulse" style={{ height: '80px', width: '100%', marginBottom: '10px', background: '#2a2a2a', borderRadius: '4px' }} />
              <div className="skeleton-pulse" style={{ height: '40px', width: '80%', background: '#2a2a2a', borderRadius: '4px' }} />
            </div>
          )}

          {routeData && !isAnalyzing && (
            <div className="route-intelligence" style={{ marginTop: '30px', color: '#fff' }}>
              <h3 className="section-title" style={{ borderBottom: '1px solid #333', paddingBottom: '10px', marginBottom: '15px' }}>Route Intelligence</h3>

              {routeData.is_rerouted ? (
                <div className="status-card status-card--danger" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', padding: '15px', borderRadius: '6px', marginBottom: '20px' }}>
                  <div className="status-label" style={{ color: '#ef4444', fontWeight: 'bold', marginBottom: '5px' }}>⚠️ Reroute Executed</div>
                  <div style={{ fontSize: '0.85rem' }}>
                    Direct path via {routeData.standard_route.path.join(' → ')} intercepted active
                    threat zones. Rerouting via {routeData.safe_route.path.join(' → ')}.
                  </div>
                </div>
              ) : (
                <div className="status-card status-card--clear" style={{ background: 'rgba(34, 197, 94, 0.1)', border: '1px solid #22c55e', padding: '15px', borderRadius: '6px', marginBottom: '20px' }}>
                  <div className="status-label" style={{ color: '#22c55e', fontWeight: 'bold' }}>✅ Route Clear</div>
                </div>
              )}

              <div className="glass-card glass-card--accent" style={{ background: '#111', border: '1px solid #444', padding: '15px', borderRadius: '6px', marginBottom: '20px', borderLeft: '3px solid #b700ff' }}>
                <div className="glass-card-title" style={{ color: '#b700ff', fontWeight: 'bold', fontSize: '0.85rem', marginBottom: '8px' }}>🤖 AI Copilot Briefing</div>
                {isAiThinking ? (
                  <div className="skeleton-pulse" style={{ height: '40px', width: '100%', background: '#2a2a2a', borderRadius: '4px' }} />
                ) : (
                  <div className="glass-card-body" style={{ fontSize: '0.85rem', color: '#ccc', lineHeight: '1.4' }}>
                    {aiBriefing || 'Standing by for route vectors.'}
                  </div>
                )}
              </div>

              <h4 className="matrix-title" style={{ color: '#aaa', marginBottom: '10px', fontSize: '0.9rem' }}>Threat Matrix (Simulated)</h4>
              <div className="glass-card" style={{ background: '#1e1e1e', padding: '15px', borderRadius: '6px', fontSize: '0.85rem' }}>
                <div className="threat-row" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span>Geopolitical Risk</span>
                  <span className="threat-value--warn" style={{ color: '#f59e0b' }}>72%</span>
                </div>
                <div className="threat-row" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span>Aviation Weather</span>
                  <span className="threat-value--low" style={{ color: '#22c55e' }}>12%</span>
                </div>
                <div className="threat-row" style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Civil Unrest</span>
                  <span className="threat-value--low" style={{ color: '#22c55e' }}>16%</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* FIXED MAP WRAPPER: Ensures Leaflet doesn't crash to 0px height */}
      <div className="map-wrapper" style={{ flex: 1, position: 'relative', height: '100vh', background: '#0a0a0a' }}>
        <MapContainer 
          center={[20.0, 30.0]} 
          zoom={3} 
          minZoom={2} 
          maxBounds={[[-85, -180], [85, 180]]} // Safe bounds that prevent the map from crashing
          maxBoundsViscosity={1.0} 
          style={{ width: '100%', height: '100vh' }} // Forces Leaflet canvas to render at full height
        >
          <TileLayer 
            url="https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png" 
            noWrap={true} 
          />

          {dangerZones.map((zone) => (
            <GeoJSON
              key={zone.id}
              data={zone.boundary}
              style={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.25, weight: 2 }}
            >
              <Popup>
                <div className="popup-title" style={{ color: '#ef4444', fontWeight: 'bold' }}>🚨 HIGH RISK ZONE</div>
                <hr className="popup-divider" style={{ borderTop: '1px solid #ccc', margin: '8px 0' }} />
                <div className="popup-meta" style={{ fontSize: '0.9rem', fontFamily: 'system-ui' }}>
                  <b>Source:</b> {zone.source}
                  <br />
                  <b>Status:</b> Active
                  <div className="popup-desc" style={{ marginTop: '5px', color: '#555' }}>{zone.description}</div>
                </div>
              </Popup>
            </GeoJSON>
          ))}

          {standardPathCoords.length > 0 && routeData?.is_rerouted && (
            <Polyline
              positions={standardPathCoords}
              color="#ef4444"
              weight={3}
              dashArray="5, 10"
              opacity={0.4}
            />
          )}

          {safePathCoords.length > 0 && (
            <Polyline
              positions={safePathCoords}
              color="#3b82f6"
              weight={4}
              opacity={0.9}
              pathOptions={{ className: 'animated-path' }}
            />
          )}

          {airports.map((airport) => (
            <CircleMarker
              key={airport.id}
              center={[airport.lat, airport.lon]}
              radius={airport.risk_level === 'High' ? 30 : 15}
              pathOptions={{
                color: airport.risk_level === 'High' ? '#ef4444' : '#22c55e',
                fillOpacity: 0.15,
              }}
            >
              <Popup>
                <b className="popup-airport-name">{airport.name}</b>
                <br />
                <span className="popup-meta">Status: {airport.risk_level} Risk</span>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>

        <div className="risk-legend" style={{ position: 'absolute', bottom: '20px', right: '20px', zIndex: 1000, background: 'rgba(20,20,20,0.9)', padding: '15px', borderRadius: '8px', border: '1px solid #333', fontSize: '0.8rem', color: '#fff', fontFamily: 'system-ui' }}>
          <strong style={{ display: 'block', marginBottom: '10px' }}>Risk Legend</strong>
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
            <span className="legend-swatch legend-swatch--zone" style={{ width: '12px', height: '12px', background: '#ef4444', display: 'inline-block', marginRight: '8px', opacity: 0.5 }} />
            Conflict Zone (No-Fly)
          </div>
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
            <span className="legend-swatch legend-swatch--blocked" style={{ width: '12px', height: '3px', background: '#ef4444', display: 'inline-block', marginRight: '8px' }} />
            Blocked Direct Path
          </div>
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center' }}>
            <span className="legend-swatch legend-swatch--route" style={{ width: '12px', height: '3px', background: '#3b82f6', display: 'inline-block', marginRight: '8px' }} />
            Active Radar Route
          </div>
        </div>
      </div>
    </div>
  );
}