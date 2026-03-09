type KpiCardProps = {
  label: string;
  value: string;
  hint?: string;
  rawValue?: string | null;
};

export function KpiCard({ label, value, hint, rawValue }: KpiCardProps) {
  return (
    <div className="kpi-card">
      <span className="kpi-card__label" title={hint}>
        {label}
      </span>
      <strong className="kpi-card__value">{value}</strong>
      {hint ? <p className="kpi-card__hint">{hint}</p> : null}
      {rawValue ? <span className="kpi-card__raw">{rawValue}</span> : null}
    </div>
  );
}
