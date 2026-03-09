import type { OrderDetailResponse } from "../lib/api";
import { formatCompactDecimal, formatTimestamp, titleCase } from "../lib/format";

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
          <p className="panel__eyebrow">Order Detail</p>
          <h2 className="panel__title">Append-only timeline</h2>
        </div>
        <button className="button button--ghost" onClick={onClose} type="button">
          Close
        </button>
      </div>
      {isLoading ? <div className="skeleton skeleton--block" /> : null}
      {isError ? (
        <StatePanel
          description="The order detail request failed. Try selecting the row again."
          title="Unable to load order"
        />
      ) : null}
      {detail ? (
        <div className="drawer__content">
          <SectionCard title={detail.projection.order_id}>
            <dl className="definition-grid">
              <div>
                <dt>Status</dt>
                <dd>
                  <StatusBadge value={detail.projection.status} />
                </dd>
              </div>
              <div>
                <dt>Intent</dt>
                <dd>{detail.projection.intent_id}</dd>
              </div>
              <div>
                <dt>Quantity</dt>
                <dd>{formatCompactDecimal(detail.projection.quantity)}</dd>
              </div>
              <div>
                <dt>Filled</dt>
                <dd>{formatCompactDecimal(detail.projection.filled_quantity)}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{formatTimestamp(detail.projection.created_at)}</dd>
              </div>
              <div>
                <dt>Updated</dt>
                <dd>{formatTimestamp(detail.projection.updated_at)}</dd>
              </div>
            </dl>
          </SectionCard>
          <SectionCard title="Event Timeline">
            {detail.events.length === 0 ? (
              <StatePanel
                description="No order events have been recorded yet."
                title="No events yet"
              />
            ) : (
              <div className="timeline">
                {detail.events.map((event) => (
                  <div className="timeline__item" key={event.event_id}>
                    <div className="timeline__meta">
                      <StatusBadge value={event.status} />
                      <span>{formatTimestamp(event.occurred_at)}</span>
                    </div>
                    <strong>{titleCase(event.event_type)}</strong>
                    <p>{event.reason ?? "No explicit reason recorded."}</p>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
          <SectionCard title="Fills">
            {detail.fills.length === 0 ? (
              <StatePanel description="No fills have been recorded yet." title="No fills yet" />
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Fill ID</th>
                    <th>Occurred</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    <th>Fee</th>
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
            )}
          </SectionCard>
        </div>
      ) : null}
    </aside>
  );
}
