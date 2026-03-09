import { useEffect, useMemo, useState } from "react";

import { IngestionForm } from "../components/IngestionForm";
import { PageIntro } from "../components/PageIntro";
import { SectionCard } from "../components/SectionCard";
import { StatePanel } from "../components/StatePanel";
import { useDatasetBars } from "../hooks/useDatasetBars";
import { useDatasets } from "../hooks/useDatasets";
import { useIngestUpbitDaily } from "../hooks/useIngestUpbitDaily";
import { formatCompactDecimal, formatTimestamp } from "../lib/format";
import type { UpbitIngestionResponse } from "../lib/api";

export function ResearchPage() {
  const datasets = useDatasets();
  const ingestion = useIngestUpbitDaily();
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [symbolFilter, setSymbolFilter] = useState("");
  const [result, setResult] = useState<UpbitIngestionResponse | null>(null);
  const datasetBars = useDatasetBars(selectedDataset, symbolFilter || undefined, 20);

  useEffect(() => {
    if (!selectedDataset && datasets.data?.items.length) {
      setSelectedDataset(datasets.data.items[0].dataset);
    }
  }, [datasets.data, selectedDataset]);

  const datasetOptions = datasets.data?.items ?? [];
  const selectedRowsLabel = useMemo(() => datasetBars.data?.items.length ?? 0, [datasetBars.data?.items.length]);

  return (
    <div className="page-stack">
      <PageIntro
        description="시장 데이터를 저장하고, 이후 전략 실행에 사용할 가격 이력을 미리 살펴보는 화면입니다."
        note="처음 사용하는 경우 이 페이지 하단의 업비트 수집부터 시작하면 됩니다."
        title="거래 전에 데이터를 준비하는 곳입니다"
      />
      <div className="page-grid page-grid--wide">
        <SectionCard
          description="저장되어 다시 사용할 수 있는 시장 데이터셋 목록입니다."
          eyebrow="리서치"
          title="데이터셋 목록"
        >
          {datasets.isLoading ? (
            <div className="skeleton skeleton--block" />
          ) : datasets.isError ? (
            <StatePanel
              description="리서치 데이터셋 목록을 불러오지 못했습니다."
              onAction={() => void datasets.refetch()}
              actionLabel="다시 시도"
              title="데이터셋을 불러올 수 없음"
            />
          ) : datasetOptions.length === 0 ? (
            <StatePanel
              description="이 페이지 아래의 수집 폼을 사용해 첫 번째 데이터셋을 만들어 보십시오."
              title="데이터셋 없음"
            />
          ) : (
            <div className="dataset-list">
              {datasetOptions.map((item) => (
                <button
                  className={`dataset-list__item${
                    selectedDataset === item.dataset ? " dataset-list__item--active" : ""
                  }`}
                  key={item.dataset}
                  onClick={() => setSelectedDataset(item.dataset)}
                  type="button"
                >
                  <strong>{item.dataset}</strong>
                  <span>레코드 {item.row_count}건</span>
                  <span>{formatTimestamp(item.latest_timestamp, "시각 정보 없음")}</span>
                </button>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard
          description="전략이나 백테스트에서 사용하기 전에 저장된 가격 이력을 미리 확인합니다."
          eyebrow="리서치"
          title="시장 데이터 미리보기"
        >
          <div className="toolbar">
            <label className="field field--inline">
              <span>선택한 데이터셋</span>
              <input readOnly value={selectedDataset ?? ""} />
            </label>
            <label className="field field--inline">
              <span>심볼 필터</span>
              <input
                onChange={(event) => setSymbolFilter(event.target.value)}
                placeholder="선택 사항"
                value={symbolFilter}
              />
            </label>
          </div>
          {!selectedDataset ? (
            <StatePanel description="왼쪽 목록에서 데이터셋을 선택하십시오." title="데이터셋 선택" />
          ) : datasetBars.isLoading ? (
            <div className="skeleton skeleton--block" />
          ) : datasetBars.isError ? (
            <StatePanel
              description="시장 데이터 미리보기를 불러오지 못했습니다."
              onAction={() => void datasetBars.refetch()}
              actionLabel="다시 시도"
              title="시장 데이터를 불러올 수 없음"
            />
          ) : datasetBars.data && datasetBars.data.items.length > 0 ? (
            <>
              <p className="panel__eyebrow">가격 레코드 {selectedRowsLabel}건</p>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>시각</th>
                      <th>시가</th>
                      <th>고가</th>
                      <th>저가</th>
                      <th>종가</th>
                      <th>거래량</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datasetBars.data.items.map((bar) => (
                      <tr key={`${bar.symbol}-${bar.timestamp}`}>
                        <td>{formatTimestamp(bar.timestamp)}</td>
                        <td>{formatCompactDecimal(bar.open)}</td>
                        <td>{formatCompactDecimal(bar.high)}</td>
                        <td>{formatCompactDecimal(bar.low)}</td>
                        <td>{formatCompactDecimal(bar.close)}</td>
                        <td>{formatCompactDecimal(bar.volume)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <StatePanel
              description="선택한 데이터셋과 심볼 필터에 맞는 기록이 없습니다. 심볼 필터를 비우거나 다른 데이터셋을 선택해 보십시오."
              title="시장 데이터 없음"
            />
          )}
        </SectionCard>

        <SectionCard
          description="업비트에서 일봉 가격 이력을 받아 리서치용 데이터셋으로 저장합니다."
          eyebrow="리서치"
          title="업비트 데이터 수집"
        >
          <IngestionForm
            errorMessage={ingestion.error instanceof Error ? ingestion.error.message : null}
            isSubmitting={ingestion.isPending}
            onSubmit={async (payload) => {
              const response = await ingestion.mutateAsync(payload);
              setResult(response);
              if (!selectedDataset) {
                setSelectedDataset(response.dataset);
              }
              return response;
            }}
            result={result}
          />
          <p className="panel__description">저장이 끝나면 위 목록에서 데이터셋을 선택해 최신 시장 데이터를 미리볼 수 있습니다.</p>
        </SectionCard>
      </div>
    </div>
  );
}
