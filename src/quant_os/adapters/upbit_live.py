from __future__ import annotations

from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import hmac
import json
import os
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import unquote, urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from quant_os.adapters.live import LiveAdapterBase
from quant_os.db.store import OperationalStore
from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
from quant_os.domain.ids import new_id
from quant_os.domain.models import FillEvent, OrderEvent, OrderIntent, PortfolioState, Position, SubmitResult
from quant_os.domain.types import ZERO, quantize, to_decimal
from quant_os.risk.kill_switch import KillSwitch

Transport = Callable[[str, str, dict[str, str], bytes | None], Any]


class UpbitApiError(RuntimeError):
    def __init__(self, *, name: str, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.name = name
        self.message = message
        self.status_code = status_code


class UpbitExchangeClient:
    def __init__(
        self,
        *,
        access_key: str,
        secret_key: str,
        api_base_url: str = "https://api.upbit.com",
        transport: Transport | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._access_key = access_key
        self._secret_key = secret_key
        self._api_base_url = api_base_url.rstrip("/")
        self._transport = transport or _default_transport(timeout_seconds)

    @classmethod
    def from_env(
        cls,
        *,
        access_key_env: str,
        secret_key_env: str,
        api_base_url: str,
        transport: Transport | None = None,
    ) -> "UpbitExchangeClient":
        access_key = os.environ.get(access_key_env)
        secret_key = os.environ.get(secret_key_env)
        if not access_key or not secret_key:
            raise ValueError(
                f"missing Upbit credentials in environment: {access_key_env}, {secret_key_env}"
            )
        return cls(
            access_key=access_key,
            secret_key=secret_key,
            api_base_url=api_base_url,
            transport=transport,
        )

    def get_accounts(self) -> list[dict[str, object]]:
        payload = self._request("GET", "/v1/accounts")
        if not isinstance(payload, list):
            raise ValueError("unexpected Upbit accounts payload")
        return payload

    def fetch_ticker_price(self, market: str) -> Decimal:
        payload = self._request("GET", "/v1/ticker", params={"markets": market}, authenticated=False)
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"unexpected Upbit ticker payload for market={market}")
        return to_decimal(payload[0]["trade_price"])

    def create_order(self, body: dict[str, str]) -> dict[str, object]:
        payload = self._request("POST", "/v1/orders", body=body)
        if not isinstance(payload, dict):
            raise ValueError("unexpected Upbit create order payload")
        return payload

    def cancel_order(self, *, uuid: str | None = None, identifier: str | None = None) -> dict[str, object]:
        params: dict[str, str] = {}
        if uuid is not None:
            params["uuid"] = uuid
        if identifier is not None:
            params["identifier"] = identifier
        payload = self._request("DELETE", "/v1/order", params=params)
        if not isinstance(payload, dict):
            raise ValueError("unexpected Upbit cancel payload")
        return payload

    def get_orders_by_ids(self, *, uuids: tuple[str, ...]) -> list[dict[str, object]]:
        if not uuids:
            return []
        params = {"uuids[]": list(uuids)}
        payload = self._request("GET", "/v1/orders/uuids", params=params)
        if not isinstance(payload, list):
            raise ValueError("unexpected Upbit orders payload")
        return payload

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        body: dict[str, object] | None = None,
        authenticated: bool = True,
    ) -> Any:
        query_string = _build_query_string(params=params, body=body)
        url = f"{self._api_base_url}{path}"
        if params:
            url = f"{url}?{query_string}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "quant-os/0.1.0",
        }
        request_body = json.dumps(body).encode("utf-8") if body is not None else None
        if authenticated:
            headers["Authorization"] = f"Bearer {_build_jwt(self._access_key, self._secret_key, query_string if (params or body) else None)}"
        return self._transport(method, url, headers, request_body)


class UpbitLiveAdapter(LiveAdapterBase):
    def __init__(
        self,
        initial_portfolio: PortfolioState,
        *,
        client: UpbitExchangeClient,
        store: OperationalStore | None = None,
        kill_switch: KillSwitch | None = None,
    ) -> None:
        super().__init__(initial_portfolio, store=store, kill_switch=kill_switch)
        self._client = client
        self._known_broker_to_local: dict[str, str] = {}
        self._local_to_broker: dict[str, str] = {}
        self._bootstrap_from_store()

    def submit_intent(self, intent: OrderIntent) -> SubmitResult:
        order_id = self._intent_to_order.get(intent.intent_id)
        if order_id is not None:
            if self._kill_switch is not None:
                self._kill_switch.evaluate_duplicate_intent(
                    intent_id=intent.intent_id,
                    triggered_at=self._tick(),
                )
            return SubmitResult(
                accepted=False,
                order_id=order_id,
                status=OrderStatus.PRECHECK_REJECTED,
                message="duplicate intent_id rejected",
            )

        order_id = new_id("order")
        self._intent_to_order[intent.intent_id] = order_id

        planned_event = self._state_machine.plan(intent, order_id=order_id, occurred_at=self._tick())
        self._record_order_event(planned_event)
        if self._kill_switch is not None and not self._kill_switch.can_submit_orders():
            rejected_event = self._state_machine.transition(
                order_id,
                OrderStatus.PRECHECK_REJECTED,
                occurred_at=self._tick(),
                reason="kill switch active",
            )
            self._record_order_event(rejected_event)
            return SubmitResult(
                accepted=False,
                order_id=order_id,
                status=OrderStatus.PRECHECK_REJECTED,
                message="kill switch active",
            )
        approved_event = self._state_machine.transition(order_id, OrderStatus.APPROVED, occurred_at=self._tick())
        self._record_order_event(approved_event)
        submitting_event = self._state_machine.transition(order_id, OrderStatus.SUBMITTING, occurred_at=self._tick())
        self._record_order_event(submitting_event)

        try:
            payload = self._build_create_order_payload(intent, order_id=order_id)
        except ValueError as exc:
            rejected_event = self._state_machine.transition(
                order_id,
                OrderStatus.PRECHECK_REJECTED,
                occurred_at=self._tick(),
                reason=str(exc),
            )
            self._record_order_event(rejected_event)
            return SubmitResult(
                accepted=False,
                order_id=order_id,
                status=OrderStatus.PRECHECK_REJECTED,
                message=str(exc),
            )

        try:
            remote_order = self._client.create_order(payload)
        except UpbitApiError as exc:
            rejected_event = self._state_machine.transition(
                order_id,
                OrderStatus.BROKER_REJECTED,
                occurred_at=self._tick(),
                reason=exc.message,
                raw_payload={"request": payload, "error_name": exc.name, "status_code": exc.status_code},
            )
            self._record_order_event(rejected_event)
            return SubmitResult(
                accepted=False,
                order_id=order_id,
                status=OrderStatus.BROKER_REJECTED,
                message=exc.message,
            )
        except Exception as exc:  # noqa: BLE001
            pending_event = self._state_machine.transition(
                order_id,
                OrderStatus.RECONCILE_PENDING,
                occurred_at=self._tick(),
                reason=f"submit outcome uncertain: {exc}",
                raw_payload={"request": payload},
            )
            self._record_order_event(pending_event)
            self._note_operational_failure(
                component="live.submit_order",
                error_message=str(exc),
            )
            return SubmitResult(
                accepted=False,
                order_id=order_id,
                status=OrderStatus.RECONCILE_PENDING,
                message="submit outcome uncertain",
            )

        self._apply_remote_order_snapshot(remote_order, order_id=order_id, from_submit=True)
        try:
            self._refresh_portfolio_from_accounts()
        except Exception as exc:  # noqa: BLE001
            self._transition_to_reconcile_pending(
                order_id,
                reason=f"portfolio sync failed after submit: {exc}",
                raw_payload={"request": payload, "response": remote_order},
            )
            self._note_operational_failure(
                component="live.refresh_portfolio_after_submit",
                error_message=str(exc),
            )
            return SubmitResult(
                accepted=False,
                order_id=order_id,
                status=OrderStatus.RECONCILE_PENDING,
                message="portfolio sync failed after submit",
            )
        projection = self._state_machine.get_projection(order_id)
        return SubmitResult(
            accepted=projection.status not in {OrderStatus.BROKER_REJECTED, OrderStatus.RECONCILE_PENDING},
            order_id=order_id,
            status=projection.status,
            message=None,
        )

    def cancel_order(self, order_id: str) -> None:
        broker_order_id = self._local_to_broker.get(order_id)
        if broker_order_id is None and self._store is not None:
            try:
                broker_order_id = self._store.get_order_projection(order_id).broker_order_id
            except KeyError:
                return
        if broker_order_id is None:
            return
        projection = self._ensure_hydrated(order_id)
        if projection.status in {OrderStatus.WORKING, OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED}:
            cancel_requested = self._state_machine.transition(
                order_id,
                OrderStatus.CANCEL_REQUESTED,
                occurred_at=self._tick(),
            )
            self._record_order_event(cancel_requested)
        try:
            remote_order = self._client.cancel_order(uuid=broker_order_id)
        except Exception as exc:  # noqa: BLE001
            self._transition_to_reconcile_pending(order_id, reason=f"cancel outcome uncertain: {exc}")
            self._note_operational_failure(
                component="live.cancel_order",
                error_message=str(exc),
            )
            raise RuntimeError(f"cancel outcome uncertain for order_id={order_id}") from exc
        self._apply_remote_order_snapshot(remote_order, order_id=order_id, from_submit=False)
        try:
            self._refresh_portfolio_from_accounts()
        except Exception as exc:  # noqa: BLE001
            self._transition_to_reconcile_pending(
                order_id,
                reason=f"portfolio sync failed after cancel: {exc}",
                raw_payload={"response": remote_order},
            )
            self._note_operational_failure(
                component="live.refresh_portfolio_after_cancel",
                error_message=str(exc),
            )
            raise RuntimeError(f"portfolio sync failed after cancel for order_id={order_id}") from exc

    def sync_events(self, since: datetime | None) -> tuple[OrderEvent | FillEvent, ...]:
        try:
            if self._known_broker_to_local:
                remote_orders = self._client.get_orders_by_ids(uuids=tuple(self._known_broker_to_local))
                for remote_order in remote_orders:
                    broker_order_id = str(remote_order.get("uuid", "")).strip()
                    if broker_order_id not in self._known_broker_to_local:
                        continue
                    self._apply_remote_order_snapshot(
                        remote_order,
                        order_id=self._known_broker_to_local[broker_order_id],
                        from_submit=False,
                    )
            self._refresh_portfolio_from_accounts()
        except Exception as exc:  # noqa: BLE001
            self._mark_all_open_orders_reconcile_pending(reason=f"sync failure: {exc}")
            self._note_operational_failure(
                component="live.sync_events",
                error_message=str(exc),
            )
            raise RuntimeError("live sync failed") from exc
        return super().sync_events(since)

    def get_portfolio_state(self) -> PortfolioState:
        try:
            self._refresh_portfolio_from_accounts()
        except Exception as exc:  # noqa: BLE001
            self._mark_all_open_orders_reconcile_pending(reason=f"portfolio refresh failure: {exc}")
            self._note_operational_failure(
                component="live.get_portfolio_state",
                error_message=str(exc),
            )
            raise RuntimeError("live portfolio refresh failed") from exc
        return self._portfolio

    def _build_create_order_payload(self, intent: OrderIntent, *, order_id: str) -> dict[str, str]:
        side = "bid" if intent.side is OrderSide.BUY else "ask"
        payload: dict[str, str] = {
            "market": intent.symbol,
            "side": side,
            "identifier": order_id,
        }
        if intent.order_type is OrderType.LIMIT:
            if intent.limit_price is None:
                raise ValueError("limit orders require limit_price")
            payload["ord_type"] = "limit"
            payload["volume"] = _decimal_string(intent.quantity)
            payload["price"] = _decimal_string(intent.limit_price)
            return payload

        if intent.side is OrderSide.BUY:
            price = self._portfolio.market_prices.get(intent.symbol)
            if price is None or price <= ZERO:
                price = self._client.fetch_ticker_price(intent.symbol)
            payload["ord_type"] = "price"
            payload["price"] = _decimal_string(quantize(intent.quantity * price, "0.0000"))
            return payload

        payload["ord_type"] = "market"
        payload["volume"] = _decimal_string(intent.quantity)
        return payload

    def _apply_remote_order_snapshot(self, remote_order: dict[str, object], *, order_id: str, from_submit: bool) -> None:
        projection = self._ensure_hydrated(order_id)
        broker_order_id = str(remote_order["uuid"])
        self._known_broker_to_local[broker_order_id] = order_id
        self._local_to_broker[order_id] = broker_order_id

        created_at = _parse_upbit_datetime(str(remote_order.get("created_at") or datetime.now(tz=timezone.utc).isoformat()))
        snapshot_at = _parse_upbit_datetime(
            str(remote_order.get("updated_at") or remote_order.get("created_at") or datetime.now(tz=timezone.utc).isoformat())
        )
        if projection.broker_order_id is None:
            acknowledged = self._state_machine.transition(
                order_id,
                OrderStatus.ACKNOWLEDGED,
                occurred_at=max(self._tick(), created_at),
                broker_order_id=broker_order_id,
                reason="broker acknowledged order",
                raw_payload=remote_order,
            )
            self._record_order_event(acknowledged)
            projection = self._state_machine.get_projection(order_id)

        target_status = _map_upbit_state(remote_order, projection)
        if target_status is OrderStatus.WORKING and projection.status is OrderStatus.ACKNOWLEDGED:
            working = self._state_machine.transition(
                order_id,
                OrderStatus.WORKING,
                occurred_at=max(self._tick(), snapshot_at, projection.last_event_at or created_at),
                raw_payload=remote_order if from_submit else None,
            )
            self._record_order_event(working)
            projection = self._state_machine.get_projection(order_id)

        self._sync_fill_delta(order_id=order_id, remote_order=remote_order)
        projection = self._state_machine.get_projection(order_id)
        if target_status != projection.status:
            event = self._state_machine.transition(
                order_id,
                target_status,
                occurred_at=max(self._tick(), snapshot_at, projection.last_event_at or snapshot_at),
                broker_order_id=broker_order_id,
                raw_payload=remote_order if target_status in {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.CANCELLED_PARTIAL, OrderStatus.RECONCILE_PENDING} else None,
            )
            self._record_order_event(event)

    def _sync_fill_delta(self, *, order_id: str, remote_order: dict[str, object]) -> None:
        projection = self._ensure_hydrated(order_id)
        remote_executed = quantize(remote_to_decimal(remote_order.get("executed_volume")), "0.0000")
        local_filled = quantize(projection.filled_quantity, "0.0000")
        delta = quantize(remote_executed - local_filled, "0.0000")
        if delta <= ZERO:
            return

        total_paid_fee = quantize(remote_to_decimal(remote_order.get("paid_fee")), "0.0000")
        local_fee = sum((fill.fee for fill in self._state_machine.fills(order_id)), start=ZERO)
        fee_delta = quantize(max(ZERO, total_paid_fee - local_fee), "0.0000")

        avg_price = remote_to_decimal(remote_order.get("avg_price") or remote_order.get("price"))
        occurred_at = _parse_upbit_datetime(str(remote_order.get("updated_at") or remote_order.get("created_at") or datetime.now(tz=timezone.utc).isoformat()))
        projection = self._state_machine.get_projection(order_id)
        fill = FillEvent(
            fill_id=new_id("fill"),
            order_id=order_id,
            intent_id=projection.intent_id,
            strategy_run_id=projection.strategy_run_id,
            symbol=projection.symbol,
            side=projection.side,
            quantity=delta,
            price=quantize(avg_price, "0.0000"),
            fee=fee_delta,
            tax=ZERO,
            occurred_at=max(self._tick(), occurred_at),
            broker_fill_id=f"{self._local_to_broker[order_id]}:{remote_executed}",
            raw_payload=remote_order,
        )
        self._record_fill(fill)

    def _refresh_portfolio_from_accounts(self) -> None:
        accounts = self._client.get_accounts()
        cash_balance = ZERO
        positions: list[Position] = []
        market_prices = dict(self._portfolio.market_prices)
        for item in accounts:
            currency = str(item["currency"]).upper()
            balance = remote_to_decimal(item["balance"])
            locked = remote_to_decimal(item.get("locked"))
            total_quantity = quantize(balance + locked, "0.0000")
            avg_buy_price = remote_to_decimal(item.get("avg_buy_price"))
            if currency == self._portfolio.base_currency.upper():
                cash_balance = quantize(total_quantity, "0.0000")
                continue
            symbol = f"{str(item.get('unit_currency', self._portfolio.base_currency)).upper()}-{currency}"
            market_prices.setdefault(symbol, avg_buy_price if avg_buy_price > ZERO else None)
            positions.append(
                Position(
                    symbol=symbol,
                    quantity=total_quantity,
                    average_cost=quantize(avg_buy_price, "0.0000"),
                    market_price=market_prices.get(symbol),
                )
            )
        nav = quantize(
            cash_balance
            + sum(
                position.quantity * (position.market_price or position.average_cost)
                for position in positions
            ),
            "0.0000",
        )
        self._portfolio = PortfolioState(
            as_of=self._tick(),
            base_currency=self._portfolio.base_currency,
            cash_balance=cash_balance,
            net_asset_value=max(nav, Decimal("0.0001")),
            positions=tuple(positions),
            market_prices={key: value for key, value in market_prices.items() if value is not None},
        )

    def _transition_to_reconcile_pending(
        self,
        order_id: str,
        *,
        reason: str,
        raw_payload: dict[str, object] | None = None,
    ) -> None:
        projection = self._ensure_hydrated(order_id)
        if projection.status in {
            OrderStatus.RECONCILE_PENDING,
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.CANCELLED_PARTIAL,
            OrderStatus.EXPIRED,
            OrderStatus.BROKER_REJECTED,
            OrderStatus.PRECHECK_REJECTED,
            OrderStatus.BUSTED,
        }:
            return
        event = self._state_machine.transition(
            order_id,
            OrderStatus.RECONCILE_PENDING,
            occurred_at=self._tick(),
            broker_order_id=projection.broker_order_id,
            reason=reason,
            raw_payload=raw_payload,
        )
        self._record_order_event(event)

    def _mark_all_open_orders_reconcile_pending(self, *, reason: str) -> None:
        for projection in self._state_machine.projections():
            if projection.status in {
                OrderStatus.PLANNED,
                OrderStatus.APPROVED,
                OrderStatus.SUBMITTING,
                OrderStatus.ACKNOWLEDGED,
                OrderStatus.WORKING,
                OrderStatus.PARTIALLY_FILLED,
                OrderStatus.CANCEL_REQUESTED,
            }:
                self._transition_to_reconcile_pending(projection.order_id, reason=reason)

    def _bootstrap_from_store(self) -> None:
        if self._store is None:
            return
        history: list[OrderEvent | FillEvent] = []
        for projection in self._store.list_recent_orders(limit=500):
            if projection.broker_order_id is None:
                continue
            if projection.broker_order_id.startswith(("paper-", "shadow-")):
                continue
            events = tuple(self._store.list_order_events(projection.order_id))
            fills = tuple(self._store.list_fills(projection.order_id))
            self._state_machine.hydrate_projection(projection, events=events, fills=fills)
            self._intent_to_order[projection.intent_id] = projection.order_id
            self._known_broker_to_local[projection.broker_order_id] = projection.order_id
            self._local_to_broker[projection.order_id] = projection.broker_order_id
            history.extend(events)
            history.extend(fills)
        self._event_log = list(sorted(history, key=lambda event: event.occurred_at))

    def _ensure_hydrated(self, order_id: str):
        try:
            return self._state_machine.get_projection(order_id)
        except KeyError:
            if self._store is None:
                raise
            projection = self._store.get_order_projection(order_id)
            self._state_machine.hydrate_projection(
                projection,
                events=tuple(self._store.list_order_events(order_id)),
                fills=tuple(self._store.list_fills(order_id)),
            )
            return self._state_machine.get_projection(order_id)


def _map_upbit_state(remote_order: dict[str, object], projection) -> OrderStatus:
    state = str(remote_order.get("state", "")).lower()
    remaining_volume = quantize(remote_to_decimal(remote_order.get("remaining_volume")), "0.0000")
    executed_volume = quantize(remote_to_decimal(remote_order.get("executed_volume")), "0.0000")
    if state in {"wait", "watch"}:
        return OrderStatus.PARTIALLY_FILLED if executed_volume > ZERO else OrderStatus.WORKING
    if state == "done":
        return OrderStatus.FILLED
    if state == "cancel":
        return OrderStatus.CANCELLED_PARTIAL if executed_volume > ZERO and remaining_volume > ZERO else OrderStatus.CANCELLED
    return OrderStatus.RECONCILE_PENDING


def remote_to_decimal(value: object | None) -> Decimal:
    if value in (None, "", "0", 0):
        return ZERO
    return to_decimal(value)


def _parse_upbit_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


def _build_jwt(access_key: str, secret_key: str, query_string: str | None) -> str:
    header = {"alg": "HS512", "typ": "JWT"}
    payload: dict[str, object] = {
        "access_key": access_key,
        "nonce": str(uuid4()),
    }
    if query_string:
        payload["query_hash"] = hashlib.sha512(query_string.encode("utf-8")).hexdigest()
        payload["query_hash_alg"] = "SHA512"
    signing_input = f"{_b64json(header)}.{_b64json(payload)}".encode("utf-8")
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha512).digest()
    return f"{signing_input.decode('utf-8')}.{_b64(signature)}"


def _b64json(payload: dict[str, object]) -> str:
    return _b64(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _b64(raw: bytes) -> str:
    return urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _build_query_string(*, params: dict[str, object] | None, body: dict[str, object] | None) -> str:
    source = params if params is not None else body
    if not source:
        return ""
    flattened: list[tuple[str, str]] = []
    for key, value in source.items():
        if isinstance(value, list):
            flattened.extend((key, str(item)) for item in value)
        else:
            flattened.append((key, str(value)))
    return unquote(urlencode(flattened, doseq=True))


def _default_transport(timeout_seconds: float) -> Transport:
    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> Any:
        request = Request(url, method=method, headers=headers, data=body)
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            payload = json.loads(exc.read().decode("utf-8"))
            error = payload.get("error", {})
            raise UpbitApiError(
                name=str(error.get("name", "upbit_api_error")),
                message=str(error.get("message", f"Upbit API request failed: {exc.code}")),
                status_code=exc.code,
            ) from exc

    return transport


def _decimal_string(value: Decimal) -> str:
    return format(quantize(value, "0.0000"), "f")
