const compactNumberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
});

const moneyFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
});

export function formatDecimal(value: string | null | undefined, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return value;
  }

  return moneyFormatter.format(numeric);
}

export function formatCompactDecimal(value: string | null | undefined, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return value;
  }

  return compactNumberFormatter.format(numeric);
}

export function formatTimestamp(value: string | null | undefined, fallback = "-") {
  if (!value) {
    return fallback;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function titleCase(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
