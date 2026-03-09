import { humanizeMode, humanizeSide, humanizeStatus } from "../lib/format";

type StatusBadgeProps = {
  value: string;
  kind?: "mode" | "status" | "side";
};

const MODE_CLASS_MAP: Record<string, string> = {
  paper: "badge--neutral",
  shadow: "badge--warning",
  live: "badge--danger",
};

const SIDE_CLASS_MAP: Record<string, string> = {
  buy: "badge--success",
  sell: "badge--danger",
};

const STATUS_CLASS_MAP: Record<string, string> = {
  matched: "badge--success",
  filled: "badge--success",
  acknowledged: "badge--neutral",
  working: "badge--neutral",
  partially_filled: "badge--warning",
  mismatch: "badge--danger",
  error: "badge--danger",
  broker_rejected: "badge--danger",
  reconcile_pending: "badge--warning",
};

function getClassName(value: string, kind?: "mode" | "status" | "side") {
  if (kind === "mode") {
    return MODE_CLASS_MAP[value] ?? "badge--neutral";
  }

  if (kind === "side") {
    return SIDE_CLASS_MAP[value] ?? "badge--neutral";
  }

  return STATUS_CLASS_MAP[value] ?? "badge--neutral";
}

export function StatusBadge({ value, kind = "status" }: StatusBadgeProps) {
  const label =
    kind === "mode"
      ? humanizeMode(value)
      : kind === "side"
        ? humanizeSide(value)
        : humanizeStatus(value);

  return <span className={`badge ${getClassName(value, kind)}`}>{label}</span>;
}
