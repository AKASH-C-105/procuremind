"""
ProcureMind - Strategic Pricing Model
Computes negotiation boundaries using market intelligence
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple


@dataclass
class NegotiationBounds:
    market_low: float
    market_high: float
    target_price: float
    walk_away_price: float
    opening_counteroffer: float
    strategy: str


class PricingModel:
    """
    Computes optimal negotiation price ranges using:
    - Route distance normalization
    - Weight-based pricing
    - Deadline urgency premium
    - Historical market rates
    """

    BASE_RATE_PER_KM = 28.0       # ₹ per km base
    WEIGHT_FACTOR = 3.5           # ₹ per kg per 100km
    URGENCY_PREMIUM = 0.08        # 8% for tight deadlines
    MARKET_VARIANCE = 0.06        # ±6% market variance

    def compute_market_rate(self, distance_km: float, weight_kg: float,
                             deadline_days: int) -> float:
        """Estimate fair market rate for a shipment"""
        base = self.BASE_RATE_PER_KM * distance_km
        weight_adj = self.WEIGHT_FACTOR * weight_kg * (distance_km / 100)
        urgency = self.URGENCY_PREMIUM if deadline_days <= 3 else 0
        return base + weight_adj + (base * urgency)

    def compute_negotiation_bounds(
        self,
        distance_km: float,
        weight_kg: float,
        deadline_days: int,
        budget_inr: float,
        carrier_quote: float,
    ) -> NegotiationBounds:
        """
        Compute full negotiation strategy bounds.
        Uses Nash bargaining inspired split-the-difference approach.
        """
        market_rate = self.compute_market_rate(distance_km, weight_kg, deadline_days)
        market_low  = round(market_rate * (1 - self.MARKET_VARIANCE), -2)
        market_high = round(market_rate * (1 + self.MARKET_VARIANCE), -2)

        # Target: 5% below market midpoint, but never above budget
        target = round(min(market_rate * 0.95, budget_inr * 0.98), -2)

        # Walk-away = budget ceiling
        walk_away = round(budget_inr, -2)

        # Opening counter = split between target and carrier quote (aggressive)
        opening_counter = round((target * 0.6 + carrier_quote * 0.4), -2)

        # Strategy selection
        if carrier_quote > budget_inr * 1.15:
            strategy = "aggressive"
        elif carrier_quote > budget_inr * 1.05:
            strategy = "moderate"
        else:
            strategy = "collaborative"

        return NegotiationBounds(
            market_low=market_low,
            market_high=market_high,
            target_price=target,
            walk_away_price=walk_away,
            opening_counteroffer=opening_counter,
            strategy=strategy,
        )

    def bayesian_price_update(
        self, prior_estimate: float, carrier_response: float, round_num: int
    ) -> float:
        """
        Bayesian update: as rounds increase, weight carrier's signal more.
        Simulates learning carrier's reservation price.
        """
        trust_weight = min(0.1 * round_num, 0.5)
        return prior_estimate * (1 - trust_weight) + carrier_response * trust_weight

    def convergence_check(self, ai_offer: float, carrier_offer: float,
                          threshold_pct: float = 0.02) -> bool:
        """Check if prices have converged within threshold"""
        if carrier_offer == 0:
            return False
        return abs(ai_offer - carrier_offer) / carrier_offer < threshold_pct
