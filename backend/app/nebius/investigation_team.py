from typing import Any, Protocol, Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    key: str
    label: str
    value: str | int | float | bool
    source: str | None = None


class EvidenceTimelineItem(BaseModel):
    sequence: int
    event: str
    tick: int | str | None = None
    source: str | None = None
    significance: str | None = None


class AgentFinding(BaseModel):
    name: str
    role: str
    finding: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class AIInvestigationTeamRequest(BaseModel):
    incident: dict[str, Any] = Field(default_factory=dict)
    detector_outputs: list[dict[str, Any]] = Field(default_factory=list)
    order_book_context: dict[str, Any] = Field(default_factory=dict)
    trades: list[dict[str, Any]] = Field(default_factory=list)
    market_metrics: dict[str, Any] = Field(default_factory=dict)
    episode_summary: dict[str, Any] = Field(default_factory=dict)


class AIInvestigationTeamResponse(BaseModel):
    mode: Literal["nebius", "mock"]
    endpoint: str
    investigation_id: str
    manipulation_type: str
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    agents: list[AgentFinding]
    consensus: str
    evidence_timeline: list[EvidenceTimelineItem]
    recommended_action: str
    executive_summary: str
    fallback_reason: str | None = None
    raw_response: dict[str, Any] | None = None
    structured_assessment: dict[str, Any] | None = None


class InvestigationTeamClient(Protocol):
    def analyze_investigation_team(self, request: AIInvestigationTeamRequest) -> AIInvestigationTeamResponse:
        ...


AIInvestigationAgentFinding = AgentFinding


def analyze_with_client(
    client: InvestigationTeamClient,
    request: AIInvestigationTeamRequest,
) -> AIInvestigationTeamResponse:
    return client.analyze_investigation_team(prepare_payload(request))


def prepare_payload(request: AIInvestigationTeamRequest) -> AIInvestigationTeamRequest:
    return AIInvestigationTeamRequest(
        incident=dict(request.incident),
        detector_outputs=[dict(item) for item in request.detector_outputs],
        order_book_context=dict(request.order_book_context),
        trades=[dict(item) for item in request.trades],
        market_metrics=dict(request.market_metrics),
        episode_summary=dict(request.episode_summary),
    )


def normalize_response(
    response: dict[str, Any],
    *,
    endpoint: str,
    mode: Literal["nebius", "mock"] = "nebius",
    fallback_reason: str | None = None,
) -> AIInvestigationTeamResponse:
    return AIInvestigationTeamResponse(
        mode=mode,
        endpoint=endpoint,
        fallback_reason=fallback_reason,
        investigation_id=str(response.get("investigation_id") or "ai-investigation-team"),
        manipulation_type=str(response.get("manipulation_type") or "unknown"),
        risk_score=_bounded_float(response.get("risk_score"), 0.5),
        confidence=_bounded_float(response.get("confidence"), 0.5),
        agents=_agent_findings(response.get("agents")),
        consensus=str(response.get("consensus") or "Investigation team reached no consensus."),
        evidence_timeline=_timeline_items(response.get("evidence_timeline")),
        recommended_action=str(response.get("recommended_action") or "Review the synthetic incident."),
        executive_summary=str(response.get("executive_summary") or "AI investigation completed."),
        raw_response=response if mode == "nebius" else None,
        structured_assessment=(
            response.get("structured_assessment")
            if isinstance(response.get("structured_assessment"), dict)
            else None
        ),
    )


def mock_response(request: AIInvestigationTeamRequest, *, reason: str) -> AIInvestigationTeamResponse:
    incident = request.incident
    metrics = request.market_metrics
    detector_outputs = request.detector_outputs
    manipulation_type = _manipulation_type(incident, detector_outputs)
    risk_score = _investigation_risk_score(incident, detector_outputs, metrics)
    confidence = _bounded_float(
        max([_feature_float(row, "confidence") for row in detector_outputs] or [risk_score]),
        risk_score,
    )
    evidence = _investigation_evidence(metrics, detector_outputs)
    timeline = _investigation_timeline(incident, request.order_book_context, request.trades)
    return AIInvestigationTeamResponse(
        mode="mock",
        endpoint="mock Nebius /investigation-team",
        fallback_reason=reason,
        investigation_id=str(incident.get("incident_id") or incident.get("id") or "INV-MOCK-001"),
        manipulation_type=manipulation_type,
        risk_score=round(risk_score, 4),
        confidence=round(confidence, 4),
        agents=[
            AgentFinding(
                name="OrderBookExpertAgent",
                role="Order book microstructure reviewer",
                finding=f"Order-book context is consistent with {manipulation_type}.",
                confidence=round(min(0.96, risk_score + 0.04), 4),
                evidence=evidence[:3],
            ),
            AgentFinding(
                name="TradePatternAgent",
                role="Trade and cancellation pattern reviewer",
                finding="Trade and event cadence supports synthetic replay review.",
                confidence=round(max(0.55, confidence - 0.05), 4),
                evidence=[EvidenceItem(key="trade_count", label="Trade count", value=len(request.trades)), *evidence[:2]],
            ),
            AgentFinding(
                name="StatisticsAgent",
                role="Metric anomaly reviewer",
                finding="Market metrics crossed deterministic anomaly thresholds.",
                confidence=round(risk_score, 4),
                evidence=evidence,
            ),
            AgentFinding(
                name="ComplianceAgent",
                role="Synthetic compliance framing reviewer",
                finding="Case is suitable for educational escalation, not real enforcement.",
                confidence=0.89,
                evidence=[
                    EvidenceItem(key="synthetic_simulation", label="Synthetic simulation", value=True),
                    EvidenceItem(key="real_market_data", label="Real market data", value=False),
                ],
            ),
            AgentFinding(
                name="LeadInvestigatorAgent",
                role="Consensus owner",
                finding=f"Consensus: {manipulation_type} risk is {risk_score:.2f}.",
                confidence=round((risk_score + confidence) / 2, 4),
                evidence=[
                    EvidenceItem(key=f"timeline_{item.sequence}", label="Timeline", value=item.event, source=item.source)
                    for item in timeline[:3]
                ],
            ),
        ],
        consensus=f"{manipulation_type} synthetic incident with risk {risk_score:.2f}.",
        evidence_timeline=timeline,
        recommended_action="Queue this synthetic interval for replay, artifact capture, and detector-threshold review.",
        executive_summary=(
            f"AI Investigation Team reviewed incident {incident.get('incident_id') or incident.get('id') or 'unknown'} "
            f"and found {manipulation_type} evidence at risk {risk_score:.2f}."
        ),
    )


def _agent_findings(value: Any) -> list[AgentFinding]:
    if not isinstance(value, list):
        value = []
    findings: list[AgentFinding] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        findings.append(
            AgentFinding(
                name=str(item.get("name") or f"InvestigationAgent{index + 1}"),
                role=str(item.get("role") or "Investigation reviewer"),
                finding=str(item.get("finding") or "No finding provided."),
                confidence=_bounded_float(item.get("confidence"), 0.5),
                evidence=_evidence_items(item.get("evidence")),
            )
        )
    return findings or [
        AgentFinding(
            name="LeadInvestigatorAgent",
            role="Consensus owner",
            finding="Endpoint returned no agent findings.",
            confidence=0.5,
            evidence=[],
        )
    ]


def _evidence_items(value: Any) -> list[EvidenceItem]:
    if isinstance(value, str):
        return [EvidenceItem(key="evidence", label="Evidence", value=value)]
    if not isinstance(value, list):
        return []
    items: list[EvidenceItem] = []
    for index, item in enumerate(value):
        if isinstance(item, dict):
            items.append(
                EvidenceItem(
                    key=str(item.get("key") or f"evidence_{index + 1}"),
                    label=str(item.get("label") or item.get("key") or "Evidence"),
                    value=_evidence_value(item.get("value") if "value" in item else item.get("text") or item),
                    source=str(item["source"]) if item.get("source") is not None else None,
                )
            )
        else:
            items.append(EvidenceItem(key=f"evidence_{index + 1}", label="Evidence", value=str(item)))
    return items


def _timeline_items(value: Any) -> list[EvidenceTimelineItem]:
    if isinstance(value, str):
        return [EvidenceTimelineItem(sequence=1, event=value)]
    if not isinstance(value, list):
        return []
    items: list[EvidenceTimelineItem] = []
    for index, item in enumerate(value):
        sequence = index + 1
        if isinstance(item, dict):
            items.append(
                EvidenceTimelineItem(
                    sequence=int(item.get("sequence") or sequence),
                    event=str(item.get("event") or item.get("description") or item),
                    tick=item.get("tick"),
                    source=str(item["source"]) if item.get("source") is not None else None,
                    significance=str(item["significance"]) if item.get("significance") is not None else None,
                )
            )
        else:
            items.append(EvidenceTimelineItem(sequence=sequence, event=str(item)))
    return items


def _manipulation_type(incident: dict[str, Any], detector_outputs: list[dict[str, Any]]) -> str:
    candidates = [
        incident.get("manipulation_type"),
        incident.get("type"),
        incident.get("scenario"),
        incident.get("scenario_family"),
    ]
    candidates.extend(row.get("detected_pattern") or row.get("detector") for row in detector_outputs)
    for candidate in candidates:
        if candidate:
            return str(candidate).lower().replace("-", "_").replace(" ", "_")
    return "unknown"


def _investigation_risk_score(
    incident: dict[str, Any],
    detector_outputs: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> float:
    confidence_values = [_feature_float(row, "confidence") for row in detector_outputs]
    suspicion_values = [_feature_float(row, "suspicion_score") for row in detector_outputs]
    metric_values = [
        _feature_float(metrics, "wall_size_ratio") / 10,
        _feature_float(metrics, "cancel_to_trade_ratio") / 12,
        _feature_float(metrics, "message_rate") / 40,
        _feature_float(metrics, "depth_change_pct"),
        _feature_float(metrics, "imbalance"),
    ]
    incident_confidence = _feature_float(incident, "confidence")
    return max(0.05, min(0.99, max([incident_confidence, *confidence_values, *suspicion_values, *metric_values, 0.42])))


def _investigation_evidence(metrics: dict[str, Any], detector_outputs: list[dict[str, Any]]) -> list[EvidenceItem]:
    evidence = [
        EvidenceItem(key=key, label=key.replace("_", " "), value=_evidence_value(value), source="market_metrics")
        for key, value in sorted(metrics.items())
        if key in {"wall_size_ratio", "cancel_to_trade_ratio", "message_rate", "depth_change_pct", "imbalance"}
    ]
    for index, row in enumerate(detector_outputs[:3]):
        detector = row.get("detector") or row.get("detected_pattern") or "detector"
        confidence = row.get("confidence") or row.get("suspicion_score") or 0
        evidence.append(
            EvidenceItem(
                key=f"detector_{index + 1}",
                label=str(detector),
                value=_evidence_value(confidence),
                source="detector_outputs",
            )
        )
    return evidence or [EvidenceItem(key="detector_evidence", label="Detector evidence", value="available")]


def _investigation_timeline(
    incident: dict[str, Any],
    order_book_context: dict[str, Any],
    trades: list[dict[str, Any]],
) -> list[EvidenceTimelineItem]:
    tick = incident.get("tick") or incident.get("created_at") or "unknown"
    events = order_book_context.get("events")
    event_count = len(events) if isinstance(events, list) else 0
    return [
        EvidenceTimelineItem(sequence=1, event=f"Incident observed at tick/time {tick}.", tick=tick, source="incident"),
        EvidenceTimelineItem(sequence=2, event=f"Order-book context supplied with {event_count} event(s).", source="order_book_context"),
        EvidenceTimelineItem(sequence=3, event=f"Trade context supplied with {len(trades)} trade(s).", source="trades"),
        EvidenceTimelineItem(sequence=4, event="AI Investigation Team produced consensus from specialist findings.", source="investigation_team"),
    ]


def _feature_float(features: dict[str, Any], key: str) -> float:
    try:
        return float(features.get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bounded_float(value: Any, fallback: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return fallback


def _evidence_value(value: Any) -> str | int | float | bool:
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
