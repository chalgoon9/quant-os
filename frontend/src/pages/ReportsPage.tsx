import { SectionCard } from "../components/SectionCard";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";
import { useDailyReport } from "../hooks/useDailyReport";
import { useKillSwitchActive } from "../hooks/useKillSwitchActive";
import { useReconciliationLatest } from "../hooks/useReconciliationLatest";
import { formatDecimal, formatTimestamp, titleCase } from "../lib/format";

export function ReportsPage() {
  const dailyReport = useDailyReport();
  const reconciliation = useReconciliationLatest();
  const killSwitch = useKillSwitchActive();

  return (
    <div className="page-grid page-grid--wide">
      <SectionCard eyebrow="Reports" title="Daily Report">
        {dailyReport.isLoading ? (
          <div className="skeleton skeleton--block" />
        ) : dailyReport.isError ? (
          <StatePanel
            description="No daily report could be generated from the latest operational data."
            onAction={() => void dailyReport.refetch()}
            actionLabel="Retry"
            title="No report available yet"
          />
        ) : dailyReport.data ? (
          <div className="stack-md">
            <div className="inline-list">
              <span>As of {formatTimestamp(dailyReport.data.as_of)}</span>
              <StatusBadge value={dailyReport.data.reconciliation_status} />
            </div>
            <div className="report-grid">
              <div>
                <span>NAV</span>
                <strong>{formatDecimal(dailyReport.data.nav)}</strong>
              </div>
              <div>
                <span>Cash</span>
                <strong>{formatDecimal(dailyReport.data.cash_balance)}</strong>
              </div>
              <div>
                <span>Total PnL</span>
                <strong>{formatDecimal(dailyReport.data.total_pnl)}</strong>
              </div>
            </div>
            <pre className="report-markdown">{dailyReport.data.body_markdown}</pre>
          </div>
        ) : (
          <StatePanel description="No report content is available yet." title="No report available yet" />
        )}
      </SectionCard>

      <SectionCard eyebrow="Reports" title="Reconciliation Detail">
        {reconciliation.isLoading ? (
          <div className="skeleton skeleton--block" />
        ) : reconciliation.isError ? (
          <StatePanel
            description="The latest reconciliation record is unavailable."
            onAction={() => void reconciliation.refetch()}
            actionLabel="Retry"
            title="Unable to load reconciliation"
          />
        ) : reconciliation.data ? (
          <div className="stack-md">
            <div className="inline-list">
              <StatusBadge value={reconciliation.data.status} />
              <span>{reconciliation.data.summary}</span>
              <span>{reconciliation.data.mismatch_count} mismatches</span>
            </div>
            {reconciliation.data.issues.length === 0 ? (
              <StatePanel description="No issues recorded." title="No issues" />
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Message</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {reconciliation.data.issues.map((issue) => (
                    <tr key={`${issue.code}-${issue.message}`}>
                      <td>{issue.code}</td>
                      <td>{issue.message}</td>
                      <td>{issue.details ? JSON.stringify(issue.details) : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ) : (
          <StatePanel description="No reconciliation record is available yet." title="No record yet" />
        )}
      </SectionCard>

      <SectionCard eyebrow="Reports" title="Kill Switch Preview">
        {killSwitch.isLoading ? (
          <div className="skeleton skeleton--block" />
        ) : killSwitch.isError ? (
          <StatePanel
            description="Kill switch history preview is unavailable."
            onAction={() => void killSwitch.refetch()}
            actionLabel="Retry"
            title="Unable to load kill switch"
          />
        ) : killSwitch.data && killSwitch.data.items.length > 0 ? (
          <div className="timeline">
            {killSwitch.data.items.map((item) => (
              <div className="timeline__item" key={item.event_id}>
                <div className="timeline__meta">
                  <StatusBadge value="mismatch" />
                  <span>{formatTimestamp(item.triggered_at)}</span>
                </div>
                <strong>{titleCase(item.reason)}</strong>
                <p>{item.details ? JSON.stringify(item.details) : "No details"}</p>
              </div>
            ))}
          </div>
        ) : (
          <StatePanel description="No active kill switch events." title="Clear" />
        )}
      </SectionCard>
    </div>
  );
}
