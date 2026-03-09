import { useEffect, useMemo, useState } from "react";

import { IngestionForm } from "../components/IngestionForm";
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
  const selectedRowsLabel = useMemo(
    () => datasetBars.data?.items.length ?? 0,
    [datasetBars.data?.items.length],
  );

  return (
    <div className="page-grid page-grid--wide">
      <SectionCard eyebrow="Research" title="Dataset List">
        {datasets.isLoading ? (
          <div className="skeleton skeleton--block" />
        ) : datasets.isError ? (
          <StatePanel
            description="Research datasets could not be loaded."
            onAction={() => void datasets.refetch()}
            actionLabel="Retry"
            title="Unable to load datasets"
          />
        ) : datasetOptions.length === 0 ? (
          <StatePanel description="Run an ingestion job to create a dataset." title="No datasets yet" />
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
                <span>{item.row_count} rows</span>
                <span>{formatTimestamp(item.latest_timestamp, "No timestamp")}</span>
              </button>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard eyebrow="Research" title="Bars Preview">
        <div className="toolbar">
          <label className="field field--inline">
            <span>Selected dataset</span>
            <input readOnly value={selectedDataset ?? ""} />
          </label>
          <label className="field field--inline">
            <span>Symbol filter</span>
            <input
              onChange={(event) => setSymbolFilter(event.target.value)}
              placeholder="Optional"
              value={symbolFilter}
            />
          </label>
        </div>
        {!selectedDataset ? (
          <StatePanel description="Choose a dataset from the list." title="Select a dataset" />
        ) : datasetBars.isLoading ? (
          <div className="skeleton skeleton--block" />
        ) : datasetBars.isError ? (
          <StatePanel
            description="Bars preview could not be loaded."
            onAction={() => void datasetBars.refetch()}
            actionLabel="Retry"
            title="Unable to load bars"
          />
        ) : datasetBars.data && datasetBars.data.items.length > 0 ? (
          <>
            <p className="panel__eyebrow">{selectedRowsLabel} rows loaded</p>
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Open</th>
                  <th>High</th>
                  <th>Low</th>
                  <th>Close</th>
                  <th>Volume</th>
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
          </>
        ) : (
          <StatePanel description="No rows matched this dataset and symbol filter." title="No bars found" />
        )}
      </SectionCard>

      <SectionCard eyebrow="Research" title="Upbit Ingestion">
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
      </SectionCard>
    </div>
  );
}
