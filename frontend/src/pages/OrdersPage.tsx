import { useState } from "react";

import { OrderDetailDrawer } from "../components/OrderDetailDrawer";
import { PageIntro } from "../components/PageIntro";
import { SectionCard } from "../components/SectionCard";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";
import { useOrderDetail } from "../hooks/useOrderDetail";
import { useOrders } from "../hooks/useOrders";
import { formatCompactDecimal, formatTimestamp } from "../lib/format";

export function OrdersPage() {
  const orders = useOrders(30);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const orderDetail = useOrderDetail(selectedOrderId);

  return (
    <div className="page-stack">
      <PageIntro
        description="최근 주문을 확인하고, 각 주문이 어떤 상태 변화를 거쳤는지와 체결 내역을 함께 보는 화면입니다."
        note="전략에서 목표 변화가 실행 단계까지 도달해 주문 기록이 남기 시작하면 이 화면에 자동으로 표시됩니다."
        title="시스템이 어떤 거래를 시도했는지 확인합니다"
      />
      <div className="page-grid page-grid--orders">
        <SectionCard
          description="최근 활동 순으로 정렬된 주문 목록입니다. 행을 누르면 상태 이력과 체결 내역을 확인할 수 있습니다."
          eyebrow="주문"
          title="최근 주문"
        >
          {orders.isLoading ? (
            <div className="skeleton skeleton--block" />
          ) : orders.isError ? (
            <StatePanel
              description="백엔드에서 주문 목록을 불러오지 못했습니다."
              onAction={() => void orders.refetch()}
              actionLabel="다시 시도"
              title="주문을 불러올 수 없음"
            />
          ) : orders.data && orders.data.items.length > 0 ? (
            <div className="table-wrap">
              <table className="table table--clickable">
                <thead>
                  <tr>
                    <th>주문 ID</th>
                    <th>심볼</th>
                    <th>방향</th>
                    <th>상태</th>
                    <th>주문 수량</th>
                    <th>체결 수량</th>
                    <th>갱신 시각</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.data.items.map((item) => (
                    <tr key={item.order_id} onClick={() => setSelectedOrderId(item.order_id)}>
                      <td>{item.order_id}</td>
                      <td>{item.symbol}</td>
                      <td>
                        <StatusBadge kind="side" value={item.side} />
                      </td>
                      <td>
                        <StatusBadge value={item.status} />
                      </td>
                      <td>{formatCompactDecimal(item.quantity)}</td>
                      <td>{formatCompactDecimal(item.filled_quantity)}</td>
                      <td>{formatTimestamp(item.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <StatePanel
              description="아직 기록된 주문이 없습니다. 시스템이 목표 변화에 따라 실제 주문을 만들면 이 목록이 채워집니다."
              title="주문 없음"
            />
          )}
        </SectionCard>

        <OrderDetailDrawer
          detail={orderDetail.data}
          isError={orderDetail.isError}
          isLoading={orderDetail.isLoading}
          onClose={() => setSelectedOrderId(null)}
        />
      </div>
    </div>
  );
}
