"""
ProcureMind - Communication Channel Simulators
Generates realistic Email, WhatsApp, and SMS negotiation threads
"""

import random
from datetime import datetime
from typing import List, Dict


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─── EMAIL SIMULATOR ────────────────────────────────────────────────

EMAIL_TEMPLATES = {
    "initial_rfq": (
        "Subject: RFQ – Freight Services | {origin} to {destination} | Shipment {shipment_id}\n\n"
        "Dear {carrier_name} Team,\n\n"
        "We are seeking freight services for the below shipment and request your best quotation:\n\n"
        "  • Route       : {origin} → {destination}\n"
        "  • Weight      : {weight_kg} kg\n"
        "  • Goods Type  : {goods_type}\n"
        "  • Required By : {deadline_days} days\n\n"
        "Please revert with your competitive rates at the earliest.\n\n"
        "Warm regards,\nProcureMind AI Procurement System"
    ),
    "counteroffer": (
        "Subject: Re: RFQ – Freight Services | {origin} to {destination} | Shipment {shipment_id}\n\n"
        "Dear {carrier_name} Team,\n\n"
        "Thank you for your quotation of ₹{carrier_quote:,.0f}.\n\n"
        "After reviewing current market benchmarks and our volume commitments, "
        "we propose a revised rate of ₹{counter_offer:,.0f} for this shipment.\n\n"
        "This aligns with the prevailing market range of ₹{market_low:,.0f} – ₹{market_high:,.0f} "
        "and reflects our expectation of a long-term partnership.\n\n"
        "We look forward to your revised offer.\n\n"
        "Best regards,\nProcureMind AI Agent | Logistics Procurement"
    ),
    "acceptance": (
        "Subject: RE: Award Notification – {origin} to {destination} | Shipment {shipment_id}\n\n"
        "Dear {carrier_name} Team,\n\n"
        "We are pleased to confirm the award of Shipment {shipment_id} to {carrier_name} "
        "at the agreed rate of ₹{final_price:,.0f}.\n\n"
        "Please arrange pickup within {deadline_days} days. Our team will share the shipping order shortly.\n\n"
        "Thank you for your cooperation.\n\n"
        "Regards,\nProcureMind Procurement | Operations"
    ),
    "rejection": (
        "Subject: RE: RFQ Update – {origin} to {destination} | Shipment {shipment_id}\n\n"
        "Dear {carrier_name} Team,\n\n"
        "Thank you for your participation. After evaluation, we have awarded this shipment "
        "to another carrier whose offer was more aligned with our budget constraints.\n\n"
        "We hope to work with you on future opportunities.\n\n"
        "Regards,\nProcureMind Procurement Team"
    ),
}

CARRIER_EMAIL_RESPONSES = [
    "Thank you for your counter. The best we can offer at this time is ₹{revised_price:,.0f}. "
    "This accounts for fuel surcharges and the tight delivery window.",
    "We appreciate the opportunity. Our revised quote stands at ₹{revised_price:,.0f}, "
    "which already reflects a significant reduction from our standard tariff.",
    "After internal review, we can offer ₹{revised_price:,.0f}. "
    "This is our most competitive rate for this lane.",
    "Understood. We can revise to ₹{revised_price:,.0f}, "
    "provided the payment terms remain Net 30.",
]

def simulate_email_thread(shipment: dict, carrier: dict, negotiation_rounds: List[dict]) -> List[dict]:
    thread = []
    # Initial RFQ
    thread.append({
        "channel": "email", "sender": "ProcureMind", "receiver": carrier["name"],
        "timestamp": _timestamp(), "round": 0,
        "message": EMAIL_TEMPLATES["initial_rfq"].format(**shipment, carrier_name=carrier["name"]),
        "price": None,
    })
    for r in negotiation_rounds:
        if r["sender"] == "ai_agent":
            thread.append({
                "channel": "email", "sender": "ProcureMind AI Agent", "receiver": carrier["name"],
                "timestamp": _timestamp(), "round": r["round"],
                "message": EMAIL_TEMPLATES["counteroffer"].format(
                    **shipment, carrier_name=carrier["name"],
                    carrier_quote=r.get("carrier_price", r["ai_offer"]),
                    counter_offer=r["ai_offer"],
                    market_low=r.get("market_low", 0),
                    market_high=r.get("market_high", 0),
                ),
                "price": r["ai_offer"],
            })
        else:
            tmpl = random.choice(CARRIER_EMAIL_RESPONSES)
            thread.append({
                "channel": "email", "sender": carrier["name"], "receiver": "ProcureMind",
                "timestamp": _timestamp(), "round": r["round"],
                "message": tmpl.format(revised_price=r["carrier_price"]),
                "price": r["carrier_price"],
            })
    return thread


# ─── WHATSAPP SIMULATOR ─────────────────────────────────────────────

WA_TEMPLATES = {
    "greeting":    "Hi {contact}, this is ProcureMind AI 🤖. Reaching out re: shipment {shipment_id} ({origin}→{destination}).",
    "quote_req":   "Could you share your best rate for {weight_kg}kg freight, delivery in {deadline_days} days? 🚛",
    "counteroffer":"Your quote ₹{carrier_quote:,.0f} noted. Can you revise to ₹{counter_offer:,.0f}? Market avg is ~₹{market_avg:,.0f}.",
    "acceptance":  "✅ Great! Confirming award at ₹{final_price:,.0f}. PO will follow on email.",
    "rejection":   "Thanks for quoting. We've proceeded with another carrier this time. Will reach out for future shipments 🙏",
}

WA_CARRIER_RESPONSES = [
    "Sure, best we can do is ₹{revised_price:,.0f} 👍",
    "₹{revised_price:,.0f} – that's our floor for this route.",
    "Let me check with ops... can offer ₹{revised_price:,.0f}. Final.",
    "₹{revised_price:,.0f} with guaranteed next-day dispatch ✅",
]

def simulate_whatsapp_thread(shipment: dict, carrier: dict, negotiation_rounds: List[dict]) -> List[dict]:
    thread = []
    contact = carrier["name"].split()[0]
    thread.append({
        "channel": "whatsapp", "sender": "ProcureMind", "receiver": contact,
        "timestamp": _timestamp(), "round": 0,
        "message": WA_TEMPLATES["greeting"].format(contact=contact, **shipment) + "\n" +
                   WA_TEMPLATES["quote_req"].format(**shipment),
        "price": None,
    })
    for r in negotiation_rounds:
        if r["sender"] == "ai_agent":
            thread.append({
                "channel": "whatsapp", "sender": "ProcureMind", "receiver": contact,
                "timestamp": _timestamp(), "round": r["round"],
                "message": WA_TEMPLATES["counteroffer"].format(
                    carrier_quote=r.get("carrier_price", r["ai_offer"]),
                    counter_offer=r["ai_offer"],
                    market_avg=(r.get("market_low", 0) + r.get("market_high", 0)) / 2,
                ),
                "price": r["ai_offer"],
            })
        else:
            tmpl = random.choice(WA_CARRIER_RESPONSES)
            thread.append({
                "channel": "whatsapp", "sender": contact, "receiver": "ProcureMind",
                "timestamp": _timestamp(), "round": r["round"],
                "message": tmpl.format(revised_price=r["carrier_price"]),
                "price": r["carrier_price"],
            })
    return thread


# ─── SMS SIMULATOR ──────────────────────────────────────────────────

SMS_TEMPLATES = {
    "initial":     "ProcureMind: RFQ {shipment_id} {origin}-{destination} {weight_kg}kg. Reply with rate.",
    "counteroffer":"ProcureMind: Offer ₹{carrier_quote:,.0f} rcvd. Counter ₹{counter_offer:,.0f}? Reply YES/price.",
    "acceptance":  "ProcureMind: Awarded! ₹{final_price:,.0f} confirmed. Email follows.",
    "rejection":   "ProcureMind: Thanks for quote {shipment_id}. Awarded to another carrier.",
}

SMS_CARRIER_RESPONSES = [
    "Best rate ₹{revised_price:,.0f}. Delivery guaranteed.",
    "₹{revised_price:,.0f} - confirmed.",
    "Can do ₹{revised_price:,.0f}. Awaiting PO.",
    "YES ₹{revised_price:,.0f} accepted.",
]

def simulate_sms_thread(shipment: dict, carrier: dict, negotiation_rounds: List[dict]) -> List[dict]:
    thread = []
    thread.append({
        "channel": "sms", "sender": "ProcureMind", "receiver": carrier["name"],
        "timestamp": _timestamp(), "round": 0,
        "message": SMS_TEMPLATES["initial"].format(**shipment),
        "price": None,
    })
    for r in negotiation_rounds:
        if r["sender"] == "ai_agent":
            thread.append({
                "channel": "sms", "sender": "ProcureMind", "receiver": carrier["name"],
                "timestamp": _timestamp(), "round": r["round"],
                "message": SMS_TEMPLATES["counteroffer"].format(
                    carrier_quote=r.get("carrier_price", r["ai_offer"]),
                    counter_offer=r["ai_offer"],
                ),
                "price": r["ai_offer"],
            })
        else:
            tmpl = random.choice(SMS_CARRIER_RESPONSES)
            thread.append({
                "channel": "sms", "sender": carrier["name"], "receiver": "ProcureMind",
                "timestamp": _timestamp(), "round": r["round"],
                "message": tmpl.format(revised_price=r["carrier_price"]),
                "price": r["carrier_price"],
            })
    return thread
