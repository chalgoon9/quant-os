import type { OrderDetailResponse } from "../lib/api";
import {
  formatCompactDecimal,
  formatTimestamp,
  humanizeEventType,
} from "../lib/format";

import { SectionCard } from "./SectionCard";
import { StatusBadge } from "./StatusBadge";
import { StatePanel } from "./StatePanel";

type OrderDetailDrawerProps = {
  detail: OrderDetailResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  onClose: () => void;
};

export function OrderDetailDrawer({
  detail,
  isLoading,
  isError,
  onClose,
}: OrderDetailDrawerProps) {
  return (
    <aside className={`drawer${detail || isLoading || isError ? " drawer--open" : ""}`}>
      <div className="drawer__header">
        <div>
          <p className="panel__eyebrow">주문 상세</p>
          <h2 className="panel__title">이 주문을 읽는 방법</h2>
          <p className="panel__description">
            상단 요약은 현재 상태를, 타임라인은 상태 변경 이력을, 체결 내역은 실제로 나뉘어 체결된 거래 조각을 보여줍니다.
          </p>
        </div>
        <button className="button button--ghost" onClick={onClose} type="button">
          닫기
        </button>
      </div>
      {isLoading ? <div className="skeleton skeleton--block" /> : null}
      {isError ? (
        <StatePanel
          description="주문 상세를 불러오지 못했습니다. 행을 다시 선택해 보십시오."
          title="주문 상세를 불러올 수 없음"
        />
      ) : null}
      {detail ? (
        <div className="drawer__content">
          <SectionCard
            description="이 주문의 최신 상태 요약입니다."
            title={detail.projection.order_id}
          >
            <dl className="definition-grid">
              <div>
                <dt>상태</dt>
                <dd>
                  <StatusBadge value={detail.projection.status} />
                </dd>
              </div>
              <div>
                <dt>의도 ID</dt>
                <dd>{detail.projection.intent_id}</dd>
              </div>
              <div>
                <dt>주문 수량</dt>
                <dd>{formatCompactDecimal(detail.projection.quantity)}</dd>
              </div>
              <div>
                <dt>체결 수량</dt>
                <dd>{formatCompactDecimal(detail.projection.filled_quantity)}</dd>
              </div>
              <div>
                <dt>생성 시각</dt>
                <dd>{formatTimestamp(detail.projection.created_at)}</dd>
              </div>
              <div>
                <dt>마지막 갱신</dt>
                <dd>{formatTimestamp(detail.projection.updated_at)}</dd>
              </div>
            </dl>
          </SectionCard>
          <SectionCard
            description="주문 제출부터 체결 또는 취소까지 기록된 상태 변경 이력입니다."
            title="주문 타임라인"
          >
            {detail.events.length === 0 ? (
              <StatePanel
                description="아직 이 주문에 대한 상태 변경 기록이 없습니다."
                title="이벤트 없음"
              />
            ) : (
              <div className="timeline">
                {detail.events.map((event) => (
                  <div className="timeline__item" key={event.event_id}>
                    <div className="timeline__meta">
                      <StatusBadge value={event.status} />
                      <span>{formatTimestamp(event.occurred_at)}</span>
                    </div>
                    <strong>{humanizeEventType(event.event_type)}</strong>
                    <p>{event.reason ?? "별도로 기록된 사유는 없습니다."}</p>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
          <SectionCard
            description="이 주문에 대해 실제로 체결된 내역입니다. 부분 체결이면 여러 줄로 나뉠 수 있습니다."
            title="체결 내역"
          >
            {detail.fills.length === 0 ? (
              <StatePanel
                description="아직 이 주문에 연결된 체결 기록이 없습니다."
                title="체결 없음"
              />
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>체결 ID</th>
                      <th>시각</th>
                      <th>수량</th>
                      <th>가격</th>
                      <th>수수료</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.fills.map((fill) => (
                      <tr key={fill.fill_id}>
                        <td>{fill.fill_id}</td>
                        <td>{formatTimestamp(fill.occurred_at)}</td>
                        <td>{formatCompactDecimal(fill.quantity)}</td>
                        <td>{formatCompactDecimal(fill.price)}</td>
                        <td>{formatCompactDecimal(fill.fee)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>
      ) : null}
    </aside>
  );
}
