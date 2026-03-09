import { Link } from "react-router-dom";

import type { KillSwitchEventDto } from "../lib/api";
import { formatTimestamp, humanizeKillSwitchReason } from "../lib/format";

type KillSwitchBannerProps = {
  events: KillSwitchEventDto[];
};

export function KillSwitchBanner({ events }: KillSwitchBannerProps) {
  if (events.length === 0) {
    return null;
  }

  const latestEvent = [...events].sort((left, right) =>
    right.triggered_at.localeCompare(left.triggered_at),
  )[0];

  return (
    <div className="kill-banner" role="alert">
      <div>
        <strong>킬 스위치 활성화</strong>
        <p>
          신규 주문이 중단되어 있습니다. 원인: {events
            .map((event) => humanizeKillSwitchReason(event.reason))
            .join(", ")}. 최근 발생 시각은 {formatTimestamp(latestEvent.triggered_at)}입니다.
        </p>
      </div>
      <div className="kill-banner__actions">
        <Link className="button button--ghost" to="/reports">
          리포트 보기
        </Link>
        <Link className="button" to="/controls">
          제어 화면 열기
        </Link>
      </div>
    </div>
  );
}
