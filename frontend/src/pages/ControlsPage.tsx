import { SectionCard } from "../components/SectionCard";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";
import { PageIntro } from "../components/PageIntro";
import { useKillSwitchActive } from "../hooks/useKillSwitchActive";
import { useRuntime } from "../hooks/useRuntime";
import {
  formatTimestamp,
  humanizeExecutionAdapter,
  humanizeKillSwitchReason,
} from "../lib/format";

export function ControlsPage() {
  const runtime = useRuntime();
  const killSwitch = useKillSwitchActive();

  return (
    <div className="page-stack">
      <PageIntro
        description="현재 운용 모드와 신규 주문을 막을 수 있는 안전 규칙을 설명하는 화면입니다."
        note="이 MVP 대시보드는 읽기 전용입니다. 실제 주문 제출보다는 준비 상태와 안전 상태 확인이 목적입니다."
        title="지금 무엇이 가능한지 설명합니다"
      />
      <div className="page-grid">
        <SectionCard
          className="panel--span-full"
          description="대시보드에서 보게 되는 세 가지 모드를 쉬운 말로 설명합니다."
          eyebrow="제어"
          title="모드 안내"
        >
          <ul className="help-list">
            <li>`페이퍼`는 브로커를 건드리지 않고 주문과 체결을 내부에서 시뮬레이션합니다.</li>
            <li>`섀도`는 실제 주문 없이 의사결정 흐름만 따라가며 결과를 검토하는 모드입니다.</li>
            <li>`라이브`는 준비 상태 표시용이며, 이 MVP에서는 실제 주문 제출이 비활성화되어 있습니다.</li>
          </ul>
        </SectionCard>
        <SectionCard
          description="현재 운용 모드를 쉬운 말로 풀어 설명합니다."
          eyebrow="제어"
          title="현재 모드 안내"
        >
          {runtime.isLoading ? (
            <div className="skeleton skeleton--block" />
          ) : runtime.isError ? (
            <StatePanel
              description="런타임 세부 정보를 불러오지 못했습니다."
              onAction={() => void runtime.refetch()}
              actionLabel="다시 시도"
              title="런타임 정보를 불러올 수 없음"
            />
          ) : runtime.data ? (
            <div className="stack-md">
              <div className="inline-list">
                <StatusBadge kind="mode" value={runtime.data.mode} />
                <span>{humanizeExecutionAdapter(runtime.data.execution_adapter)}</span>
              </div>
              <p>
                {runtime.data.mode === "live"
                  ? "안전을 위해 이 MVP에서는 라이브 주문이 비활성화되어 있습니다. 이 대시보드로 실제 주문을 제출하면 안 됩니다."
                  : runtime.data.mode === "shadow"
                    ? "섀도 모드는 의사결정 흐름을 검토하기 위한 모드이며, 이 MVP에서는 실제 주문을 보내지 않습니다."
                    : "페이퍼 모드는 브로커로 아무것도 보내지 않고 주문과 체결을 내부에서 시뮬레이션합니다."}
              </p>
            </div>
          ) : null}
        </SectionCard>

        <SectionCard
          description="현재 신규 주문을 막는 안전 규칙과 발생 이유를 보여줍니다."
          eyebrow="제어"
          title="킬 스위치 패널"
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
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>사유</th>
                    <th>발생 시각</th>
                    <th>실제 값</th>
                    <th>기준값</th>
                  </tr>
                </thead>
                <tbody>
                  {killSwitch.data.items.map((item) => (
                    <tr key={item.event_id}>
                      <td>{humanizeKillSwitchReason(item.reason)}</td>
                      <td>{formatTimestamp(item.triggered_at)}</td>
                      <td>{item.trigger_value ?? "-"}</td>
                      <td>{item.threshold_value ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <StatePanel
              description="현재 신규 주문을 막는 활성 킬 스위치 이벤트가 없습니다."
              title="안전 상태 정상"
            />
          )}
        </SectionCard>

        <SectionCard
          description="나중에 브로커 계좌 동기화가 연결되면 이 영역에 표시됩니다."
          eyebrow="제어"
          title="브로커 동기화"
        >
          <StatePanel
            description="이 MVP에서는 아직 브로커 동기화가 연결되지 않았습니다. 추가되면 브로커 기준 현금, 포지션, 체결 정보를 이곳에서 확인할 수 있습니다."
            title="아직 연결되지 않음"
          />
        </SectionCard>
      </div>
    </div>
  );
}
