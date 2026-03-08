"""
ProcureMind - Synthetic Data Generator
Generates realistic logistics procurement data and seeds the SQLite DB.
Carriers, routes, and all data are stored in the DB — not just Python lists.
"""

import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# Default seed data — written to DB on first run
DEFAULT_CARRIERS = [
    {"id": "C001", "name": "BlueDart Express", "reliability": 0.94, "avg_delay_hrs": 2.1, "success_rate": 0.96, "rating": 4.7},
    {"id": "C002", "name": "DTDC Logistics",   "reliability": 0.87, "avg_delay_hrs": 4.5, "success_rate": 0.89, "rating": 4.2},
    {"id": "C003", "name": "Delhivery Freight", "reliability": 0.91, "avg_delay_hrs": 3.0, "success_rate": 0.93, "rating": 4.5},
    {"id": "C004", "name": "Gati KWE",          "reliability": 0.85, "avg_delay_hrs": 5.2, "success_rate": 0.86, "rating": 4.0},
    {"id": "C005", "name": "XpressBees",        "reliability": 0.89, "avg_delay_hrs": 3.8, "success_rate": 0.90, "rating": 4.3},
]

DEFAULT_ROUTES = [
    {"origin": "Mumbai",    "destination": "Delhi",     "base_rate": 52000, "distance_km": 1400},
    {"origin": "Chennai",   "destination": "Bangalore", "base_rate": 18000, "distance_km": 350},
    {"origin": "Mumbai",    "destination": "Pune",      "base_rate": 9500,  "distance_km": 150},
    {"origin": "Delhi",     "destination": "Kolkata",   "base_rate": 45000, "distance_km": 1500},
    {"origin": "Hyderabad", "destination": "Chennai",   "base_rate": 22000, "distance_km": 625},
    {"origin": "Ahmedabad", "destination": "Mumbai",    "base_rate": 14000, "distance_km": 530},
    {"origin": "Bangalore", "destination": "Hyderabad", "base_rate": 20000, "distance_km": 570},
    {"origin": "Kolkata",   "destination": "Delhi",     "base_rate": 47000, "distance_km": 1480},
]

GOODS_TYPES = ["Electronics", "Pharmaceuticals", "Textiles", "Auto Parts", "FMCG", "Machinery"]


def generate_shipments(routes, n=200):
    shipments = []
    for i in range(n):
        route = random.choice(routes)
        weight = round(random.uniform(100, 5000), 1)
        deadline_days = random.randint(2, 10)
        base = route["base_rate"]
        budget = round(base * random.uniform(0.85, 1.0), -2)
        shipments.append({
            "shipment_id": f"SHP{1000+i}",
            "origin": route["origin"],
            "destination": route["destination"],
            "weight_kg": weight,
            "goods_type": random.choice(GOODS_TYPES),
            "deadline_days": deadline_days,
            "budget_inr": budget,
            "distance_km": route["distance_km"],
            "created_at": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
            "status": random.choice(["pending", "negotiating", "awarded", "completed"]),
        })
    return shipments


def generate_carrier_quotes(shipments, carriers, routes):
    quotes = []
    for s in shipments:
        route_data = next((r for r in routes if r["origin"] == s["origin"] and r["destination"] == s["destination"]), None)
        if not route_data:
            continue
        base = route_data["base_rate"]
        for carrier in carriers:
            markup = random.uniform(1.05, 1.20)
            initial_quote = round(base * markup, -2)
            quotes.append({
                "quote_id": f"Q{len(quotes)+1:04d}",
                "shipment_id": s["shipment_id"],
                "carrier_id": carrier["id"],
                "carrier_name": carrier["name"],
                "initial_quote_inr": initial_quote,
                "final_quote_inr": None,
                "negotiation_rounds": 0,
                "status": "pending",
                "created_at": s["created_at"],
            })
    return quotes


def generate_negotiation_logs(shipments, quotes, carriers):
    logs = []
    awarded_shipments = [s for s in shipments if s["status"] in ("negotiating", "awarded", "completed")]
    for s in awarded_shipments[:50]:
        s_quotes = [q for q in quotes if q["shipment_id"] == s["shipment_id"]]
        for q in s_quotes:
            carrier = next(c for c in carriers if c["id"] == q["carrier_id"])
            initial = q["initial_quote_inr"]
            target = s["budget_inr"]
            current = initial
            rounds = random.randint(2, 5)
            for r in range(1, rounds + 1):
                if r == 1:
                    logs.append({
                        "log_id": f"LOG{len(logs)+1:05d}",
                        "shipment_id": s["shipment_id"],
                        "carrier_id": carrier["id"],
                        "round": r,
                        "sender": "carrier",
                        "channel": random.choice(["email", "whatsapp", "sms"]),
                        "message": f"Quote for {s['origin']}–{s['destination']}: ₹{current:,.0f}",
                        "price": current,
                        "timestamp": datetime.now().isoformat(),
                    })
                else:
                    step = (current - target) * random.uniform(0.3, 0.6)
                    current = round(current - step, -2)
                    sender = "ai_agent" if r % 2 == 0 else "carrier"
                    logs.append({
                        "log_id": f"LOG{len(logs)+1:05d}",
                        "shipment_id": s["shipment_id"],
                        "carrier_id": carrier["id"],
                        "round": r,
                        "sender": sender,
                        "channel": random.choice(["email", "whatsapp", "sms"]),
                        "message": f"Revised offer: ₹{current:,.0f}" if sender == "carrier" else f"Counter proposal: ₹{current:,.0f}",
                        "price": current,
                        "timestamp": datetime.now().isoformat(),
                    })
    return logs


def init_db(db_path="procuremind.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS carriers (
        id TEXT PRIMARY KEY, name TEXT, reliability REAL,
        avg_delay_hrs REAL, success_rate REAL, rating REAL
    );
    CREATE TABLE IF NOT EXISTS routes (
        route_id INTEGER PRIMARY KEY AUTOINCREMENT,
        origin TEXT, destination TEXT,
        base_rate REAL, distance_km REAL,
        UNIQUE(origin, destination)
    );
    CREATE TABLE IF NOT EXISTS shipments (
        shipment_id TEXT PRIMARY KEY, origin TEXT, destination TEXT,
        weight_kg REAL, goods_type TEXT, deadline_days INTEGER,
        budget_inr REAL, distance_km REAL, created_at TEXT, status TEXT
    );
    CREATE TABLE IF NOT EXISTS carrier_quotes (
        quote_id TEXT PRIMARY KEY, shipment_id TEXT, carrier_id TEXT,
        carrier_name TEXT, initial_quote_inr REAL, final_quote_inr REAL,
        negotiation_rounds INTEGER, status TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS negotiation_logs (
        log_id TEXT PRIMARY KEY, shipment_id TEXT, carrier_id TEXT,
        round INTEGER, sender TEXT, channel TEXT, message TEXT,
        price REAL, timestamp TEXT
    );
    CREATE TABLE IF NOT EXISTS negotiations (
        negotiation_id TEXT PRIMARY KEY,
        shipment_id TEXT,
        carrier_id TEXT,
        carrier_name TEXT,
        initial_quote REAL,
        final_price REAL,
        savings REAL,
        savings_pct REAL,
        rounds_count INTEGER,
        converged INTEGER DEFAULT 0,
        channel TEXT,
        strategy TEXT,
        composite_score REAL DEFAULT 0,
        price_score REAL DEFAULT 0,
        reliability_score REAL DEFAULT 0,
        performance_score REAL DEFAULT 0,
        is_winner INTEGER DEFAULT 0,
        created_at TEXT
    );
    """)
    conn.commit()
    return conn


def load_carriers(db_path="procuremind.db"):
    """Load carriers from DB"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM carriers ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_routes(db_path="procuremind.db"):
    """Load routes from DB"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM routes ORDER BY route_id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def seed_database(db_path="procuremind.db"):
    conn = init_db(db_path)
    c = conn.cursor()

    # Carriers
    c.executemany("INSERT OR REPLACE INTO carriers VALUES (?,?,?,?,?,?)",
        [(x["id"], x["name"], x["reliability"], x["avg_delay_hrs"], x["success_rate"], x["rating"]) for x in DEFAULT_CARRIERS])

    # Routes
    for r in DEFAULT_ROUTES:
        c.execute("INSERT OR IGNORE INTO routes (origin, destination, base_rate, distance_km) VALUES (?,?,?,?)",
            (r["origin"], r["destination"], r["base_rate"], r["distance_km"]))

    # Load back for generating shipments
    conn.row_factory = sqlite3.Row
    carriers = [dict(row) for row in conn.execute("SELECT * FROM carriers").fetchall()]
    routes_db = [dict(row) for row in conn.execute("SELECT * FROM routes").fetchall()]
    conn.row_factory = None

    # Shipments
    shipments = generate_shipments(routes_db, 200)
    c.executemany("INSERT OR REPLACE INTO shipments VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(s["shipment_id"], s["origin"], s["destination"], s["weight_kg"], s["goods_type"],
          s["deadline_days"], s["budget_inr"], s["distance_km"], s["created_at"], s["status"]) for s in shipments])

    # Quotes
    quotes = generate_carrier_quotes(shipments, carriers, routes_db)
    c.executemany("INSERT OR REPLACE INTO carrier_quotes VALUES (?,?,?,?,?,?,?,?,?)",
        [(q["quote_id"], q["shipment_id"], q["carrier_id"], q["carrier_name"],
          q["initial_quote_inr"], q["final_quote_inr"], q["negotiation_rounds"], q["status"], q["created_at"]) for q in quotes])

    # Logs
    logs = generate_negotiation_logs(shipments, quotes, carriers)
    c.executemany("INSERT OR REPLACE INTO negotiation_logs VALUES (?,?,?,?,?,?,?,?,?)",
        [(l["log_id"], l["shipment_id"], l["carrier_id"], l["round"], l["sender"],
          l["channel"], l["message"], l["price"], l["timestamp"]) for l in logs])

    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(shipments)} shipments, {len(quotes)} quotes, {len(logs)} logs")
    return {"carriers": carriers, "shipments": shipments, "quotes": quotes}


if __name__ == "__main__":
    seed_database()
