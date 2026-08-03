from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def apply_overlay(
    *,
    base_total: float,
    base_subscores: Dict[str, Any],
    base_weights: Dict[str, float],
    weight_adjustments: Dict[str, float],
    added_dimensions: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[float, Dict[str, float]]:
    """
    Cheap arithmetic re-rank from a shared base score pass.

    weight_adjustments are deltas applied on top of base weights
    (e.g. {"founder_quality": 0.05} bumps that dimension's weight by +0.05).
    Negative base weights (e.g. vc_attention) are supported generically.
    """
    added_dimensions = added_dimensions or []
    effective_weights = dict(base_weights)
    for dim, delta in (weight_adjustments or {}).items():
        effective_weights[dim] = effective_weights.get(dim, 0.0) + float(delta)

    # Normalize absolute weight mass so totals stay comparable across partners,
    # while preserving sign of each dimension weight.
    abs_sum = sum(abs(w) for w in effective_weights.values()) or 1.0

    adjusted_subscores: Dict[str, float] = {}
    total = 0.0
    for dim, weight in effective_weights.items():
        raw = base_subscores.get(dim, {})
        if isinstance(raw, dict):
            value = float(raw.get("score", 0.0))
        else:
            value = float(raw or 0.0)
        contrib = value * (weight / abs_sum)
        adjusted_subscores[dim] = contrib
        total += contrib

    # Custom dimensions: reuse base evidence scores when present; otherwise 0
    # until an async LLM fill is triggered elsewhere.
    for dim in added_dimensions:
        name = dim.get("name")
        if not name:
            continue
        weight = float(dim.get("weight", 0.0))
        reuse_from = dim.get("reuse_base_dimension")
        if reuse_from and reuse_from in base_subscores:
            raw = base_subscores[reuse_from]
            value = float(raw.get("score", 0.0) if isinstance(raw, dict) else raw or 0.0)
        else:
            value = float(dim.get("score", 0.0))
        contrib = value * weight
        adjusted_subscores[name] = contrib
        total += contrib

    # If only weight deltas (no added dims), keep magnitude near base_total
    if not added_dimensions and base_weights:
        # Re-scale so a no-op overlay ≈ base_total
        base_abs = sum(abs(w) for w in base_weights.values()) or 1.0
        noop_total = 0.0
        for dim, weight in base_weights.items():
            raw = base_subscores.get(dim, {})
            value = float(raw.get("score", 0.0) if isinstance(raw, dict) else raw or 0.0)
            noop_total += value * (weight / base_abs)
        if abs(noop_total) > 1e-9:
            total = base_total * (total / noop_total)

    return total, adjusted_subscores
