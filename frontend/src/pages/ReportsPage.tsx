import { SectionCard } from "../components/SectionCard";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";
import { PageIntro } from "../components/PageIntro";
import { useDailyReport } from "../hooks/useDailyReport";
import { useKillSwitchActive } from "../hooks/useKillSwitchActive";
import { useReconciliationLatest } from "../hooks/useReconciliationLatest";
import {
  formatDecimal,
  formatTimestamp,
  humanizeKillSwitchReason,
  humanizeReconciliationIssueCode,
} from "../lib/format";

function describeIssueDetails(details: Record<string, unknown> | null) {
  if (!details) {
    return "추가 상세 정보가 기록되지 않았습니다.";
  }

  const expected = details.expected;
  const actual = details.actual;

  if (expected !== undefined || actual !== undefined) {
    return `기대값 ${String(expected ?? "-")}, 실제값 ${String(actual ?? "-")}`;
  }

  return Object.entries(details)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(", ");
}

export function ReportsPage() {
  const dailyReport = useDailyReport();
  const reconciliation = useReconciliationLatest();
  const killSwitch = useKillSwitchActive();

  return (
    <div className="page-stack">
      <PageIntro
        description="일일 요약, 정합성 점검, 안전 이벤트를 한 곳에서 확인하는 화면입니다."
        note="가장 최근 실행에서 무슨 일이 있었는지, 어떤 차이점이나 안전 차단이 있었는지 알고 싶을 때 이 페이지를 보십시오."
        title="마지막 실행 결과를 설명합니다"
      />
      <div className="page-grid page-grid--wide">
        <SectionCard
          className="panel--span-full"
          description="도메인 용어나 상태 표가 낯설 때 먼저 읽는 안내입니다."
          eyebrow="리포트"
          title="리포트 읽는 방법"
        >
          <ul className="help-list">
            <li>`일일 리포트`는 최근 실행 기준 자산 가치, 현금, 손익을 요약합니다.</li>
            <li>`정합성 점검`은 시스템 기록이 기대 상태와 계속 맞는지 설명합니다.</li>
            <li>`킬 스위치` 항목은 어떤 안전 규칙이 언제 신규 주문을 멈췄는지 보여줍니다.</li>
          </ul>
        </SectionCard>
        <SectionCard
          description="계좌 가치, 현금, 손익, 핵심 메모를 요약한 일일 리포트입니다."
          eyebrow="리포트"
          title="일일 리포트"
        >
          {dailyReport.isLoading ? (
            <div className="skeleton skeleton--block" />
          ) : dailyReport.isError ? (
            <StatePanel
              description="최신 운영 데이터로부터 일일 리포트를 만들지 못했습니다."
              onAction={() => void dailyReport.refetch()}
              actionLabel="다시 시도"
              title="리포트 없음"
            />
          ) : dailyReport.data ? (
            <div className="stack-md">
              <div className="inline-list">
                <span>기준 시각 {formatTimestamp(dailyReport.data.as_of)}</span>
                <StatusBadge value={dailyReport.data.reconciliation_status} />
              </div>
              <div className="report-grid">
                <div>
                  <span>순자산가치</span>
                  <strong>{formatDecimal(dailyReport.data.nav)}</strong>
                </div>
                <div>
                  <span>현금</span>
                  <strong>{formatDecimal(dailyReport.data.cash_balance)}</strong>
                </div>
                <div>
                  <span>총 손익</span>
                  <strong>{formatDecimal(dailyReport.data.total_pnl)}</strong>
                </div>
              </div>
              <pre className="report-markdown">{dailyReport.data.body_markdown}</pre>
            </div>
          ) : (
            <StatePanel
              description="리포트 생성 단계가 끝난 뒤에 이 카드가 채워집니다. 운영 데이터가 아직 부족하면 개요와 주문 화면도 비어 있을 수 있습니다."
              title="리포트 없음"
            />
          )}
        </SectionCard>

        <SectionCard
          description="내부 기록이 최신 기대 상태 또는 외부 상태와 맞는지 보여줍니다."
          eyebrow="리포트"
          title="정합성 점검 상세"
        >
          {reconciliation.isLoading ? (
            <div className="skeleton skeleton--block" />
          ) : reconciliation.isError ? (
            <StatePanel
              description="최신 정합성 점검 기록을 불러오지 못했습니다."
              onAction={() => void reconciliation.refetch()}
              actionLabel="다시 시도"
              title="정합성 점검을 불러올 수 없음"
            />
          ) : reconciliation.data ? (
            <div className="stack-md">
              <div className="inline-list">
                <StatusBadge value={reconciliation.data.status} />
                <span>{reconciliation.data.summary}</span>
                <span>차이 {reconciliation.data.mismatch_count}건</span>
              </div>
              {reconciliation.data.issues.length === 0 ? (
                <StatePanel description="기록된 이슈가 없습니다." title="이슈 없음" />
              ) : (
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>구분</th>
                        <th>메시지</th>
                        <th>상세</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reconciliation.data.issues.map((issue) => (
                        <tr key={`${issue.code}-${issue.message}`}>
                          <td>{humanizeReconciliationIssueCode(issue.code)}</td>
                          <td>{issue.message}</td>
                          <td>{describeIssueDetails(issue.details)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : (
            <StatePanel
              description="시스템 점검이 실행된 뒤 이 카드가 채워집니다. 기록 간 차이가 있으면 이곳에서 설명됩니다."
              title="정합성 점검 기록 없음"
            />
          )}
        </SectionCard>

        <SectionCard
          description="현재 신규 주문을 막고 있는 안전 이벤트 목록입니다."
          eyebrow="리포트"
          title="킬 스위치 미리보기"
        >
          {killSwitch.isLoading ? (
            <div className="skeleton skeleton--block" />
          ) : killSwitch.isError ? (
            <StatePanel
              description="킬 스위치 기록 미리보기를 불러오지 못했습니다."
              onAction={() => void killSwitch.refetch()}
              actionLabel="다시 시도"
              title="킬 스위치를 불러올 수 없음"
            />
          ) : killSwitch.data && killSwitch.data.items.length > 0 ? (
            <div className="timeline">
              {killSwitch.data.items.map((item) => (
                <div className="timeline__item" key={item.event_id}>
                  <div className="timeline__meta">
                    <StatusBadge value="mismatch" />
                    <span>{formatTimestamp(item.triggered_at)}</span>
                  </div>
                  <strong>{humanizeKillSwitchReason(item.reason)}</strong>
                  <p>{describeIssueDetails(item.details)}</p>
                </div>
              ))}
            </div>
          ) : (
            <StatePanel
              description="현재 신규 주문을 막고 있는 활성 킬 스위치 이벤트가 없습니다."
              title="안전 상태 정상"
            />
          )}
        </SectionCard>
      </div>
    </div>
  );
}
