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
        <span>마켓 심볼</span>
        <input onChange={(event) => setMarket(event.target.value)} value={market} />
        <small className="field__hint">예시: `KRW-BTC`, `KRW-ETH`.</small>
      </label>
      <label className="field">
        <span>개수(일봉)</span>
        <input
          min="1"
          onChange={(event) => setCount(event.target.value)}
          type="number"
          value={count}
        />
        <small className="field__hint">
          불러올 일봉 개수입니다. `30`이면 최근 30개 일봉을 가져옵니다.
        </small>
      </label>
      <label className="field">
        <span>데이터셋 이름(선택)</span>
        <input
          onChange={(event) => setDataset(event.target.value)}
          placeholder="비워 두면 자동으로 이름을 정합니다"
          value={dataset}
        />
        <small className="field__hint">리서치와 백테스트에서 다시 사용할 저장 이름입니다.</small>
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "불러오는 중..." : "일봉 데이터 저장"}
      </button>
      {errorMessage ? <p className="form-error">{errorMessage}</p> : null}
      {result ? (
        <div className="result-card">
          <strong>{result.market} 저장 완료</strong>
          <p>데이터셋: {result.dataset}</p>
          <p>경로: {result.path}</p>
        </div>
      ) : null}
    </form>
  );
}
