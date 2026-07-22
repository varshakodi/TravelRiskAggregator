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

const statusColor = (status) => {
  switch (status) {
    case 'active':    return '#22c55e';
    case 'landed':    return '#6b7280';
    case 'cancelled': return '#ef4444';
    case 'diverted':  return '#f59e0b';
    default:          return '#60a5fa';
  }
};

export default function App() {
  const [dangerZones, setDangerZones]         = useState([]);
  const [airports, setAirports]               = useState([]);
  const [loading, setLoading]                 = useState(true);
  const [activeRouteParams, setActiveRouteParams] = useState(null);
  const [routeData, setRouteData]             = useState(null);
  const [isAnalyzing, setIsAnalyzing]         = useState(false);
  const [aiBriefing, setAiBriefing]           = useState(null);
  const [isAiThinking, setIsAiThinking]       = useState(false);
  const [routeFlights, setRouteFlights]       = useState([]);

  // Initial data load
  useEffect(() => {
    Promise.all([
      axios.get('http://localhost:8000/api/airports'),
      axios.get('http://localhost:8000/api/danger-zones'),
    ])
      .then(([airportsRes, zonesRes]) => {
        if (airportsRes.data?.airports) setAirports(airportsRes.data.airports);
        if (zonesRes.data?.zones)       setDangerZones(zonesRes.data.zones);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  // Route computation
  useEffect(() => {
    if (!activeRouteParams) return;

    setIsAnalyzing(true);
    setRouteData(null);
    setAiBriefing(null);
    setRouteFlights([]);

    const timer = setTimeout(() => {
      axios
        .post('http://localhost:8000/api/route/calculate', activeRouteParams)
        .then((response) => {
          setRouteData(response.data);

          // Fetch real scheduled flights for this route from AviationStack
          axios
            .get(`http://localhost:8000/api/live-flights/${activeRouteParams.origin}/${activeRouteParams.destination}`)
            .then((res) => { if (res.data?.flights) setRouteFlights(res.data.flights); })
            .catch(() => {});

          setIsAiThinking(true);
          axios
            .post('http://localhost:8000/api/route/briefing', {
              origin:         activeRouteParams.origin,
              destination:    activeRouteParams.destination,
              standard_route: response.data.standard_route.path,
              safe_route:     response.data.safe_route.path,
              status:         response.data.status,
              // REROUTED: the safe route's zones_crossed is empty by definition
              // (that's what makes it safe) — the briefing needs what the
              // *blocked* direct route hit instead. NO_SAFE_PATH: the top-level
              // field already reflects what the lowest-risk option still crosses.
              zones_crossed:  response.data.status === 'REROUTED'
                ? response.data.standard_route.zones_crossed
                : response.data.zones_crossed,
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
  const safePathCoords     = routeData ? getCoordinates(routeData.safe_route?.path)     : [];

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden' }}>

      {/* ── SIDEBAR ── */}
      <aside style={{ width: '360px', height: '100vh', overflowY: 'auto', background: '#0d0d0d', borderRight: '1px solid #222', flexShrink: 0 }}>

        <header style={{ padding: '20px', borderBottom: '1px solid #222' }}>
          <h1 style={{ margin: 0, fontSize: '1.15rem', color: '#fff', letterSpacing: '-0.02em' }}>
            Risk Aggregator <span style={{ color: '#3b82f6' }}>v2.5</span>
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.75rem', color: '#555' }}>Global Threat &amp; Routing Engine</p>
        </header>

        <div style={{ padding: '20px' }}>

          {/* Route selector */}
          {airports.length > 0 && (
            <SearchPanel
              airports={airports}
              onRouteSelect={(orig, dest) => setActiveRouteParams({ origin: orig, destination: dest })}
            />
          )}

          {/* Skeleton while computing */}
          {isAnalyzing && (
            <div style={{ marginTop: '28px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {[60, 100, 80].map((w, i) => (
                <div key={i} className="skeleton-pulse" style={{ height: i === 1 ? '80px' : '20px', width: `${w}%`, background: '#1e1e1e', borderRadius: '6px' }} />
              ))}
            </div>
          )}

          {/* Route intelligence */}
          {routeData && !isAnalyzing && (
            <div style={{ marginTop: '28px', color: '#fff' }}>
              <h3 style={{ fontSize: '0.7rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#555', marginBottom: '14px' }}>Route Intelligence</h3>

              {/* Status card */}
              {routeData.status === 'NO_SAFE_PATH' ? (
                <div style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.4)', padding: '14px', borderRadius: '8px', marginBottom: '16px' }}>
                  <div style={{ color: '#f59e0b', fontWeight: '700', fontSize: '0.85rem', marginBottom: '6px' }}>⚠️ No Fully Safe Route</div>
                  <div style={{ fontSize: '0.8rem', color: '#fcd34d', lineHeight: '1.5' }}>
                    Every available path crosses active threat airspace.<br />
                    Lowest-risk option: <span style={{ fontFamily: 'monospace', color: '#fff' }}>{routeData.safe_route.path.join(' → ')}</span>
                  </div>
                  {routeData.zones_crossed?.length > 0 && (
                    <div style={{ marginTop: '8px', fontSize: '0.75rem', color: '#d97706' }}>
                      Crosses: {routeData.zones_crossed.join('; ')}
                    </div>
                  )}
                </div>
              ) : routeData.status === 'REROUTED' ? (
                <div style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.4)', padding: '14px', borderRadius: '8px', marginBottom: '16px' }}>
                  <div style={{ color: '#ef4444', fontWeight: '700', fontSize: '0.85rem', marginBottom: '6px' }}>⚠️ Reroute Executed</div>
                  <div style={{ fontSize: '0.8rem', color: '#fca5a5', lineHeight: '1.5' }}>
                    Direct path <span style={{ fontFamily: 'monospace' }}>{routeData.standard_route.path.join(' → ')}</span> intercepted active threat zones.<br />
                    Rerouting via <span style={{ fontFamily: 'monospace', color: '#fff' }}>{routeData.safe_route.path.join(' → ')}</span>
                  </div>
                  {routeData.safe_route.total_distance_km && (
                    <div style={{ marginTop: '8px', fontSize: '0.75rem', color: '#6b7280' }}>
                      Safe route distance: {routeData.safe_route.total_distance_km.toLocaleString()} km
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.35)', padding: '14px', borderRadius: '8px', marginBottom: '16px' }}>
                  <div style={{ color: '#22c55e', fontWeight: '700', fontSize: '0.85rem' }}>✅ Route Clear</div>
                  <div style={{ fontSize: '0.8rem', color: '#86efac', marginTop: '4px' }}>
                    <span style={{ fontFamily: 'monospace' }}>{routeData.standard_route.path.join(' → ')}</span>
                  </div>
                  {routeData.standard_route.total_distance_km && (
                    <div style={{ marginTop: '6px', fontSize: '0.75rem', color: '#6b7280' }}>
                      Distance: {routeData.standard_route.total_distance_km.toLocaleString()} km
                    </div>
                  )}
                </div>
              )}

              {/* AI Copilot Briefing */}
              <div style={{ background: '#111', border: '1px solid #2a2a2a', borderLeft: '3px solid #7c3aed', padding: '14px', borderRadius: '8px', marginBottom: '16px' }}>
                <div style={{ color: '#a78bfa', fontWeight: '700', fontSize: '0.78rem', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>🤖 AI Copilot Briefing</div>
                {isAiThinking ? (
                  <div className="skeleton-pulse" style={{ height: '48px', background: '#1e1e1e', borderRadius: '4px' }} />
                ) : (
                  <div style={{ fontSize: '0.82rem', color: '#c4b5fd', lineHeight: '1.55' }}>
                    {aiBriefing || 'Standing by for route vectors.'}
                  </div>
                )}
              </div>

              {/* Real flights on this route (AviationStack) */}
              {routeFlights.length > 0 && (
                <div style={{ marginBottom: '16px' }}>
                  <h4 style={{ fontSize: '0.7rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#555', marginBottom: '10px' }}>
                    Real Flights on Route ({routeFlights.length})
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {routeFlights.slice(0, 6).map((f, i) => (
                      <div key={i} style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '10px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                          <span style={{ color: '#38bdf8', fontWeight: '700', fontFamily: 'monospace', fontSize: '0.85rem' }}>{f.flight_number}</span>
                          <span style={{
                            color: statusColor(f.status),
                            background: `${statusColor(f.status)}15`,
                            border: `1px solid ${statusColor(f.status)}40`,
                            padding: '1px 7px', borderRadius: '4px',
                            fontSize: '0.62rem', textTransform: 'uppercase', fontWeight: '700',
                          }}>{f.status}</span>
                        </div>
                        <div style={{ color: '#94a3b8', fontSize: '0.78rem', marginBottom: '3px' }}>{f.airline}</div>
                        <div style={{ color: '#475569', fontSize: '0.73rem' }}>
                          {f.dep_scheduled ? new Date(f.dep_scheduled).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '–'}
                          {' → '}
                          {f.arr_scheduled ? new Date(f.arr_scheduled).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '–'}
                        </div>
                        {(f.dep_delay > 0 || f.arr_delay > 0) && (
                          <div style={{ marginTop: '4px', color: '#f59e0b', fontSize: '0.7rem' }}>
                            ⏱ {f.dep_delay ? `DEP +${f.dep_delay}min` : ''}{f.arr_delay ? ` ARR +${f.arr_delay}min` : ''}
                          </div>
                        )}
                        {f.gate && (
                          <div style={{ marginTop: '2px', color: '#334155', fontSize: '0.7rem' }}>Gate {f.gate}{f.terminal ? ` · T${f.terminal}` : ''}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Threat matrix */}
              <div>
                <h4 style={{ fontSize: '0.7rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#555', marginBottom: '10px' }}>Threat Matrix</h4>
                <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: '8px', padding: '14px', fontSize: '0.82rem' }}>
                  {[['Geopolitical Risk', '72%', '#f59e0b'], ['Aviation Weather', '12%', '#22c55e'], ['Civil Unrest', '16%', '#22c55e']].map(([label, val, color]) => (
                    <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: label === 'Civil Unrest' ? 0 : '10px' }}>
                      <span style={{ color: '#888' }}>{label}</span>
                      <span style={{ color, fontWeight: '700' }}>{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* ── MAP ── */}
      <div style={{ flex: 1, position: 'relative', height: '100vh' }}>
        <MapContainer
          center={[25.0, 70.0]}
          zoom={3}
          minZoom={2}
          maxBounds={[[-85, -180], [85, 180]]}
          maxBoundsViscosity={1.0}
          style={{ width: '100%', height: '100vh' }}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png"
            noWrap={true}
          />

          {/* Danger zones */}
          {dangerZones.map((zone) => (
            <GeoJSON
              key={zone.id}
              data={zone.boundary}
              style={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.18, weight: 1.5 }}
            >
              <Popup>
                <div style={{ fontFamily: 'system-ui' }}>
                  <div style={{ color: '#ef4444', fontWeight: 'bold', marginBottom: '4px' }}>🚨 {zone.source}</div>
                  <div style={{ fontSize: '0.85rem', color: '#555' }}>{zone.description}</div>
                </div>
              </Popup>
            </GeoJSON>
          ))}

          {/* Blocked direct path (red dashed) */}
          {standardPathCoords.length > 0 && routeData?.status && routeData.status !== 'CLEAR' && (
            <Polyline positions={standardPathCoords} color="#ef4444" weight={2} dashArray="6, 10" opacity={0.45} />
          )}

          {/* Safe rerouted path (blue solid) */}
          {safePathCoords.length > 0 && (
            <Polyline positions={safePathCoords} color="#3b82f6" weight={3.5} opacity={0.9} pathOptions={{ className: 'animated-path' }} />
          )}

          {/* Airports */}
          {airports.map((airport) => (
            <CircleMarker
              key={airport.id}
              center={[airport.lat, airport.lon]}
              radius={airport.risk_level === 'High' ? 10 : 6}
              pathOptions={{
                color: airport.risk_level === 'High' ? '#ef4444' : airport.risk_level === 'Medium' ? '#f59e0b' : '#22c55e',
                fillOpacity: 0.2,
                weight: 1.5,
              }}
            >
              <Popup>
                <div style={{ fontFamily: 'system-ui' }}>
                  <b>{airport.name}</b><br />
                  <span style={{ fontSize: '0.85rem', color: '#555' }}>{airport.iata_code} · {airport.risk_level} Risk</span>
                  {airport.risk_description && (
                    <div style={{ marginTop: '4px', fontSize: '0.8rem', color: '#888' }}>{airport.risk_description}</div>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>

        {/* Legend */}
        <div style={{ position: 'absolute', bottom: '20px', right: '20px', zIndex: 1000, background: 'rgba(13,13,13,0.92)', padding: '14px', borderRadius: '8px', border: '1px solid #222', fontSize: '0.75rem', color: '#fff', fontFamily: 'system-ui', backdropFilter: 'blur(6px)' }}>
          <strong style={{ display: 'block', marginBottom: '10px', color: '#aaa', textTransform: 'uppercase', fontSize: '0.65rem', letterSpacing: '0.08em' }}>Legend</strong>
          {[
            [<span style={{ width: '12px', height: '12px', background: '#ef4444', display: 'inline-block', opacity: 0.5 }} />, 'Conflict / No-Fly Zone'],
            [<span style={{ width: '12px', height: '3px', background: '#ef4444', display: 'inline-block' }} />, 'Blocked Direct Path'],
            [<span style={{ width: '12px', height: '3px', background: '#3b82f6', display: 'inline-block' }} />, 'Safe Rerouted Path'],
            [<span style={{ width: '10px', height: '10px', borderRadius: '50%', border: '1.5px solid #22c55e', display: 'inline-block' }} />, 'Airport (Low Risk)'],
            [<span style={{ width: '10px', height: '10px', borderRadius: '50%', border: '1.5px solid #ef4444', display: 'inline-block' }} />, 'Airport (High Risk)'],
          ].map(([icon, label], i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: i < 4 ? '6px' : 0 }}>
              {icon}
              <span style={{ color: '#aaa' }}>{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}