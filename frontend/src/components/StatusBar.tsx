import type { RuntimeResponse } from "../lib/api";

import { StatusBadge } from "./StatusBadge";

type StatusBarProps = {
  runtime: RuntimeResponse;
};

export function StatusBar({ runtime }: StatusBarProps) {
  return (
    <div className="status-bar" role="status">
      <div className="status-bar__cluster">
        <span className="status-bar__label">Mode</span>
        <StatusBadge kind="mode" value={runtime.mode} />
      </div>
      <div className="status-bar__cluster">
        <span className="status-bar__label">Strategy</span>
        <strong>{runtime.strategy}</strong>
      </div>
      <div className="status-bar__cluster">
        <span className="status-bar__label">Venue</span>
        <strong>{runtime.venue}</strong>
      </div>
      <div className="status-bar__cluster">
        <span className="status-bar__label">Execution</span>
        <strong>{runtime.execution_adapter}</strong>
      </div>
      <div className="status-bar__cluster">
        <span className="status-bar__label">Dataset</span>
        <strong>{runtime.research_dataset}</strong>
      </div>
    </div>
  );
}
