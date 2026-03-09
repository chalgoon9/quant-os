import { Link } from "react-router-dom";

import type { KillSwitchEventDto } from "../lib/api";
import { formatTimestamp, titleCase } from "../lib/format";

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
        <strong>KILL SWITCH ACTIVE</strong>
        <p>
          {events.map((event) => titleCase(event.reason)).join(", ")} · latest trigger{" "}
          {formatTimestamp(latestEvent.triggered_at)}
        </p>
      </div>
      <div className="kill-banner__actions">
        <Link className="button button--ghost" to="/reports">
          Open Reports
        </Link>
        <Link className="button" to="/controls">
          Open Controls
        </Link>
      </div>
    </div>
  );
}
