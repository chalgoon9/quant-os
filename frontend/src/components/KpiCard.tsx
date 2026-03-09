type KpiCardProps = {
  label: string;
  value: string;
  rawValue?: string | null;
};

export function KpiCard({ label, value, rawValue }: KpiCardProps) {
  return (
    <div className="kpi-card">
      <span className="kpi-card__label">{label}</span>
      <strong className="kpi-card__value">{value}</strong>
      {rawValue ? <span className="kpi-card__raw">{rawValue}</span> : null}
    </div>
  );
}
