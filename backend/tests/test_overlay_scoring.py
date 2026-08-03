from app.services.overlay_scoring import apply_overlay
from app.services.scoring import rules_score_company
from app.models.entities import Company, Signal


def test_negative_vc_attention_hurts_base_rules_score():
    rubric = {
        "dimensions": {
            "founder_quality": {"weight": 0.30},
            "vc_attention": {"weight": -0.15},
            "traction_signal": {"weight": 0.25},
            "market_timing_fit": {"weight": 0.25},
            "network_proximity": {"weight": 0.20},
        }
    }
    quiet = Company(id=1, name="QuietCo", description="founder building quietly")
    loud = Company(
        id=2,
        name="LoudCo",
        description="raised series a from sequoia and a16z with lots of press",
    )
    quiet_sigs = [
        Signal(source="exa", title="Quiet launch", summary="early customers", payload={})
    ]
    loud_sigs = [
        Signal(
            source="exa",
            title="Crowded round",
            summary="raised series a from sequoia and a16z funded venture",
            payload={},
        )
    ]
    quiet_score = rules_score_company(quiet, quiet_sigs, rubric)["total_score"]
    loud_score = rules_score_company(loud, loud_sigs, rubric)["total_score"]
    assert quiet_score > loud_score


def test_partner_weight_delta_changes_rank():
    base_weights = {"founder_quality": 0.5, "traction_signal": 0.5}
    subscores = {
        "founder_quality": {"score": 80},
        "traction_signal": {"score": 40},
    }
    base, _ = apply_overlay(
        base_total=60,
        base_subscores=subscores,
        base_weights=base_weights,
        weight_adjustments={},
    )
    bumped, _ = apply_overlay(
        base_total=60,
        base_subscores=subscores,
        base_weights=base_weights,
        weight_adjustments={"founder_quality": 0.2},
    )
    assert bumped != base
    assert base == 60  # no-op overlay preserves base total
