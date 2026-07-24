import json
import sys
from pathlib import Path

from app.arena.engine import SimulationEngine
from app.detectors.features import extract_features
from app.evaluation.ground_truth import binary_classification_metrics, evaluate_detection
from app.evaluation.run_planning import derive_run_seed, engine_profile, exact_balanced_plan, exact_weighted_plan
from app.schemas.arena import AgentEvent, OrderBookSnapshot, PriceLevel
from serverless.jobs import detector_tournament, run_batch_experiments


def test_run_plans_are_exact_weighted_and_seeded() -> None:
    scenarios = exact_balanced_plan(7, ["normal", "spoofing", "layering"], seed=11)
    difficulties = exact_weighted_plan(
        7,
        {"easy": 0.2, "medium": 0.3, "hard": 0.4, "adversarial": 0.1},
        seed=11,
    )

    assert len(scenarios) == 7
    assert {name: scenarios.count(name) for name in set(scenarios)} == {
        "normal": 3,
        "spoofing": 2,
        "layering": 2,
    }
    assert {name: difficulties.count(name) for name in set(difficulties)} == {
        "easy": 1,
        "medium": 2,
        "hard": 3,
        "adversarial": 1,
    }
    assert scenarios == exact_balanced_plan(7, ["normal", "spoofing", "layering"], seed=11)


def test_basic_tournament_runs_exact_total_and_uses_seed(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "basic"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "detector_tournament.py",
            "--runs",
            "3",
            "--scenarios",
            "normal_market,spoofing_like_wall",
            "--detectors",
            "spoofing_like,layering_like",
            "--random-seed",
            "91",
            "--output",
            str(output),
        ],
    )

    detector_tournament.main()
    payload = json.loads((output / "results.json").read_text(encoding="utf-8"))

    assert payload["runs"] == 3
    assert len({row["run_id"] for row in payload["run_results"]}) == 3
    assert {row["seed"] for row in payload["run_results"]} == {
        derive_run_seed(91, index) for index in range(3)
    }
    attack_rows = [row for row in payload["run_results"] if row["scenario"] == "spoofing_like_wall"]
    assert attack_rows and all(row["truth"] for row in attack_rows)
    normal_metrics = [row for row in payload["metrics"] if row["scenario"] == "normal-market"]
    assert all(row["precision"] is None and row["recall"] is None and row["f1"] is None for row in normal_metrics)
    assert all(row["specificity"] is not None for row in normal_metrics)


def test_batch_runner_applies_difficulty_and_rich_ground_truth() -> None:
    result = run_batch_experiments._run_one(0, "spoofing_like_wall", "hard", 300)
    label = result.labels[0]

    assert result.seed == derive_run_seed(300, 0)
    assert result.difficulty == "hard"
    assert label["difficulty"] == "hard"
    assert label["manipulation_windows"]
    assert label["phase_windows"]
    assert label["event_ids"]
    assert label["order_ids"]
    assert result.metrics["detection_timing"] in {"early", "on_time", "late", "missed"}
    assert "event_recall" in result.metrics
    assert "participant_recall" in result.metrics
    assert "order_recall" in result.metrics


def test_adjacent_experiment_seeds_produce_independent_run_seeds_and_profiles() -> None:
    first = {derive_run_seed(100, index) for index in range(200)}
    second = {derive_run_seed(101, index) for index in range(200)}

    assert len(first) == 200
    assert len(second) == 200
    assert first.isdisjoint(second)
    seed = derive_run_seed(100, 0)
    assert engine_profile("medium", seed=seed) == engine_profile("medium", seed=seed)
    assert engine_profile("medium", seed=seed) != engine_profile("medium", seed=derive_run_seed(101, 0))


def test_distinct_base_seeds_change_normalized_market_events() -> None:
    first = run_batch_experiments._run_one(0, "spoofing_like_wall", "medium", 100)
    second = run_batch_experiments._run_one(0, "spoofing_like_wall", "medium", 101)

    def normalize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
        return [{key: value for key, value in row.items() if key != "timestamp"} for row in rows]

    assert first.seed != second.seed
    assert normalize(first.events) != normalize(second.events)


def test_order_lifetime_is_observed_order_age_not_scenario_elapsed() -> None:
    book = OrderBookSnapshot(
        bids=[PriceLevel(price=99.0, quantity=10.0)],
        asks=[PriceLevel(price=101.0, quantity=40.0)],
        best_bid=99.0,
        best_ask=101.0,
        mid=100.0,
        spread=2.0,
    )
    tracker: dict[str, int] = {}
    placed = AgentEvent(type="limit", order_id="order-1", agent_id="p1", side="sell", price=101.0, quantity=40.0)
    extract_features(
        book=book,
        events=[placed],
        previous_depth_top_n=None,
        tick_interval_seconds=0.5,
        active_scenario=None,
        current_tick=2,
        order_first_seen_ticks=tracker,
    )
    features = extract_features(
        book=book,
        events=[],
        previous_depth_top_n=None,
        tick_interval_seconds=0.5,
        active_scenario=None,
        current_tick=5,
        order_first_seen_ticks=tracker,
    )

    assert features.order_lifetime_ms == 1500.0


def test_layering_runs_on_both_book_sides_by_seed() -> None:
    even = SimulationEngine(seed=2)
    odd = SimulationEngine(seed=3)
    even.launch_scenario("layering_like")
    odd.launch_scenario("layering_like")
    for _ in range(2):
        even_state = even.step()
        odd_state = odd.step()

    assert any(level.get("owner") == "abuser" for level in even_state["book"]["asks"])
    assert any(level.get("owner") == "abuser" for level in odd_state["book"]["bids"])


def test_ground_truth_scores_temporal_event_attribution_and_phases() -> None:
    result = evaluate_detection(
        alert_ticks=[3, 4],
        label={
            "manipulation_windows": [{"start_tick": 2, "end_tick": 5}],
            "phase_windows": {"pressure_phase": {"start_tick": 3, "end_tick": 4}},
            "event_ids": ["e1", "e2"],
            "agent_ids": ["p1"],
            "order_ids": ["o1"],
        },
        predicted_event_ids={"e1"},
        predicted_participant_ids={"p1"},
        predicted_order_ids={"o1"},
    )

    assert result["temporal_overlap"] == 0.5
    assert result["event_precision"] == 1.0
    assert result["event_recall"] == 0.5
    assert result["participant_recall"] == 1.0
    assert result["order_recall"] == 1.0
    assert result["detection_timing"] == "on_time"
    assert result["phase_detection"] == {"pressure_phase": True}


def test_binary_classification_metrics_are_shared_and_exact() -> None:
    assert binary_classification_metrics(tp=1, fp=1, fn=0, tn=1) == {
        "precision": 0.5,
        "recall": 1.0,
        "f1": 0.6667,
        "specificity": 0.5,
        "false_positive_rate": 0.5,
        "true_positive": 1,
        "false_positive": 1,
        "false_negative": 0,
        "true_negative": 1,
    }
