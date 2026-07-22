import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Popup, CircleMarker, Polyline, GeoJSON } from 'react-leaflet';
import { api } from './api';
import 'leaflet/dist/leaflet.css';

import SearchPanel from './components/SearchPanel';
import RouteStatus from './components/RouteStatus';
import ThreatMatrix from './components/ThreatMatrix';
import Briefing from './components/Briefing';
import FlightsList from './components/FlightsList';
import MapLegend from './components/MapLegend';

// Leaflet path colors mirror the CSS tokens (Leaflet needs literal values).
const COLOR = {
  accent: '#9085e9',
  good: '#0ca30c',
  warn: '#fab219',
  critical: '#d03b3b',
};

const airportColor = (risk) =>
  risk === 'High' ? COLOR.critical : risk === 'Medium' ? COLOR.warn : COLOR.good;

export default function App() {
  const [dangerZones, setDangerZones] = useState([]);
  const [airports, setAirports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeRouteParams, setActiveRouteParams] = useState(null);
  const [routeData, setRouteData] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiBriefing, setAiBriefing] = useState(null);
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [routeFlights, setRouteFlights] = useState([]);
  const [loadError, setLoadError] = useState(null);

  // Initial data load
  useEffect(() => {
    Promise.all([api.get('/api/airports'), api.get('/api/danger-zones')])
      .then(([airportsRes, zonesRes]) => {
        if (airportsRes.data?.airports) setAirports(airportsRes.data.airports);
        if (zonesRes.data?.zones) setDangerZones(zonesRes.data.zones);
      })
      .catch(() => setLoadError('Could not reach the routing engine. Refresh to retry.'))
      .finally(() => setLoading(false));
  }, []);

  // Route computation
  useEffect(() => {
    if (!activeRouteParams) return;

    setIsAnalyzing(true);
    setRouteData(null);
    setAiBriefing(null);
    setRouteFlights([]);

    api
      .post('/api/route/calculate', activeRouteParams)
      .then((response) => {
        setRouteData(response.data);

        api
          .get(`/api/live-flights/${activeRouteParams.origin}/${activeRouteParams.destination}`)
          .then((res) => { if (res.data?.flights) setRouteFlights(res.data.flights); })
          .catch(() => {});

        // The server recomputes the route and owns every fact that reaches
        // the AI prompt — the client only says which route to brief.
        setIsAiThinking(true);
        api
          .post('/api/route/briefing', {
            origin: activeRouteParams.origin,
            destination: activeRouteParams.destination,
          })
          .then((aiRes) => setAiBriefing(aiRes.data.briefing))
          .catch(() => setAiBriefing(null))
          .finally(() => setIsAiThinking(false));
      })
      .catch(() => setRouteData(null))
      .finally(() => setIsAnalyzing(false));
  }, [activeRouteParams]);

  if (loading) {
    return <div className="app-loading">Loading airspace data…</div>;
  }

  const coords = (route) =>
    route?.path
      ?.map((iata) => {
        const apt = airports.find((a) => a.iata_code === iata);
        return apt ? [apt.lat, apt.lon] : null;
      })
      .filter(Boolean) || [];

  const standardPathCoords = coords(routeData?.standard_route);
  const safePathCoords = coords(routeData?.safe_route);
  const showBlocked = routeData && routeData.status !== 'CLEAR';

  return (
    <div className="app-container">
      <aside className="sidebar">
        <header className="sidebar-header">
          <div>
            <h1>Risk Aggregator</h1>
            <p className="subtitle">Global threat &amp; routing engine</p>
          </div>
          <span className="chip">
            <span className="dot" />
            {dangerZones.length} active zones
          </span>
        </header>

        <div className="sidebar-body">
          {airports.length > 0 && (
            <SearchPanel
              airports={airports}
              busy={isAnalyzing}
              onRouteSelect={(orig, dest) => setActiveRouteParams({ origin: orig, destination: dest })}
            />
          )}

          {loadError && <div className="hint-card">{loadError}</div>}

          {!routeData && !isAnalyzing && !loadError && (
            <div className="hint-card">
              Select an origin and destination to compute a hazard-aware route.
              The engine avoids live SIGMET weather cells, conflict airspace and
              seismic zones, and reports exactly what it routed around.
            </div>
          )}

          {isAnalyzing && (
            <div className="route-intelligence">
              <div className="skeleton-pulse" style={{ height: 84, marginBottom: 12 }} />
              <div className="skeleton-pulse" style={{ height: 120 }} />
            </div>
          )}

          {routeData && !isAnalyzing && (
            <div className="route-intelligence">
              <RouteStatus routeData={routeData} />
              <Briefing briefing={aiBriefing} thinking={isAiThinking} />
              <ThreatMatrix breakdown={routeData.threat_breakdown} />
              <FlightsList flights={routeFlights} />
            </div>
          )}
        </div>
      </aside>

      <div className="map-wrapper">
        <MapContainer
          center={[25.0, 70.0]}
          zoom={3}
          minZoom={2}
          maxBounds={[[-85, -180], [85, 180]]}
          maxBoundsViscosity={1.0}
          zoomControl={true}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png"
            noWrap={true}
          />

          {dangerZones.map((zone) => (
            <GeoJSON
              key={zone.id}
              data={zone.boundary}
              style={{ color: COLOR.critical, fillColor: COLOR.critical, fillOpacity: 0.10, weight: 1 }}
            >
              <Popup>
                <div className="popup-title">{zone.source}</div>
                <div className="popup-meta">Severity {zone.severity}/10</div>
                <div className="popup-desc">{zone.description}</div>
              </Popup>
            </GeoJSON>
          ))}

          {showBlocked && standardPathCoords.length > 0 && (
            <Polyline
              positions={standardPathCoords}
              color={COLOR.critical}
              weight={1.5}
              dashArray="5, 9"
              opacity={0.55}
            />
          )}

          {safePathCoords.length > 0 && (
            <Polyline
              positions={safePathCoords}
              color={COLOR.accent}
              weight={2.5}
              opacity={0.95}
              pathOptions={{ className: 'animated-path' }}
            />
          )}

          {airports.map((airport) => (
            <CircleMarker
              key={airport.id}
              center={[airport.lat, airport.lon]}
              radius={airport.risk_level === 'High' ? 6 : 4}
              pathOptions={{
                color: airportColor(airport.risk_level),
                fillColor: airportColor(airport.risk_level),
                fillOpacity: 0.25,
                weight: 1.5,
              }}
            >
              <Popup>
                <div className="popup-title">{airport.name}</div>
                <div className="popup-meta">{airport.iata_code} · {airport.risk_level} risk</div>
                {airport.risk_description && (
                  <div className="popup-desc">{airport.risk_description}</div>
                )}
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>

        <MapLegend />
      </div>
    </div>
  );
}
