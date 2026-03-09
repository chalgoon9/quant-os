import { Link } from "react-router-dom";

import { useKillSwitchActive } from "../hooks/useKillSwitchActive";
import { useOpsSummary } from "../hooks/useOpsSummary";
import { useReconciliationLatest } from "../hooks/useReconciliationLatest";
import { PageIntro } from "../components/PageIntro";
import { formatDecimal, humanizeKillSwitchReason } from "../lib/format";
import { KpiCard } from "../components/KpiCard";
import { SectionCard } from "../components/SectionCard";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";

export function OverviewPage() {
  const opsSummary = useOpsSummary();
  const reconciliation = useReconciliationLatest();
  const killSwitch = useKillSwitchActive();

  return (
    <div className="page-stack">
      <PageIntro
        description="계좌 가치, 사용 가능한 현금, 손익, 최근 안전 상태를 가장 먼저 확인하는 화면입니다."
        note="이 화면이 대부분 비어 있다면 먼저 리서치에서 데이터를 불러오고, 이후 페이퍼 또는 섀도 흐름이 포트폴리오 기록을 남기도록 실행하십시오."
        title="지금 시스템이 알고 있는 상태를 한눈에 봅니다"
      />
      <div className="page-grid">
        <SectionCard
          action={
            <Link className="button button--ghost" to="/research">
              리서치 열기
            </Link>
          }
          className="panel--span-full"
          description="처음 사용하는 분을 위한 짧은 시작 순서와, 이 화면에서 가장 중요한 용어 설명입니다."
          eyebrow="개요"
          title="처음 시작하기"
        >
          <div className="help-grid">
            <div>
              <strong className="help-grid__title">처음 사용하는 순서</strong>
              <ol className="help-list help-list--numbered">
                <li>리서치로 이동해 일봉 시장 데이터를 저장합니다.</li>
                <li>시스템이 포트폴리오 스냅샷을 기록한 뒤 이 화면으로 돌아옵니다.</li>
                <li>주문 화면에서 주문 이력과 체결 내역을 확인합니다.</li>
                <li>리포트 화면에서 정합성 점검과 안전 이벤트를 검토합니다.</li>
              </ol>
            </div>
            <div>
              <strong className="help-grid__title">빠른 용어 설명</strong>
              <ul className="help-list">
                <li>`순자산가치`는 현금과 현재 보유 포지션 가치를 합친 값입니다.</li>
                <li>`실현 손익`은 이미 끝난 거래에서 확정된 손익입니다.</li>
                <li>`미실현 손익`은 아직 보유 중인 포지션의 평가 손익입니다.</li>
                <li>`정합성 점검`은 시스템 기록을 계속 신뢰할 수 있는지 확인하는 안전 검사입니다.</li>
              </ul>
            </div>
          </div>
        </SectionCard>
        <SectionCard
          description="계좌 가치, 현금, 손익을 빠르게 확인하는 요약 카드입니다."
          eyebrow="개요"
          title="포트폴리오 스냅샷"
        >
          {opsSummary.isLoading ? (
            <div className="kpi-grid">
              {Array.from({ length: 5 }).map((_, index) => (
                <div className="skeleton skeleton--card" key={index} />
              ))}
            </div>
          ) : opsSummary.isError ? (
            <StatePanel
              description="최신 포트폴리오 요약을 불러오지 못했습니다."
              onAction={() => void opsSummary.refetch()}
              actionLabel="다시 시도"
              title="스냅샷을 불러올 수 없음"
            />
          ) : opsSummary.data ? (
            <div className="kpi-grid">
              <KpiCard
                hint="현금과 현재 보유 포지션 가치를 합친 전체 계좌 가치입니다."
                label="순자산가치(NAV)"
                rawValue={opsSummary.data.nav}
                value={formatDecimal(opsSummary.data.nav)}
              />
              <KpiCard
                hint="현재 바로 사용할 수 있는 현금 잔고입니다."
                label="현금 잔고"
                rawValue={opsSummary.data.cash_balance}
                value={formatDecimal(opsSummary.data.cash_balance)}
              />
              <KpiCard
                hint="이미 종료된 거래에서 확정된 손익입니다."
                label="실현 손익"
                rawValue={opsSummary.data.realized_pnl}
                value={formatDecimal(opsSummary.data.realized_pnl)}
              />
              <KpiCard
                hint="지금 청산한다고 가정할 때 아직 확정되지 않은 평가 손익입니다."
                label="미실현 손익"
                rawValue={opsSummary.data.unrealized_pnl}
                value={formatDecimal(opsSummary.data.unrealized_pnl)}
              />
              <KpiCard
                hint="실현 손익과 미실현 손익을 합친 값입니다."
                label="총 손익"
                rawValue={opsSummary.data.total_pnl}
                value={formatDecimal(opsSummary.data.total_pnl)}
              />
            </div>
          ) : (
            <StatePanel
              description="아직 포트폴리오 스냅샷이 기록되지 않았습니다. 계좌 가치, 현금, 손익이 기록되면 이 카드가 자동으로 채워집니다."
              title="스냅샷 없음"
            />
          )}
        </SectionCard>

        <SectionCard
          action={
            <Link className="button button--ghost" to="/reports">
              자세히 보기
            </Link>
          }
          description="시스템 기록이 기대 상태와 계속 맞는지 점검하는 카드입니다."
          eyebrow="개요"
          title="정합성 점검"
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
            <div className="stack-sm">
              <div className="inline-list">
                <StatusBadge value={reconciliation.data.status} />
                <span>차이 {reconciliation.data.mismatch_count}건</span>
              </div>
              <p>{reconciliation.data.summary}</p>
            </div>
          ) : (
            <StatePanel
              description="일일 안전 점검이 실행된 뒤에 이 카드가 표시됩니다. 이 화면에서는 시스템이 자기 기록을 계속 신뢰하는지 확인합니다."
              title="정합성 점검 기록 없음"
            />
          )}
        </SectionCard>

        <SectionCard
          action={
            <Link className="button button--ghost" to="/controls">
              제어 화면 열기
            </Link>
          }
          description="신규 주문을 막는 안전 규칙이 현재 있는지 보여줍니다."
          eyebrow="개요"
          title="킬 스위치"
        >
          {killSwitch.isLoading ? (
            <div className="skeleton skeleton--block" />
          ) : killSwitch.isError ? (
            <StatePanel
              description="킬 스위치 상태를 불러오지 못했습니다."
              onAction={() => void killSwitch.refetch()}
              actionLabel="다시 시도"
              title="킬 스위치를 불러올 수 없음"
            />
          ) : killSwitch.data && killSwitch.data.items.length > 0 ? (
            <div className="stack-sm">
              <StatusBadge value="mismatch" />
              <p>
                신규 주문이 중단되어 있습니다. 자세한 사유는 제어 화면에서 확인하십시오:{" "}
                {killSwitch.data.items.map((item) => humanizeKillSwitchReason(item.reason)).join(", ")}.
              </p>
            </div>
          ) : (
            <div className="stack-sm">
              <StatusBadge value="matched" />
              <p>현재 활성화된 안전 차단이 없습니다. 킬 스위치 때문에 신규 주문이 막혀 있지 않습니다.</p>
            </div>
          )}
        </SectionCard>

        <SectionCard
          description="포지션 동기화가 연결되면 보유 수량과 익스포저가 이곳에 표시됩니다."
          eyebrow="개요"
          title="포지션 요약"
        >
          <StatePanel
            description="이 MVP에서는 포지션 동기화가 아직 연결되지 않았습니다. 그전까지는 스냅샷, 주문, 리포트 화면으로 현재 상태를 파악하십시오."
            title="포지션 상세 없음"
          />
        </SectionCard>
      </div>
    </div>
  );
}
