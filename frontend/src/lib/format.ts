const compactNumberFormatter = new Intl.NumberFormat("ko-KR", {
  maximumFractionDigits: 2,
});

const moneyFormatter = new Intl.NumberFormat("ko-KR", {
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

export function formatPercent(value: string | null | undefined, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return value;
  }

  return `${moneyFormatter.format(numeric * 100)}%`;
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

export function humanizeMode(value: string) {
  switch (value) {
    case "paper":
      return "페이퍼";
    case "shadow":
      return "섀도";
    case "live":
      return "라이브";
    default:
      return titleCase(value);
  }
}

export function humanizeSide(value: string) {
  switch (value) {
    case "buy":
      return "매수";
    case "sell":
      return "매도";
    default:
      return titleCase(value);
  }
}

export function humanizeStatus(value: string) {
  switch (value) {
    case "matched":
      return "정상";
    case "mismatch":
      return "불일치";
    case "error":
      return "오류";
    case "filled":
      return "체결 완료";
    case "acknowledged":
      return "접수됨";
    case "approved":
      return "승인됨";
    case "working":
      return "집행 중";
    case "partially_filled":
      return "부분 체결";
    case "broker_rejected":
      return "브로커 거부";
    case "reconcile_pending":
      return "재확인 필요";
    case "cancelled":
      return "취소됨";
    case "cancel_requested":
      return "취소 요청";
    case "submitting":
      return "제출 중";
    case "planned":
      return "계획됨";
    default:
      return titleCase(value);
  }
}

export function humanizeEventType(value: string) {
  switch (value) {
    case "submitted":
      return "주문 제출";
    case "acknowledged":
      return "접수 확인";
    case "fill_recorded":
      return "체결 기록";
    case "cancel_requested":
      return "취소 요청";
    case "cancelled":
      return "취소 완료";
    default:
      return titleCase(value);
  }
}

export function humanizeExecutionAdapter(value: string) {
  switch (value) {
    case "PaperAdapter":
      return "내부 페이퍼 실행";
    case "ShadowAdapter":
      return "섀도 검증 실행";
    case "StubLiveAdapter":
      return "라이브 스텁";
    default:
      return value;
  }
}

export function humanizeVenue(value: string) {
  switch (value.toLowerCase()) {
    case "krx":
      return "KRX";
    case "upbit":
      return "업비트";
    default:
      return value;
  }
}

export function humanizeKillSwitchReason(value: string) {
  switch (value) {
    case "reconciliation_failure":
      return "안전 점검에서 기록 불일치가 확인됨";
    case "stale_market_data":
      return "시장 데이터가 오래됨";
    case "daily_loss_limit":
      return "일일 손실 한도를 초과함";
    case "event_write_failure":
      return "이벤트를 안전하게 기록하지 못함";
    case "duplicate_intent":
      return "중복 주문 요청이 감지됨";
    case "unknown_open_order":
      return "알 수 없는 미체결 주문이 감지됨";
    default:
      return humanizeStatus(value);
  }
}

export function humanizeReconciliationIssueCode(value: string) {
  switch (value) {
    case "cash_mismatch":
      return "현금 잔고 차이";
    case "position_mismatch":
      return "포지션 차이";
    case "open_order_mismatch":
      return "미체결 주문 차이";
    default:
      return humanizeStatus(value);
  }
}
