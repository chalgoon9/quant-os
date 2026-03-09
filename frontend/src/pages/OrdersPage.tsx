import { useState } from "react";

import { OrderDetailDrawer } from "../components/OrderDetailDrawer";
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
    <div className="page-grid page-grid--orders">
      <SectionCard eyebrow="Orders" title="Recent Orders">
        {orders.isLoading ? (
          <div className="skeleton skeleton--block" />
        ) : orders.isError ? (
          <StatePanel
            description="Order projection list could not be loaded."
            onAction={() => void orders.refetch()}
            actionLabel="Retry"
            title="Unable to load orders"
          />
        ) : orders.data && orders.data.items.length > 0 ? (
          <table className="table table--clickable">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Status</th>
                <th>Quantity</th>
                <th>Filled</th>
                <th>Updated</th>
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
        ) : (
          <StatePanel description="No order projection rows are available yet." title="No orders yet" />
        )}
      </SectionCard>

      <OrderDetailDrawer
        detail={orderDetail.data}
        isError={orderDetail.isError}
        isLoading={orderDetail.isLoading}
        onClose={() => setSelectedOrderId(null)}
      />
    </div>
  );
}
