import { useState } from "react";

import type { UpbitIngestionResponse } from "../lib/api";

type IngestionFormProps = {
  onSubmit: (payload: {
    market: string;
    count: number;
    dataset?: string;
  }) => Promise<UpbitIngestionResponse>;
  isSubmitting: boolean;
  result: UpbitIngestionResponse | null;
  errorMessage: string | null;
};

export function IngestionForm({
  onSubmit,
  isSubmitting,
  result,
  errorMessage,
}: IngestionFormProps) {
  const [market, setMarket] = useState("KRW-BTC");
  const [count, setCount] = useState("30");
  const [dataset, setDataset] = useState("");

  return (
    <form
      className="ingestion-form"
      onSubmit={async (event) => {
        event.preventDefault();
        await onSubmit({
          market,
          count: Number(count),
          dataset: dataset || undefined,
        });
      }}
    >
      <label className="field">
        <span>Market</span>
        <input onChange={(event) => setMarket(event.target.value)} value={market} />
      </label>
      <label className="field">
        <span>Count</span>
        <input
          min="1"
          onChange={(event) => setCount(event.target.value)}
          type="number"
          value={count}
        />
      </label>
      <label className="field">
        <span>Dataset</span>
        <input
          onChange={(event) => setDataset(event.target.value)}
          placeholder="Optional"
          value={dataset}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Fetching..." : "Fetch Daily Bars"}
      </button>
      {errorMessage ? <p className="form-error">{errorMessage}</p> : null}
      {result ? (
        <div className="result-card">
          <strong>{result.market}</strong>
          <p>{result.dataset}</p>
          <p>{result.path}</p>
        </div>
      ) : null}
    </form>
  );
}
