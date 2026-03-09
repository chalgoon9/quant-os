import { KpiCard } from "../components/KpiCard";
import { PageIntro } from "../components/PageIntro";
import { SectionCard } from "../components/SectionCard";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";
import { useBacktestLatest } from "../hooks/useBacktestLatest";
import { formatCompactDecimal, formatDecimal, formatPercent, formatTimestamp } from "../lib/format";

export function BacktestPage() {
  const backtest = useBacktestLatest();

  return (
    <div className="page-stack">
      <PageIntro
        title="전략 결과를 확인합니다"
        description="가장 최근에 실행한 백테스트 결과를 요약해서 보여주는 화면입니다."
        note="아직 결과가 없으면 먼저 터미널에서 `uv run quant-os run-backtest --config conf/base.yaml --dataset <dataset>` 명령을 실행하십시오."
      />
      <div className="page-grid page-grid--wide">
        <SectionCard
          eyebrow="백테스트"
          title="실행 요약"
          description="전략, 데이터셋, 수익률, 낙폭, 거래 수를 한 번에 확인합니다."
          className="panel--span-full"
        >
          {backtest.isLoading ? (
            <div className="kpi-grid">
              {Array.from({ length: 5 }).map((_, index) => (
                <div className="skeleton skeleton--card" key={index} />
              ))}
            </div>
          ) : backtest.isError ? (
            <StatePanel
              title="백테스트 결과 없음"
              description="아직 저장된 백테스트 결과가 없습니다. 먼저 run-backtest 명령으로 결과를 생성해 보십시오."
            />
          ) : backtest.data ? (
            <div className="stack-md">
              <div className="inline-list">
                <strong>{backtest.data.summary.strategy_name}</strong>
                <span>{backtest.data.summary.dataset}</span>
                <span>실행 시각 {formatTimestamp(backtest.data.summary.generated_at)}</span>
              </div>
              <div className="kpi-grid">
                <KpiCard
                  label="최종 NAV"
                  value={formatDecimal(backtest.data.summary.final_nav)}
                  rawValue={backtest.data.summary.final_nav}
                />
                <KpiCard
                  label="총 수익률"
                  value={formatPercent(backtest.data.summary.total_return)}
                  rawValue={backtest.data.summary.total_return}
                />
                <KpiCard
                  label="최대 낙폭"
                  value={formatPercent(backtest.data.summary.max_drawdown)}
                  rawValue={backtest.data.summary.max_drawdown}
                />
                <KpiCard
                  label="거래 수"
                  value={String(backtest.data.summary.trade_count)}
                />
                <KpiCard
                  label="초기 자금"
                  value={formatDecimal(backtest.data.summary.initial_cash)}
                  rawValue={backtest.data.summary.initial_cash}
                />
              </div>
              <div className="inline-list">
                <StatusBadge value="matched" />
                <span>사용 심볼: {backtest.data.summary.loaded_symbols.join(", ") || "-"}</span>
                {backtest.data.summary.missing_symbols.length > 0 ? (
                  <span>누락 심볼: {backtest.data.summary.missing_symbols.join(", ")}</span>
                ) : null}
              </div>
            </div>
          ) : null}
        </SectionCard>

        <SectionCard
          eyebrow="백테스트"
          title="자산 곡선"
          description="최근 자산 곡선 일부를 표로 보여줍니다."
        >
          {backtest.data ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>시각</th>
                    <th>NAV</th>
                    <th>현금</th>
                  </tr>
                </thead>
                <tbody>
                  {backtest.data.equity_curve.slice(-20).map((point) => (
                    <tr key={point.timestamp}>
                      <td>{formatTimestamp(point.timestamp)}</td>
                      <td>{formatDecimal(point.nav)}</td>
                      <td>{formatDecimal(point.cash)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <StatePanel
              title="자산 곡선 없음"
              description="백테스트를 실행하면 자산 곡선이 이곳에 표시됩니다."
            />
          )}
        </SectionCard>

        <SectionCard
          eyebrow="백테스트"
          title="최근 거래"
          description="최근 발생한 거래 내역 일부를 보여줍니다."
        >
          {backtest.data ? (
            backtest.data.trades.length > 0 ? (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>시각</th>
                      <th>심볼</th>
                      <th>방향</th>
                      <th>수량</th>
                      <th>가격</th>
                      <th>금액</th>
                    </tr>
                  </thead>
                  <tbody>
                    {backtest.data.trades.slice(-20).map((trade, index) => (
                      <tr key={`${trade.timestamp}-${trade.symbol}-${index}`}>
                        <td>{formatTimestamp(trade.timestamp)}</td>
                        <td>{trade.symbol}</td>
                        <td>
                          <StatusBadge kind="side" value={trade.side} />
                        </td>
                        <td>{formatCompactDecimal(trade.quantity)}</td>
                        <td>{formatCompactDecimal(trade.price)}</td>
                        <td>{formatCompactDecimal(trade.notional)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <StatePanel
                title="거래 없음"
                description="이 실행에서는 거래가 발생하지 않았습니다."
              />
            )
          ) : (
            <StatePanel
              title="거래 내역 없음"
              description="백테스트 실행 후 거래가 있으면 이곳에 표시됩니다."
            />
          )}
        </SectionCard>
      </div>
    </div>
  );
}
