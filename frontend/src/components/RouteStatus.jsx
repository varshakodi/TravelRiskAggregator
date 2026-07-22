import { CircleCheck, TriangleAlert, OctagonAlert } from './icons';

const fmtKm = (km) => (km ? `${km.toLocaleString()} km` : null);
const path = (route) => route?.path?.join(' → ');

// Severity ranks honestly: green = clear, amber = threat present but a clean
// detour exists, red = every option crosses active threat airspace.
export default function RouteStatus({ routeData }) {
  const { status, standard_route, safe_route, zones_crossed } = routeData;

  if (status === 'NO_SAFE_PATH') {
    const crossed = zones_crossed?.map((z) => z.description).join('; ');
    return (
      <div className="status-card status-card--critical">
        <div className="status-head"><OctagonAlert />No fully safe route</div>
        Every available path crosses active threat airspace. Lowest-risk option:
        <div className="route-path" style={{ marginTop: 5 }}>{path(safe_route)}</div>
        {crossed && <div className="status-meta">Crosses: {crossed}</div>}
        <div className="status-meta">{fmtKm(safe_route?.total_distance_km)}</div>
      </div>
    );
  }

  if (status === 'REROUTED') {
    const blocked = standard_route?.zones_crossed?.map((z) => z.description).join('; ');
    return (
      <div className="status-card status-card--warn">
        <div className="status-head"><TriangleAlert />Rerouted around threat</div>
        Direct path <span className="route-path">{path(standard_route)}</span> intersects
        active threat airspace. Clear detour:
        <div className="route-path" style={{ marginTop: 5 }}>{path(safe_route)}</div>
        {blocked && <div className="status-meta">Blocked by: {blocked}</div>}
        <div className="status-meta">Detour distance: {fmtKm(safe_route?.total_distance_km)}</div>
      </div>
    );
  }

  return (
    <div className="status-card status-card--good">
      <div className="status-head"><CircleCheck />Route clear</div>
      <div className="route-path">{path(standard_route)}</div>
      <div className="status-meta">{fmtKm(standard_route?.total_distance_km)} · no active threats on the direct path</div>
    </div>
  );
}
