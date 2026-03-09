import type { RuntimeResponse } from "../lib/api";
import { humanizeExecutionAdapter, humanizeVenue } from "../lib/format";

import { StatusBadge } from "./StatusBadge";

type StatusBarProps = {
  runtime: RuntimeResponse;
};

export function StatusBar({ runtime }: StatusBarProps) {
  const modeExplanation =
    runtime.mode === "paper"
      ? "페이퍼 모드는 주문과 체결을 내부에서만 시뮬레이션하며, 브로커로 실제 주문을 보내지 않습니다."
      : runtime.mode === "shadow"
        ? "섀도 모드는 실제 주문 없이 의사결정 흐름만 따라가며 결과를 점검하는 용도입니다."
        : "라이브 모드는 준비 상태를 보여주기 위한 표시이며, 이 MVP에서는 실제 주문 제출이 비활성화되어 있습니다.";

  return (
    <div className="status-bar" role="status">
      <div className="status-bar__cluster">
        <span className="status-bar__label">모드</span>
        <StatusBadge kind="mode" value={runtime.mode} />
      </div>
      <div className="status-bar__cluster">
        <span className="status-bar__label">전략</span>
        <strong>{runtime.strategy}</strong>
      </div>
      <div className="status-bar__cluster">
        <span className="status-bar__label">시장</span>
        <strong>{humanizeVenue(runtime.venue)}</strong>
      </div>
      <div className="status-bar__cluster">
        <span className="status-bar__label">실행 경로</span>
        <strong>{humanizeExecutionAdapter(runtime.execution_adapter)}</strong>
      </div>
      <div className="status-bar__cluster">
        <span className="status-bar__label">현재 데이터셋</span>
        <strong>{runtime.research_dataset}</strong>
      </div>
      <p className="status-bar__note">{modeExplanation}</p>
    </div>
  );
}
