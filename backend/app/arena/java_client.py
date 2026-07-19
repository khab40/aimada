import asyncio
import json
from urllib import error, parse, request

from app.schemas.arena import ArenaState, AttackTrackerState, ExchangeEventReplay, Incident


class JavaArenaClient:
    """Thin retained-Python adapter to the Java-owned live arena."""

    def __init__(self, base_url: str, timeout_seconds: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def state(self) -> ArenaState:
        return ArenaState.model_validate(self._request("GET", "/api/arena/state"))

    async def get_state(self) -> ArenaState:
        return await asyncio.to_thread(lambda: self.state)

    async def start(self) -> ArenaState:
        return await self._arena_state("/api/simulation/start")

    async def pause(self) -> ArenaState:
        return await self._arena_state("/api/simulation/pause")

    async def reset(self) -> ArenaState:
        return await self._arena_state("/api/simulation/reset")

    async def stop(self) -> None:
        return None

    async def start_scenario(self, scenario_name: str) -> AttackTrackerState:
        payload = await asyncio.to_thread(
            self._request,
            "POST",
            f"/api/scenarios/{_scenario_path(scenario_name)}",
        )
        return AttackTrackerState.model_validate(payload)

    def launch_scenario(self, scenario_name: str) -> dict[str, object]:
        try:
            payload = self._request("POST", f"/api/scenarios/{_scenario_path(scenario_name)}")
        except ValueError as exc:
            return {"accepted": False, "error": str(exc)}
        return {"accepted": True, "scenario": payload}

    async def _advance_tick_async(self, running: bool = True) -> None:
        del running
        await asyncio.to_thread(self._request, "POST", "/internal/arena/step")

    async def list_incidents(self) -> list[Incident]:
        payload = await asyncio.to_thread(self._request, "GET", "/api/incidents")
        return [Incident.model_validate(item) for item in payload]

    async def get_incident(self, incident_id: str) -> Incident | None:
        try:
            payload = await asyncio.to_thread(
                self._request,
                "GET",
                f"/api/incidents/{parse.quote(incident_id, safe='')}",
            )
        except LookupError:
            return None
        return Incident.model_validate(payload)

    async def replay_exchange_events(self, *, after_sequence: int = 0, limit: int = 100) -> ExchangeEventReplay:
        query = parse.urlencode({"afterSequence": after_sequence, "limit": limit})
        payload = await asyncio.to_thread(
            self._request,
            "GET",
            f"/api/arena/exchange-events?{query}",
        )
        return ExchangeEventReplay.model_validate(payload)

    async def _arena_state(self, path: str) -> ArenaState:
        payload = await asyncio.to_thread(self._request, "POST", path)
        return ArenaState.model_validate(payload)

    def _request(self, method: str, path: str) -> object:
        req = request.Request(
            f"{self.base_url}{path}",
            method=method,
            headers={"Accept": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            if exc.code == 404:
                raise LookupError(path) from exc
            raise ValueError(f"Java arena returned HTTP {exc.code}") from exc
        except (error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Java arena is unavailable at {self.base_url}") from exc


def _scenario_path(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    mapping = {
        "spoofing_like_wall": "spoofing-like",
        "layering_like": "layering-like",
        "quote_stuffing": "quote-stuffing",
        "liquidity_evaporation": "liquidity-evaporation",
    }
    try:
        return mapping[normalized]
    except KeyError as exc:
        raise ValueError(f"unknown scenario: {value}") from exc
