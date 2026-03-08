"""
ProcureMind - Award Optimizer
Scores carriers using weighted multi-criteria model and selects winner
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class CarrierScore:
    carrier_id: str
    carrier_name: str
    final_price: float
    reliability: float
    success_rate: float
    avg_delay_hrs: float
    rating: float
    price_score: float
    reliability_score: float
    performance_score: float
    composite_score: float
    rank: int
    recommended: bool
    savings_vs_initial: float
    savings_pct: float


class AwardOptimizer:
    """
    Multi-criteria weighted scoring:
      composite = w_price * norm_price + w_rel * reliability + w_perf * performance
    """

    # Weights (must sum to 1.0)
    W_PRICE       = 0.45
    W_RELIABILITY = 0.35
    W_PERFORMANCE = 0.20

    def score_carriers(
        self,
        negotiation_results: list,   # List[NegotiationResult]
        carrier_profiles: List[dict],
    ) -> List[CarrierScore]:
        if not negotiation_results:
            return []

        # Index carrier profiles
        profiles = {c["id"]: c for c in carrier_profiles}

        prices = np.array([r.final_price for r in negotiation_results])
        price_min, price_max = prices.min(), prices.max()

        scores = []
        for r in negotiation_results:
            profile = profiles.get(r.carrier_id, {})
            reliability  = profile.get("reliability", 0.8)
            success_rate = profile.get("success_rate", 0.8)
            avg_delay    = profile.get("avg_delay_hrs", 5.0)
            rating       = profile.get("rating", 3.5)

            # Normalize price: lower = better (score closer to 1)
            if price_max == price_min:
                price_score = 1.0
            else:
                price_score = 1 - (r.final_price - price_min) / (price_max - price_min)

            # Reliability score (already 0-1)
            rel_score = reliability

            # Performance composite: success_rate - delay_penalty + rating_boost
            delay_penalty = min(avg_delay / 10.0, 0.3)
            rating_boost  = (rating - 3.0) / 4.0 * 0.2
            perf_score    = min(max(success_rate - delay_penalty + rating_boost, 0), 1)

            composite = (
                self.W_PRICE       * price_score
                + self.W_RELIABILITY * rel_score
                + self.W_PERFORMANCE * perf_score
            )

            savings = r.initial_quote - r.final_price
            savings_pct = (savings / r.initial_quote * 100) if r.initial_quote else 0

            scores.append(CarrierScore(
                carrier_id=r.carrier_id,
                carrier_name=r.carrier_name,
                final_price=r.final_price,
                reliability=reliability,
                success_rate=success_rate,
                avg_delay_hrs=avg_delay,
                rating=rating,
                price_score=round(price_score, 4),
                reliability_score=round(rel_score, 4),
                performance_score=round(perf_score, 4),
                composite_score=round(composite, 4),
                rank=0,
                recommended=False,
                savings_vs_initial=round(savings, 2),
                savings_pct=round(savings_pct, 2),
            ))

        # Rank by composite score (desc)
        scores.sort(key=lambda x: x.composite_score, reverse=True)
        for i, s in enumerate(scores):
            s.rank = i + 1
            s.recommended = (i == 0)

        return scores

    def generate_recommendation(self, scores: List[CarrierScore], shipment: dict) -> dict:
        if not scores:
            return {"error": "No scored carriers"}
        winner = scores[0]
        runner_up = scores[1] if len(scores) > 1 else None

        rationale = (
            f"{winner.carrier_name} is recommended for Shipment {shipment['shipment_id']} "
            f"({shipment['origin']} → {shipment['destination']}) based on the best composite "
            f"score of {winner.composite_score:.2%}.\n\n"
            f"Final negotiated price: ₹{winner.final_price:,.0f} "
            f"(saved ₹{winner.savings_vs_initial:,.0f} | {winner.savings_pct:.1f}% below initial quote).\n"
            f"Reliability: {winner.reliability:.0%} | Success rate: {winner.success_rate:.0%} | "
            f"Avg delay: {winner.avg_delay_hrs:.1f} hrs | Rating: ⭐ {winner.rating}"
        )

        comparison = ""
        if runner_up:
            comparison = (
                f"\nRunner-up: {runner_up.carrier_name} scored {runner_up.composite_score:.2%} "
                f"at ₹{runner_up.final_price:,.0f}."
            )

        return {
            "winner_carrier_id": winner.carrier_id,
            "winner_carrier_name": winner.carrier_name,
            "final_price": winner.final_price,
            "composite_score": winner.composite_score,
            "savings": winner.savings_vs_initial,
            "savings_pct": winner.savings_pct,
            "rationale": rationale + comparison,
            "scores": [
                {
                    "rank": s.rank,
                    "carrier": s.carrier_name,
                    "price": s.final_price,
                    "composite": s.composite_score,
                    "price_score": s.price_score,
                    "reliability_score": s.reliability_score,
                    "performance_score": s.performance_score,
                    "recommended": s.recommended,
                }
                for s in scores
            ],
        }
