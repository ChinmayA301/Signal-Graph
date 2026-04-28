export function RiskBadge({ manipulationRisk }: { manipulationRisk: number }) {
  const tier = manipulationRisk < 35 ? "low" : manipulationRisk < 65 ? "mid" : "high";
  const label =
    tier === "low" ? "Lower suspicion" : tier === "mid" ? "Elevated suspicion" : "High suspicion (review context)";
  return (
    <span className={`badge ${tier}`} title="Heuristic manipulation risk (0-100). Not a verdict.">
      Manipulation risk {manipulationRisk.toFixed(0)} — {label}
    </span>
  );
}
