"""
ProcureMind 2.0 — Flask App (Fully Dynamic)
All data served from SQLite. No hardcoded static data.
Run: python app.py
Open: http://localhost:5000
"""

import sys, os, json, sqlite3, random, asyncio, uuid
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request, send_from_directory
try:
    from flask_cors import CORS
except ImportError:
    # flask_cors is optional — install with: pip install flask-cors
    class CORS:
        def __init__(self, app, **kwargs): pass

from data.synthetic_data_generator import seed_database, init_db, GOODS_TYPES
from agents.negotiation_agent import MultiCarrierOrchestrator
from optimization.award_optimizer import AwardOptimizer
from strategy.pricing_model import PricingModel

# ── Setup ──────────────────────────────────────────────────────────
BASE    = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE, "procuremind.db")
DASH    = os.path.join(BASE, "dashboard")

app = Flask(__name__, static_folder=DASH)
CORS(app)

# Seed DB on startup if not exists
if not os.path.exists(DB_PATH):
    seed_database(DB_PATH)
else:
    # Ensure schema is up to date (adds new tables if missing)
    init_db(DB_PATH)
    # Always ensure routes are seeded (fix for pre-existing DBs with empty routes)
    from data.synthetic_data_generator import DEFAULT_ROUTES
    _conn = sqlite3.connect(DB_PATH)
    _route_count = _conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
    if _route_count == 0:
        for _r in DEFAULT_ROUTES:
            _conn.execute("INSERT OR IGNORE INTO routes (origin, destination, base_rate, distance_km) VALUES (?,?,?,?)",
                         (_r["origin"], _r["destination"], _r["base_rate"], _r["distance_km"]))
        _conn.commit()
        print(f"  ✅  Seeded {len(DEFAULT_ROUTES)} routes into DB")
    _conn.close()

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_carriers():
    """Load carriers from DB"""
    conn = db()
    rows = conn.execute("SELECT * FROM carriers ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_routes():
    """Load routes from DB"""
    conn = db()
    rows = conn.execute("SELECT * FROM routes ORDER BY route_id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Serve Dashboard ────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(DASH, "index.html")


# ── CARRIER CRUD ───────────────────────────────────────────────────

@app.get("/api/carriers")
def api_carriers():
    return jsonify(get_carriers())


@app.post("/api/carriers")
def create_carrier():
    data = request.get_json()
    required = ["id", "name", "reliability", "avg_delay_hrs", "success_rate", "rating"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"Missing field: {f}"}), 400
    conn = db()
    try:
        conn.execute("INSERT INTO carriers VALUES (?,?,?,?,?,?)",
            (data["id"], data["name"], float(data["reliability"]),
             float(data["avg_delay_hrs"]), float(data["success_rate"]), float(data["rating"])))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Carrier ID already exists"}), 409
    conn.close()
    return jsonify({"success": True, "carrier": data}), 201


@app.put("/api/carriers/<carrier_id>")
def update_carrier(carrier_id):
    data = request.get_json()
    conn = db()
    existing = conn.execute("SELECT * FROM carriers WHERE id=?", (carrier_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Carrier not found"}), 404
    conn.execute("""UPDATE carriers SET name=?, reliability=?, avg_delay_hrs=?,
        success_rate=?, rating=? WHERE id=?""",
        (data.get("name", existing["name"]),
         float(data.get("reliability", existing["reliability"])),
         float(data.get("avg_delay_hrs", existing["avg_delay_hrs"])),
         float(data.get("success_rate", existing["success_rate"])),
         float(data.get("rating", existing["rating"])),
         carrier_id))
    conn.commit()
    updated = dict(conn.execute("SELECT * FROM carriers WHERE id=?", (carrier_id,)).fetchone())
    conn.close()
    return jsonify(updated)


@app.delete("/api/carriers/<carrier_id>")
def delete_carrier(carrier_id):
    conn = db()
    existing = conn.execute("SELECT * FROM carriers WHERE id=?", (carrier_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Carrier not found"}), 404
    conn.execute("DELETE FROM carriers WHERE id=?", (carrier_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "deleted": carrier_id})


# ── ROUTE CRUD ─────────────────────────────────────────────────────

@app.get("/api/routes")
def api_routes():
    routes = get_routes()
    # Return in compatible format
    result = []
    for r in routes:
        result.append({
            "route_id": r["route_id"],
            "from": r["origin"],
            "to": r["destination"],
            "origin": r["origin"],
            "destination": r["destination"],
            "base_rate": r["base_rate"],
            "distance_km": r["distance_km"],
        })
    return jsonify(result)


@app.post("/api/routes")
def create_route():
    data = request.get_json()
    conn = db()
    try:
        conn.execute("INSERT INTO routes (origin, destination, base_rate, distance_km) VALUES (?,?,?,?)",
            (data["origin"], data["destination"], float(data["base_rate"]), float(data["distance_km"])))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Route already exists"}), 409
    conn.close()
    return jsonify({"success": True}), 201


@app.delete("/api/routes/<int:route_id>")
def delete_route(route_id):
    conn = db()
    conn.execute("DELETE FROM routes WHERE route_id=?", (route_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ── SHIPMENTS ──────────────────────────────────────────────────────

@app.get("/api/shipments")
def api_shipments():
    limit  = request.args.get("limit", 20, type=int)
    status = request.args.get("status")
    conn   = db()
    q      = "SELECT * FROM shipments"
    params = []
    if status:
        q += " WHERE status=?"; params.append(status)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.post("/api/shipments")
def create_shipment():
    data = request.get_json()
    sid = f"SHP{random.randint(5000, 99999)}"
    conn = db()
    routes = get_routes()
    route = next((r for r in routes if r["origin"] == data.get("origin") and r["destination"] == data.get("destination")), None)
    distance = route["distance_km"] if route else 0
    conn.execute("INSERT INTO shipments VALUES (?,?,?,?,?,?,?,?,?,?)",
        (sid, data.get("origin"), data.get("destination"),
         float(data.get("weight_kg", 500)), data.get("goods_type", "General"),
         int(data.get("deadline_days", 3)), float(data.get("budget_inr", 50000)),
         distance, datetime.now().isoformat(), "pending"))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "shipment_id": sid}), 201


# ── STATS ──────────────────────────────────────────────────────────

@app.get("/api/stats")
def api_stats():
    conn = db()
    total     = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
    awarded   = conn.execute("SELECT COUNT(*) FROM shipments WHERE status='awarded'").fetchone()[0]
    avg_save  = conn.execute("SELECT AVG(savings) FROM negotiations WHERE savings IS NOT NULL").fetchone()[0] or 0
    quotes    = conn.execute("SELECT COUNT(*) FROM carrier_quotes").fetchone()[0]
    carriers  = conn.execute("SELECT COUNT(*) FROM carriers").fetchone()[0]
    routes    = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
    neg_count = conn.execute("SELECT COUNT(DISTINCT shipment_id) FROM negotiations").fetchone()[0]
    total_savings = conn.execute("SELECT COALESCE(SUM(savings), 0) FROM negotiations WHERE is_winner=1").fetchone()[0]
    avg_rounds = conn.execute("SELECT AVG(rounds_count) FROM negotiations WHERE is_winner=1").fetchone()[0] or 0
    conn.close()
    return jsonify({
        "total_shipments": total,
        "awarded_shipments": awarded,
        "avg_savings_inr": round(avg_save, 2),
        "total_quotes": quotes,
        "carriers_active": carriers,
        "routes_count": routes,
        "negotiations_run": neg_count,
        "total_savings": round(total_savings, 2),
        "avg_rounds": round(avg_rounds, 1),
    })


# ── GOODS TYPES ────────────────────────────────────────────────────

@app.get("/api/goods-types")
def api_goods_types():
    return jsonify(GOODS_TYPES)


# ── MARKET RATE ────────────────────────────────────────────────────

@app.get("/api/market-rate")
def market_rate():
    origin   = request.args.get("origin")
    dest     = request.args.get("destination")
    weight   = request.args.get("weight_kg", type=float)
    deadline = request.args.get("deadline_days", type=int)
    routes   = get_routes()
    route    = next((r for r in routes if r["origin"] == origin and r["destination"] == dest), None)
    if not route:
        return jsonify({"error": "Route not found"}), 400
    pm   = PricingModel()
    rate = pm.compute_market_rate(route["distance_km"], weight, deadline)
    return jsonify({
        "market_rate":  round(rate, -2),
        "market_low":   round(rate * 0.94, -2),
        "market_high":  round(rate * 1.06, -2),
        "distance_km":  route["distance_km"],
    })


# ── NEGOTIATE ──────────────────────────────────────────────────────

@app.post("/api/negotiate")
def negotiate():
    data = request.get_json()
    origin   = data.get("origin")
    dest     = data.get("destination")
    weight   = float(data.get("weight_kg", 500))
    goods    = data.get("goods_type", "General")
    deadline = int(data.get("deadline_days", 3))
    budget   = float(data.get("budget_inr", 50000))

    routes   = get_routes()
    carriers = get_carriers()

    if not carriers:
        return jsonify({"error": "No carriers in database"}), 400

    route = next((r for r in routes if r["origin"] == origin and r["destination"] == dest), None)
    if not route:
        return jsonify({"error": f"Route {origin}→{dest} not found"}), 400

    shipment_id = f"SHP{random.randint(5000, 99999)}"
    shipment = {
        "shipment_id":  shipment_id,
        "origin":       origin,
        "destination":  dest,
        "weight_kg":    weight,
        "goods_type":   goods,
        "deadline_days": deadline,
        "budget_inr":   budget,
        "distance_km":  route["distance_km"],
    }

    carrier_quotes = {
        c["id"]: round(route["base_rate"] * random.uniform(1.05, 1.20), -2)
        for c in carriers
    }

    orchestrator = MultiCarrierOrchestrator(shipment, carriers, carrier_quotes)
    results      = asyncio.run(orchestrator.run())

    optimizer      = AwardOptimizer()
    scores         = optimizer.score_carriers(results, carriers)
    recommendation = optimizer.generate_recommendation(scores, shipment)

    # ── Persist shipment ──
    conn = db()
    conn.execute("INSERT OR REPLACE INTO shipments VALUES (?,?,?,?,?,?,?,?,?,?)",
        (shipment_id, origin, dest, weight, goods, deadline, budget,
         route["distance_km"], datetime.now().isoformat(), "awarded"))

    # ── Persist negotiation results ──
    now = datetime.now().isoformat()
    for i, r in enumerate(results):
        score_obj = next((s for s in scores if s.carrier_id == r.carrier_id), None)
        neg_id = f"NEG-{shipment_id}-{r.carrier_id}"
        conn.execute("""INSERT OR REPLACE INTO negotiations
            (negotiation_id, shipment_id, carrier_id, carrier_name,
             initial_quote, final_price, savings, savings_pct,
             rounds_count, converged, channel, strategy,
             composite_score, price_score, reliability_score, performance_score,
             is_winner, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (neg_id, shipment_id, r.carrier_id, r.carrier_name,
             r.initial_quote, r.final_price, r.savings,
             round((r.savings / r.initial_quote * 100) if r.initial_quote else 0, 2),
             len(r.rounds), 1 if r.converged else 0,
             r.channel, "",
             round(score_obj.composite_score, 4) if score_obj else 0,
             round(score_obj.price_score, 4) if score_obj else 0,
             round(score_obj.reliability_score, 4) if score_obj else 0,
             round(score_obj.performance_score, 4) if score_obj else 0,
             1 if score_obj and score_obj.recommended else 0,
             now))

    conn.commit()
    conn.close()

    # ── Build response ──
    negotiation_details = []
    for r in results:
        negotiation_details.append({
            "carrier_id":   r.carrier_id,
            "carrier_name": r.carrier_name,
            "initial_quote": r.initial_quote,
            "final_price":  r.final_price,
            "savings":      r.savings,
            "channel":      r.channel,
            "rounds":       len(r.rounds),
            "converged":    r.converged,
            "comm_log":     r.comm_log,
            "round_data": [
                {"round": rnd.round, "ai_offer": rnd.ai_offer,
                 "carrier_price": rnd.carrier_price, "delta": rnd.delta,
                 "converged": rnd.converged, "sentiment": rnd.sentiment,
                 "reasoning": rnd.reasoning,
                 "market_low": rnd.market_low, "market_high": rnd.market_high}
                for rnd in r.rounds
            ],
        })

    return jsonify({
        "shipment":       shipment,
        "carrier_quotes": carrier_quotes,
        "negotiation":    negotiation_details,
        "recommendation": recommendation,
        "scores": [{
            "rank":              s.rank,
            "carrier_id":        s.carrier_id,
            "carrier_name":      s.carrier_name,
            "final_price":       s.final_price,
            "composite_score":   s.composite_score,
            "price_score":       s.price_score,
            "reliability_score": s.reliability_score,
            "performance_score": s.performance_score,
            "savings_vs_initial": s.savings_vs_initial,
            "savings_pct":       s.savings_pct,
            "recommended":       s.recommended,
        } for s in scores],
    })


# ── ANALYTICS ──────────────────────────────────────────────────────

@app.get("/api/analytics/summary")
def analytics_summary():
    conn = db()
    total_negs = conn.execute("SELECT COUNT(DISTINCT shipment_id) FROM negotiations").fetchone()[0]
    total_savings = conn.execute("SELECT COALESCE(SUM(savings), 0) FROM negotiations WHERE is_winner=1").fetchone()[0]
    avg_time = conn.execute("SELECT AVG(rounds_count) FROM negotiations WHERE is_winner=1").fetchone()[0] or 0
    convergence = conn.execute("""
        SELECT ROUND(CAST(SUM(CASE WHEN converged=1 THEN 1 ELSE 0 END) AS FLOAT) /
               NULLIF(COUNT(*), 0) * 100, 1)
        FROM negotiations WHERE is_winner=1
    """).fetchone()[0] or 0
    conn.close()
    return jsonify({
        "total_negotiations": total_negs,
        "total_savings": round(total_savings, 2),
        "avg_rounds": round(avg_time, 1),
        "convergence_rate": convergence,
    })


@app.get("/api/analytics/savings-trend")
def analytics_savings_trend():
    conn = db()
    rows = conn.execute("""
        SELECT DATE(created_at) as day, SUM(savings) as total_savings
        FROM negotiations WHERE is_winner=1
        GROUP BY DATE(created_at) ORDER BY day
    """).fetchall()
    conn.close()
    if not rows:
        return jsonify({"labels": [], "data": []})
    return jsonify({
        "labels": [r["day"] for r in rows],
        "data": [round(r["total_savings"], 2) for r in rows],
    })


@app.get("/api/analytics/carrier-wins")
def analytics_carrier_wins():
    conn = db()
    rows = conn.execute("""
        SELECT carrier_name, COUNT(*) as wins
        FROM negotiations WHERE is_winner=1
        GROUP BY carrier_id ORDER BY wins DESC
    """).fetchall()
    conn.close()
    return jsonify({
        "labels": [r["carrier_name"] for r in rows],
        "data": [r["wins"] for r in rows],
    })


@app.get("/api/analytics/route-volume")
def analytics_route_volume():
    conn = db()
    rows = conn.execute("""
        SELECT origin || '→' || destination as route, COUNT(*) as count
        FROM shipments GROUP BY origin, destination ORDER BY count DESC
    """).fetchall()
    conn.close()
    return jsonify({
        "labels": [r["route"] for r in rows],
        "data": [r["count"] for r in rows],
    })


@app.get("/api/analytics/goods-breakdown")
def analytics_goods_breakdown():
    conn = db()
    rows = conn.execute("""
        SELECT goods_type, COUNT(*) as count
        FROM shipments WHERE goods_type IS NOT NULL
        GROUP BY goods_type ORDER BY count DESC
    """).fetchall()
    conn.close()
    return jsonify({
        "labels": [r["goods_type"] for r in rows],
        "data": [r["count"] for r in rows],
    })


# ── NEGOTIATION HISTORY ───────────────────────────────────────────

@app.get("/api/negotiations/history")
def negotiations_history():
    limit = request.args.get("limit", 50, type=int)
    conn = db()
    rows = conn.execute("""
        SELECT n.shipment_id, n.carrier_name, n.initial_quote, n.final_price,
               n.savings, n.savings_pct, n.rounds_count, n.converged, n.channel,
               n.composite_score, n.is_winner, n.created_at,
               s.origin, s.destination, s.weight_kg, s.goods_type, s.budget_inr
        FROM negotiations n
        LEFT JOIN shipments s ON n.shipment_id = s.shipment_id
        WHERE n.is_winner = 1
        ORDER BY n.created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ── Run ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  ✅  ProcureMind 2.0 running at http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
