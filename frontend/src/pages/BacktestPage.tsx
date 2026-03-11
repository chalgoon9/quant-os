import { useEffect, useMemo, useState } from "react";

import { KpiCard } from "../components/KpiCard";
import { PageIntro } from "../components/PageIntro";
import { SectionCard } from "../components/SectionCard";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";
import { useBacktestCompare } from "../hooks/useBacktestCompare";
import { useBacktestRunDetail } from "../hooks/useBacktestRunDetail";
import { useBacktestRuns } from "../hooks/useBacktestRuns";
import { useStrategies } from "../hooks/useStrategies";
import {
  formatCompactDecimal,
  formatDecimal,
  formatPercent,
  formatTimestamp,
  humanizeStrategyKind,
} from "../lib/format";

export function BacktestPage() {
  const strategies = useStrategies();
  const [strategyId, setStrategyId] = useState("");
  const [datasetFilter, setDatasetFilter] = useState("");
  const [profileFilter, setProfileFilter] = useState("");
  const runs = useBacktestRuns({
    strategyId: strategyId || undefined,
    dataset: datasetFilter || undefined,
    profileId: profileFilter || undefined,
    limit: 30,
  });
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const detail = useBacktestRunDetail(selectedRunId);
  const compare = useBacktestCompare(compareIds);
  const latestPositionSnapshot = detail.data?.position_path.at(-1) ?? null;

  useEffect(() => {
    if (!runs.data?.items.length) {
      setSelectedRunId(null);
      setCompareIds([]);
      return;
    }
    const runIds = new Set(runs.data.items.map((item) => item.run_id));
    setSelectedRunId((current) => (current && runIds.has(current) ? current : runs.data.items[0].run_id));
    setCompareIds((current) => current.filter((item) => runIds.has(item)));
  }, [runs.data]);

  const selectedRun = useMemo(
    () => runs.data?.items.find((item) => item.run_id === selectedRunId) ?? null,
    [runs.data, selectedRunId],
  );
  const datasetOptions = useMemo(
    () =>
      Array.from(
        new Set(
          (runs.data?.items ?? [])
            .map((item) => item.dataset)
            .filter((item): item is string => Boolean(item)),
        ),
      ).sort(),
    [runs.data],
  );
  const profileOptions = useMemo(
    () =>
      Array.from(
        new Set(
          (runs.data?.items ?? [])
            .map((item) => item.profile_id)
            .filter((item): item is string => Boolean(item)),
        ),
      ).sort(),
    [runs.data],
  );

  function toggleCompare(runId: string) {
    setCompareIds((current) =>
      current.includes(runId) ? current.filter((item) => item !== runId) : current.length >= 3 ? [...current.slice(1), runId] : [...current, runId],
    );
  }

  function resetFilters() {
    setStrategyId("");
    setDatasetFilter("");
    setProfileFilter("");
  }

  function formatParameterValue(value: unknown) {
    if (value === null || value === undefined) {
      return "-";
    }
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      return String(value);
    }
    return JSON.stringify(value, null, 2);
  }

  return (
    <div className="page-stack">
      <PageIntro
        title="여러 백테스트 실행을 비교합니다"
        description="전략, 데이터셋, 비용 프로파일별로 저장된 백테스트 실행을 목록으로 보고, 하나를 자세히 열거나 여러 개를 비교하는 화면입니다."
        note="기존 최신 결과도 유지되지만, 이 화면에서는 최근 실행 목록과 상세 기록을 함께 살펴볼 수 있습니다."
      />

      <SectionCard
        eyebrow="백테스트 탐색기"
        title="실행 필터"
        description="전략, 데이터셋, 프로파일로 목록을 좁힐 수 있습니다. 필터를 바꾸면 최신 순으로 다시 조회합니다."
      >
        <div className="toolbar">
          <label className="field field--inline">
            <span>전략</span>
            <select value={strategyId} onChange={(event) => setStrategyId(event.target.value)}>
              <option value="">전체 전략</option>
              {(strategies.data?.items ?? []).map((item) => (
                <option key={item.strategy_id} value={item.strategy_id}>
                  {item.strategy_id}
                </option>
              ))}
            </select>
          </label>
          <label className="field field--inline">
            <span>데이터셋</span>
            <input
              list="backtest-dataset-options"
              onChange={(event) => setDatasetFilter(event.target.value)}
              placeholder="예: krx_etf_daily"
              value={datasetFilter}
            />
            <datalist id="backtest-dataset-options">
              {datasetOptions.map((item) => (
                <option key={item} value={item} />
              ))}
            </datalist>
          </label>
          <label className="field field--inline">
            <span>프로파일</span>
            <input
              list="backtest-profile-options"
              onChange={(event) => setProfileFilter(event.target.value)}
              placeholder="예: baseline"
              value={profileFilter}
            />
            <datalist id="backtest-profile-options">
              {profileOptions.map((item) => (
                <option key={item} value={item} />
              ))}
            </datalist>
          </label>
          <button className="button button--ghost" onClick={resetFilters} type="button">
            필터 초기화
          </button>
        </div>
      </SectionCard>

      <div className="page-grid page-grid--backtests">
        <SectionCard
          eyebrow="실행 목록"
          title="저장된 백테스트"
          description="행을 누르면 상세를 열고, 체크박스로 비교 대상을 최대 3개까지 고를 수 있습니다."
        >
          {runs.isLoading ? (
            <div className="skeleton skeleton--block" />
          ) : runs.isError ? (
            <StatePanel
              title="실행 목록을 불러올 수 없음"
              description="백엔드에서 백테스트 목록을 불러오지 못했습니다."
              actionLabel="다시 시도"
              onAction={() => void runs.refetch()}
            />
          ) : runs.data && runs.data.items.length > 0 ? (
            <div className="table-wrap">
              <table className="table table--clickable">
                <thead>
                  <tr>
                    <th>비교</th>
                    <th>전략</th>
                    <th>데이터셋</th>
                    <th>프로파일</th>
                    <th>상태</th>
                    <th>수익률</th>
                    <th>거래 수</th>
                    <th>실행 시각</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.data.items.map((item) => (
                    <tr
                      className={item.run_id === selectedRunId ? "table__row--selected" : undefined}
                      key={item.run_id}
                      onClick={() => setSelectedRunId(item.run_id)}
                    >
                      <td onClick={(event) => event.stopPropagation()}>
                        <input
                          aria-label={`${item.run_id} 비교 선택`}
                          checked={compareIds.includes(item.run_id)}
                          onChange={() => toggleCompare(item.run_id)}
                          type="checkbox"
                        />
                      </td>
                      <td>
                        <div className="stack-sm">
                          <strong>{item.strategy_id ?? item.strategy_name}</strong>
                          <span className="muted-text">{item.strategy_name}</span>
                        </div>
                      </td>
                      <td>{item.dataset ?? "-"}</td>
                      <td>{item.profile_id ?? "-"}</td>
                      <td>
                        <StatusBadge value={item.status} />
                      </td>
                      <td>{formatPercent(item.total_return)}</td>
                      <td>{item.trade_count ?? "-"}</td>
                      <td>{formatTimestamp(item.started_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <StatePanel
              title="실행 목록이 비어 있음"
              description="아직 catalog에 저장된 백테스트가 없습니다. 먼저 CLI에서 run-backtest를 실행해 결과를 쌓아 보십시오."
            />
          )}
        </SectionCard>

        <SectionCard
          eyebrow="상세 보기"
          title="선택한 실행"
          description="한 번 선택한 백테스트의 핵심 지표, 자산 곡선, 최근 거래를 확인합니다."
        >
          {!selectedRunId ? (
            <StatePanel
              title="선택된 실행 없음"
              description="왼쪽 목록에서 실행 하나를 선택하면 상세 정보가 여기에 나타납니다."
            />
          ) : detail.isLoading ? (
            <div className="stack-md">
              <div className="skeleton skeleton--card" />
              <div className="skeleton skeleton--block" />
            </div>
          ) : detail.isError ? (
            <StatePanel
              title="상세 정보를 불러올 수 없음"
              description="선택한 실행의 artifact 또는 상세 요약을 읽지 못했습니다."
              actionLabel="다시 시도"
              onAction={() => void detail.refetch()}
            />
          ) : detail.data ? (
            <div className="stack-md">
              <div className="inline-list">
                <strong>{detail.data.summary.strategy_id}</strong>
                <span>{humanizeStrategyKind(detail.data.summary.strategy_kind)}</span>
                <span>버전 {detail.data.summary.strategy_version}</span>
                <span>{detail.data.summary.dataset}</span>
                <span>프로파일 {detail.data.summary.profile_id}</span>
              </div>
              <div className="kpi-grid kpi-grid--backtests">
                <KpiCard label="최종 NAV" value={formatDecimal(detail.data.summary.final_nav)} rawValue={detail.data.summary.final_nav} />
                <KpiCard label="총 수익률" value={formatPercent(detail.data.summary.total_return)} rawValue={detail.data.summary.total_return} />
                <KpiCard label="최대 낙폭" value={formatPercent(detail.data.summary.max_drawdown)} rawValue={detail.data.summary.max_drawdown} />
                <KpiCard label="누적 회전율" value={formatPercent(detail.data.summary.total_turnover)} rawValue={detail.data.summary.total_turnover} />
                <KpiCard label="거래 수" value={String(detail.data.summary.trade_count)} />
                <KpiCard label="초기 자금" value={formatDecimal(detail.data.summary.initial_cash)} rawValue={detail.data.summary.initial_cash} />
                <KpiCard label="총 거래대금" value={formatDecimal(detail.data.summary.total_traded_notional)} rawValue={detail.data.summary.total_traded_notional} />
                <KpiCard label="수수료 합계" value={formatDecimal(detail.data.summary.total_commission)} rawValue={detail.data.summary.total_commission} />
                <KpiCard label="세금 합계" value={formatDecimal(detail.data.summary.total_tax)} rawValue={detail.data.summary.total_tax} />
                <KpiCard label="슬리피지 비용" value={formatDecimal(detail.data.summary.total_slippage_cost)} rawValue={detail.data.summary.total_slippage_cost} />
              </div>
              <dl className="definition-grid">
                <div>
                  <dt>실행 ID</dt>
                  <dd>{detail.data.summary.run_id}</dd>
                </div>
                <div>
                  <dt>생성 시각</dt>
                  <dd>{formatTimestamp(detail.data.summary.generated_at)}</dd>
                </div>
                <div>
                  <dt>마지막 기준 시각</dt>
                  <dd>{formatTimestamp(detail.data.summary.as_of)}</dd>
                </div>
                <div>
                  <dt>사용 심볼</dt>
                  <dd>{detail.data.summary.loaded_symbols.join(", ") || "-"}</dd>
                </div>
              </dl>

              <div className="stack-sm">
                <strong>최근 자산 곡선</strong>
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
                      {detail.data.equity_curve.slice(-10).map((point) => (
                        <tr key={point.timestamp}>
                          <td>{formatTimestamp(point.timestamp)}</td>
                          <td>{formatDecimal(point.nav)}</td>
                          <td>{formatDecimal(point.cash)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="stack-sm">
                <strong>최근 낙폭 경로</strong>
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>시각</th>
                        <th>낙폭</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.data.drawdown_curve.slice(-10).map((point) => (
                        <tr key={point.timestamp}>
                          <td>{formatTimestamp(point.timestamp)}</td>
                          <td>{formatPercent(point.drawdown)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="stack-sm">
                <strong>마지막 포지션 스냅샷</strong>
                {latestPositionSnapshot && latestPositionSnapshot.positions.length > 0 ? (
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>심볼</th>
                          <th>수량</th>
                          <th>가격</th>
                          <th>평가금액</th>
                          <th>비중</th>
                        </tr>
                      </thead>
                      <tbody>
                        {latestPositionSnapshot.positions.map((position) => (
                          <tr key={position.symbol}>
                            <td>{position.symbol}</td>
                            <td>{formatCompactDecimal(position.quantity)}</td>
                            <td>{formatCompactDecimal(position.market_price)}</td>
                            <td>{formatDecimal(position.market_value)}</td>
                            <td>{formatPercent(position.weight)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <StatePanel
                    title="포지션 스냅샷 없음"
                    description="이 실행 시점에는 보유 포지션이 없었습니다."
                  />
                )}
              </div>

              <div className="stack-sm">
                <strong>최근 거래</strong>
                {detail.data.trades.length > 0 ? (
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>시각</th>
                          <th>심볼</th>
                          <th>방향</th>
                          <th>수량</th>
                          <th>가격</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.data.trades.slice(-10).map((trade, index) => (
                          <tr key={`${trade.timestamp}-${trade.symbol}-${index}`}>
                            <td>{formatTimestamp(trade.timestamp)}</td>
                            <td>{trade.symbol}</td>
                            <td>
                              <StatusBadge kind="side" value={trade.side} />
                            </td>
                            <td>{formatCompactDecimal(trade.quantity)}</td>
                            <td>{formatCompactDecimal(trade.price)}</td>
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
                )}
              </div>

              <div className="stack-sm">
                <strong>실행 파라미터</strong>
                {detail.data.parameter_report ? (
                  <div className="code-block">
                    <pre>{formatParameterValue(detail.data.parameter_report)}</pre>
                  </div>
                ) : (
                  <StatePanel
                    title="파라미터 리포트 없음"
                    description="이 실행에는 별도의 파라미터 리포트가 저장되지 않았습니다."
                  />
                )}
              </div>
            </div>
          ) : null}
        </SectionCard>
      </div>

      <SectionCard
        eyebrow="실행 비교"
        title="비교 선택"
        description="목록에서 2개 이상 선택하면 주요 지표를 한 표로 비교합니다. 한 번에 최대 3개까지 비교합니다."
      >
        {compareIds.length < 2 ? (
          <StatePanel
            title="비교 대상이 부족함"
            description="왼쪽 실행 목록에서 두 개 이상 체크하면 수익률, 낙폭, 거래 수를 한 번에 비교할 수 있습니다."
          />
        ) : compare.isLoading ? (
          <div className="skeleton skeleton--block" />
        ) : compare.isError ? (
          <StatePanel
            title="비교 결과를 불러올 수 없음"
            description="선택한 실행의 비교 요약을 가져오지 못했습니다."
            actionLabel="다시 시도"
            onAction={() => void compare.refetch()}
          />
        ) : compare.data ? (
          <div className="stack-md">
            <div className="inline-list">
              {compareIds.map((item) => (
                <span className="badge badge--neutral" key={item}>
                  {item}
                </span>
              ))}
            </div>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>전략</th>
                    <th>프로파일</th>
                    <th>데이터셋</th>
                    <th>최종 NAV</th>
                    <th>총 수익률</th>
                    <th>최대 낙폭</th>
                    <th>누적 회전율</th>
                    <th>거래 수</th>
                  </tr>
                </thead>
                <tbody>
                  {compare.data.items.map((item) => (
                    <tr key={item.run_id}>
                      <td>
                        <div className="stack-sm">
                          <strong>{item.strategy_id}</strong>
                          <span className="muted-text">{item.strategy_name}</span>
                        </div>
                      </td>
                      <td>{item.profile_id}</td>
                      <td>{item.dataset}</td>
                      <td>{formatDecimal(item.final_nav)}</td>
                      <td>{formatPercent(item.total_return)}</td>
                      <td>{formatPercent(item.max_drawdown)}</td>
                      <td>{formatPercent(item.total_turnover)}</td>
                      <td>{item.trade_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </SectionCard>

      {selectedRun ? (
        <p className="muted-text">
          현재 선택된 실행: <strong>{selectedRun.run_id}</strong>
        </p>
      ) : null}
    </div>
  );
}
