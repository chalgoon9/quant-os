import { Link } from "react-router-dom";

import { useKillSwitchActive } from "../hooks/useKillSwitchActive";
import { useOpsSummary } from "../hooks/useOpsSummary";
import { useReconciliationLatest } from "../hooks/useReconciliationLatest";
import { formatDecimal, titleCase } from "../lib/format";
import { KpiCard } from "../components/KpiCard";
import { SectionCard } from "../components/SectionCard";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";

export function OverviewPage() {
  const opsSummary = useOpsSummary();
  const reconciliation = useReconciliationLatest();
  const killSwitch = useKillSwitchActive();

  return (
    <div className="page-grid">
      <SectionCard eyebrow="Overview" title="Portfolio Snapshot">
        {opsSummary.isLoading ? (
          <div className="kpi-grid">
            {Array.from({ length: 5 }).map((_, index) => (
              <div className="skeleton skeleton--card" key={index} />
            ))}
          </div>
        ) : opsSummary.isError ? (
          <StatePanel
            description="The latest portfolio summary is unavailable."
            onAction={() => void opsSummary.refetch()}
            actionLabel="Retry"
            title="Unable to load snapshot"
          />
        ) : opsSummary.data ? (
          <div className="kpi-grid">
            <KpiCard label="NAV" rawValue={opsSummary.data.nav} value={formatDecimal(opsSummary.data.nav)} />
            <KpiCard
              label="Cash"
              rawValue={opsSummary.data.cash_balance}
              value={formatDecimal(opsSummary.data.cash_balance)}
            />
            <KpiCard
              label="Realized PnL"
              rawValue={opsSummary.data.realized_pnl}
              value={formatDecimal(opsSummary.data.realized_pnl)}
            />
            <KpiCard
              label="Unrealized PnL"
              rawValue={opsSummary.data.unrealized_pnl}
              value={formatDecimal(opsSummary.data.unrealized_pnl)}
            />
            <KpiCard
              label="Total PnL"
              rawValue={opsSummary.data.total_pnl}
              value={formatDecimal(opsSummary.data.total_pnl)}
            />
          </div>
        ) : (
          <StatePanel description="No portfolio snapshot has been written yet." title="No snapshot yet" />
        )}
      </SectionCard>

      <SectionCard
        action={
          <Link className="button button--ghost" to="/reports">
            View details
          </Link>
        }
        eyebrow="Overview"
        title="Reconciliation"
      >
        {reconciliation.isLoading ? (
          <div className="skeleton skeleton--block" />
        ) : reconciliation.isError ? (
          <StatePanel
            description="The latest reconciliation record could not be loaded."
            onAction={() => void reconciliation.refetch()}
            actionLabel="Retry"
            title="Unable to load reconciliation"
          />
        ) : reconciliation.data ? (
          <div className="stack-sm">
            <div className="inline-list">
              <StatusBadge value={reconciliation.data.status} />
              <span>{reconciliation.data.mismatch_count} mismatches</span>
            </div>
            <p>{reconciliation.data.summary}</p>
          </div>
        ) : (
          <StatePanel description="No reconciliation log has been written yet." title="Unknown" />
        )}
      </SectionCard>

      <SectionCard
        action={
          <Link className="button button--ghost" to="/controls">
            Open controls
          </Link>
        }
        eyebrow="Overview"
        title="Kill Switch"
      >
        {killSwitch.isLoading ? (
          <div className="skeleton skeleton--block" />
        ) : killSwitch.isError ? (
          <StatePanel
            description="Kill switch state is unavailable."
            onAction={() => void killSwitch.refetch()}
            actionLabel="Retry"
            title="Unable to load kill switch"
          />
        ) : killSwitch.data && killSwitch.data.items.length > 0 ? (
          <div className="stack-sm">
            <StatusBadge value="mismatch" />
            <p>{killSwitch.data.items.map((item) => titleCase(item.reason)).join(", ")}</p>
          </div>
        ) : (
          <div className="stack-sm">
            <StatusBadge value="matched" />
            <p>No active kill switch events.</p>
          </div>
        )}
      </SectionCard>

      <SectionCard eyebrow="Overview" title="Position Summary">
        <StatePanel description="Position API is not connected yet." title="No open positions" />
      </SectionCard>
    </div>
  );
}
