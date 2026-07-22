export default function MapLegend() {
  return (
    <div className="risk-legend">
      <strong>Legend</strong>
      <div className="legend-item"><span className="legend-swatch legend-swatch--zone" />Active threat zone</div>
      <div className="legend-item"><span className="legend-swatch legend-swatch--blocked" />Blocked direct path</div>
      <div className="legend-item"><span className="legend-swatch legend-swatch--route" />Computed route</div>
      <div className="legend-item"><span className="legend-swatch legend-swatch--ok" />Airport — low risk</div>
      <div className="legend-item"><span className="legend-swatch legend-swatch--high" />Airport — elevated risk</div>
    </div>
  );
}
