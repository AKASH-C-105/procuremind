"""
ProcureMind - AI Negotiation Agent
Handles per-carrier negotiation with Nash-bargaining inspired strategy
"""

import random
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional
from strategy.pricing_model import PricingModel, NegotiationBounds
from communication.simulators import (
    simulate_email_thread, simulate_whatsapp_thread, simulate_sms_thread
)


@dataclass
class NegotiationRound:
    round: int
    sender: str           # 'ai_agent' | 'carrier'
    ai_offer: float
    carrier_price: float
    market_low: float
    market_high: float
    delta: float          # abs difference
    converged: bool
    sentiment: str = "neutral"
    reasoning: str = ""


@dataclass
class NegotiationResult:
    carrier_id: str
    carrier_name: str
    shipment_id: str
    initial_quote: float
    final_price: float
    rounds: List[NegotiationRound]
    converged: bool
    savings: float
    channel: str
    comm_log: List[dict] = field(default_factory=list)
    score: float = 0.0


CARRIER_PERSONA = {
    # How aggressively carriers concede per round (0=stubborn, 1=flexible)
    "C001": 0.35,  # BlueDart – premium, less flexible
    "C002": 0.55,  # DTDC – mid, flexible
    "C003": 0.45,  # Delhivery – moderate
    "C004": 0.60,  # Gati – most flexible (lower reliability)
    "C005": 0.50,  # XpressBees – balanced
}


class NegotiationAgent:
    """
    AI agent that negotiates freight rates with a single carrier.
    Uses Nash bargaining (split the surplus) + Bayesian price updates.
    """

    MAX_ROUNDS = 6
    CONVERGENCE_THRESHOLD = 0.015  # 1.5%

    def __init__(self, carrier: dict, shipment: dict, pricing_model: PricingModel):
        self.carrier = carrier
        self.shipment = shipment
        self.pm = pricing_model
        self.bounds: Optional[NegotiationBounds] = None
        self.rounds: List[NegotiationRound] = []

    def _simulate_carrier_response(self, ai_offer: float, carrier_current: float,
                                    round_num: int) -> float:
        """
        Simulate carrier's counter-response.
        Carrier concedes towards AI offer, influenced by persona flexibility.
        """
        flexibility = CARRIER_PERSONA.get(self.carrier["id"], 0.45)
        noise = random.gauss(0, 0.005)  # ±0.5% noise
        concession = (carrier_current - ai_offer) * flexibility * (1 + noise)
        new_price = carrier_current - concession
        # Floor: carrier won't go below 90% of initial quote
        floor_price = self.carrier.get("_initial_quote", ai_offer) * 0.90
        return round(max(new_price, floor_price), -2)

    async def negotiate(self, initial_carrier_quote: float, channel: str = "email") -> NegotiationResult:
        """Run full negotiation loop asynchronously"""
        self.carrier["_initial_quote"] = initial_carrier_quote

        self.bounds = self.pm.compute_negotiation_bounds(
            distance_km=self.shipment["distance_km"],
            weight_kg=self.shipment["weight_kg"],
            deadline_days=self.shipment["deadline_days"],
            budget_inr=self.shipment["budget_inr"],
            carrier_quote=initial_carrier_quote,
        )

        ai_offer = self.bounds.opening_counteroffer
        carrier_price = initial_carrier_quote
        converged = False
        final_price = carrier_price

        for round_num in range(1, self.MAX_ROUNDS + 1):
            # 1. ANALYZE (Sentiment & Strategy)
            # Simulate sentiment analysis on carrier's price delta
            sentiment = "cooperative" if (initial_carrier_quote - carrier_price) > (initial_carrier_quote * 0.05) else "firm"
            
            # 2. STRATEGIZE (Bayesian Update)
            ai_offer = self.pm.bayesian_price_update(ai_offer, carrier_price, round_num)
            ai_offer = round(ai_offer, -2)

            # 3. ACT (Communication)
            reasoning = f"Countering at ₹{ai_offer:,} to test carrier's reservation price. Strategy: {self.bounds.strategy}."
            
            # Wait for "carrier" (simulated delay for parallelism realism)
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
            # Carrier responds
            carrier_price = self._simulate_carrier_response(ai_offer, carrier_price, round_num)
            delta = abs(ai_offer - carrier_price)

            converged = self.pm.convergence_check(ai_offer, carrier_price, self.CONVERGENCE_THRESHOLD)

            r = NegotiationRound(
                round=round_num,
                sender="ai_agent",
                ai_offer=ai_offer,
                carrier_price=carrier_price,
                market_low=self.bounds.market_low,
                market_high=self.bounds.market_high,
                delta=delta,
                converged=converged,
                sentiment=sentiment,
                reasoning=reasoning
            )
            self.rounds.append(r)
            final_price = carrier_price

            if converged or carrier_price <= self.bounds.target_price:
                break

            # Walk away if carrier won't budge (Match Problem Statement #1)
            if carrier_price > self.bounds.walk_away_price and round_num >= 4:
                break

        # Build communication log
        round_dicts = []
        for r in self.rounds:
            round_dicts.append({"round": r.round, "sender": "ai_agent", "ai_offer": r.ai_offer, "carrier_price": r.carrier_price, "market_low": r.market_low, "market_high": r.market_high, "sentiment": r.sentiment})
            round_dicts.append({"round": r.round, "sender": "carrier", "ai_offer": r.ai_offer, "carrier_price": r.carrier_price, "market_low": r.market_low, "market_high": r.market_high, "sentiment": r.sentiment})
        
        round_dicts_sorted = sorted(round_dicts, key=lambda x: (x["round"], 0 if x["sender"]=="ai_agent" else 1))

        if channel == "email":
            comm_log = simulate_email_thread(self.shipment, self.carrier, round_dicts_sorted)
        elif channel == "whatsapp":
            comm_log = simulate_whatsapp_thread(self.shipment, self.carrier, round_dicts_sorted)
        else:
            comm_log = simulate_sms_thread(self.shipment, self.carrier, round_dicts_sorted)

        savings = initial_carrier_quote - final_price

        return NegotiationResult(
            carrier_id=self.carrier["id"],
            carrier_name=self.carrier["name"],
            shipment_id=self.shipment["shipment_id"],
            initial_quote=initial_carrier_quote,
            final_price=final_price,
            rounds=self.rounds,
            converged=converged,
            savings=savings,
            channel=channel,
            comm_log=comm_log,
        )


class MultiCarrierOrchestrator:
    """
    Orchestrates parallel negotiation with all carriers for a shipment.
    Assigns different communication channels to different carriers.
    """

    CHANNELS = ["email", "whatsapp", "sms", "email", "whatsapp"]

    def __init__(self, shipment: dict, carriers: list, carrier_quotes: dict):
        self.shipment = shipment
        self.carriers = carriers
        self.carrier_quotes = carrier_quotes  # {carrier_id: initial_quote}
        self.pm = PricingModel()

    async def run(self) -> List[NegotiationResult]:
        """Runs parallel negotiations using asyncio task gathering"""
        tasks = []
        for i, carrier in enumerate(self.carriers):
            initial_quote = self.carrier_quotes.get(carrier["id"])
            if not initial_quote:
                continue
            channel = self.CHANNELS[i % len(self.CHANNELS)]
            agent = NegotiationAgent(carrier, self.shipment, self.pm)
            tasks.append(agent.negotiate(initial_quote, channel=channel))
        
        # True Parallel Negotiation Engine Execution
        results = await asyncio.gather(*tasks)
        return list(results)
