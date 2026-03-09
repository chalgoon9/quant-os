import { SectionCard } from "../components/SectionCard";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";
import { useKillSwitchActive } from "../hooks/useKillSwitchActive";
import { useRuntime } from "../hooks/useRuntime";
import { formatTimestamp, titleCase } from "../lib/format";

export function ControlsPage() {
  const runtime = useRuntime();
  const killSwitch = useKillSwitchActive();

  return (
    <div className="page-grid">
      <SectionCard eyebrow="Controls" title="Mode Notice">
        {runtime.isLoading ? (
          <div className="skeleton skeleton--block" />
        ) : runtime.isError ? (
          <StatePanel
            description="Runtime details are unavailable."
            onAction={() => void runtime.refetch()}
            actionLabel="Retry"
            title="Unable to load runtime"
          />
        ) : runtime.data ? (
          <div className="stack-md">
            <div className="inline-list">
              <StatusBadge kind="mode" value={runtime.data.mode} />
              <span>{runtime.data.execution_adapter}</span>
            </div>
            <p>
              {runtime.data.mode === "live"
                ? "Live mode is currently a fail-closed stub. Do not use this UI for order submission."
                : "This dashboard is read-only and intentionally excludes destructive controls."}
            </p>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard eyebrow="Controls" title="Kill Switch Panel">
        {killSwitch.isLoading ? (
          <div className="skeleton skeleton--block" />
        ) : killSwitch.isError ? (
          <StatePanel
            description="Kill switch state could not be loaded."
            onAction={() => void killSwitch.refetch()}
            actionLabel="Retry"
            title="Unable to load kill switch"
          />
        ) : killSwitch.data && killSwitch.data.items.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Reason</th>
                <th>Triggered</th>
                <th>Trigger Value</th>
                <th>Threshold</th>
              </tr>
            </thead>
            <tbody>
              {killSwitch.data.items.map((item) => (
                <tr key={item.event_id}>
                  <td>{titleCase(item.reason)}</td>
                  <td>{formatTimestamp(item.triggered_at)}</td>
                  <td>{item.trigger_value ?? "-"}</td>
                  <td>{item.threshold_value ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <StatePanel description="No active kill switch events." title="Clear" />
        )}
      </SectionCard>

      <SectionCard eyebrow="Controls" title="External Sync">
        <StatePanel description="External broker sync is not yet connected." title="Not yet connected" />
      </SectionCard>
    </div>
  );
}
