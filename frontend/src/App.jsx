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
    <div className="app-container">
      <aside className="sidebar">
        <header className="sidebar-header">
          <h1>
            Risk Aggregator <span className="version">v2.5</span>
          </h1>
          <p>Global Threat &amp; Routing Engine</p>
        </header>

        <div className="sidebar-body">
          {airports.length > 0 && (
            <SearchPanel
              airports={airports}
              onRouteSelect={(orig, dest) => setActiveRouteParams({ origin: orig, destination: dest })}
            />
          )}

          {isAnalyzing && (
            <div className="analyzing-block">
              <div className="skeleton-pulse" style={{ height: '20px', width: '60%', marginBottom: '10px' }} />
              <div className="skeleton-pulse" style={{ height: '80px', width: '100%', marginBottom: '10px' }} />
              <div className="skeleton-pulse" style={{ height: '40px', width: '80%' }} />
            </div>
          )}

          {routeData && !isAnalyzing && (
            <div className="route-intelligence">
              <h3 className="section-title">Route Intelligence</h3>

              {routeData.is_rerouted ? (
                <div className="status-card status-card--danger">
                  <div className="status-label">Reroute Executed</div>
                  <div>
                    Direct path via {routeData.standard_route.path.join(' → ')} intercepted active
                    threat zones. Rerouting via {routeData.safe_route.path.join(' → ')}.
                  </div>
                </div>
              ) : (
                <div className="status-card status-card--clear">
                  <div className="status-label">Route Clear</div>
                </div>
              )}

              <div className="glass-card glass-card--accent">
                <div className="glass-card-title">AI Copilot Briefing</div>
                {isAiThinking ? (
                  <div className="skeleton-pulse" style={{ height: '40px', width: '100%' }} />
                ) : (
                  <div className="glass-card-body">
                    {aiBriefing || 'Standing by for route vectors.'}
                  </div>
                )}
              </div>

              <h4 className="matrix-title">Threat Matrix (Simulated)</h4>
              <div className="glass-card">
                <div className="threat-row">
                  <span>Geopolitical Risk</span>
                  <span className="threat-value--warn">72%</span>
                </div>
                <div className="threat-row">
                  <span>Aviation Weather</span>
                  <span className="threat-value--low">12%</span>
                </div>
                <div className="threat-row">
                  <span>Civil Unrest</span>
                  <span className="threat-value--low">16%</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>

      <div className="map-wrapper">
        <MapContainer
          center={[19.0, 66.0]}
          zoom={5}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png"
            noWrap
          />

          {dangerZones.map((zone) => (
            <GeoJSON
              key={zone.id}
              data={zone.boundary}
              style={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.25, weight: 2 }}
            >
              <Popup>
                <div className="popup-title">High Risk Zone</div>
                <hr className="popup-divider" />
                <div className="popup-meta">
                  <b>Source:</b> {zone.source}
                  <br />
                  <b>Status:</b> Active
                  <div className="popup-desc">{zone.description}</div>
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
                <span className="popup-airport-name">{airport.name}</span>
                <br />
                <span className="popup-meta">Status: {airport.risk_level} Risk</span>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>

        <div className="risk-legend">
          <strong>Risk Legend</strong>
          <div className="legend-item">
            <span className="legend-swatch legend-swatch--zone" />
            Conflict Zone (No-Fly)
          </div>
          <div className="legend-item">
            <span className="legend-swatch legend-swatch--blocked" />
            Blocked Direct Path
          </div>
          <div className="legend-item">
            <span className="legend-swatch legend-swatch--route" />
            Active Radar Route
          </div>
        </div>
      </div>
    </div>
  );
}
