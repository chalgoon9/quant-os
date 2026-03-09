import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OrderDetailDrawer } from "./OrderDetailDrawer";

describe("OrderDetailDrawer", () => {
  it("renders Korean guidance for first-time readers", async () => {
    render(
      <OrderDetailDrawer
        detail={{
          projection: {
            order_id: "order_1",
            intent_id: "intent_1",
            strategy_run_id: null,
            symbol: "KRW-BTC",
            side: "buy",
            order_type: "market",
            time_in_force: "day",
            quantity: "1.0000",
            status: "filled",
            created_at: "2026-03-10T00:00:00+00:00",
            updated_at: "2026-03-10T00:01:00+00:00",
            filled_quantity: "1.0000",
            broker_order_id: null,
            last_event_at: "2026-03-10T00:01:00+00:00",
          },
          events: [],
          fills: [],
        }}
        isError={false}
        isLoading={false}
        onClose={() => {}}
      />,
    );

    expect(await screen.findByText("이 주문을 읽는 방법")).toBeInTheDocument();
    expect(
      await screen.findByText(
        "상단 요약은 현재 상태를, 타임라인은 상태 변경 이력을, 체결 내역은 실제로 나뉘어 체결된 거래 조각을 보여줍니다.",
      ),
    ).toBeInTheDocument();
    expect(await screen.findByText("주문 타임라인")).toBeInTheDocument();
    expect(await screen.findByText("체결 내역")).toBeInTheDocument();
  });
});
