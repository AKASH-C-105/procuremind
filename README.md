# 🤖 ProcureMind 2.0 — AI Procurement Co-Pilot

> Multi-agent AI negotiation platform with Nash Bargaining, Bayesian trust updates, Digital Twin simulation, and full award optimization — built with **Flask + Vanilla JS**.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Negotiate** | 5 parallel carrier agents negotiate simultaneously using Nash Bargaining Theory |
| 🔬 **Digital Twin** | Simulate budget scenarios (Conservative / Market / Aggressive) before going live |
| 📊 **Analytics** | Live savings trends, carrier win rates, route volume, goods breakdown |
| 🔍 **AI Explainer** | Full transparency layer — see exactly how the AI scored and awarded each carrier |
| 🚚 **Carrier Intelligence** | Behavioral profiles, reliability scores, Nash persona modeling |
| ⚡ **Live Market Rate** | Computed in real-time from distance, weight, deadline, and surge factors |

---

## 🏗️ Architecture

```
procuremind/
├── app.py                           # Flask backend — all API routes
├── agents/
│   └── negotiation_agent.py         # MultiCarrierOrchestrator + NegotiationAgent
├── optimization/
│   └── award_optimizer.py           # AwardOptimizer (Price×0.45 + Rel×0.35 + Perf×0.20)
├── strategy/
│   └── pricing_model.py             # PricingModel — market rate computation
├── data/
│   └── synthetic_data_generator.py  # DB seed + schema init
├── dashboard/
│   └── index.html                   # Full SPA frontend (HTML + CSS + JS)
└── requirements.txt
```

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/AKASH-C-105/procuremind.git
cd procuremind

# 2. Install
pip install -r requirements.txt

# 3. Run
python app.py
```

Open **http://localhost:5000** — the SQLite DB is auto-seeded on first run.

---

## 🧠 AI Engine

### Negotiation Flow
```
RFQ Input → PricingModel.compute_market_rate()
          → compute_negotiation_bounds() [per strategy]
          → 5× NegotiationAgent (asyncio.gather — parallel)
          → Bayesian trust updates per round
          → AwardOptimizer.score_carriers()
          → Winner recommendation + full audit trail
```

### Composite Scoring
```
Score = 0.45 × Price Score  +  0.35 × Reliability  +  0.20 × Performance
```

### Strategies
| Strategy | Behavior |
|---|---|
| **Auto** | AI selects based on budget vs. market rate |
| **Aggressive** | Push hard below market, more rounds |
| **Moderate** | Balanced concessions |
| **Collaborative** | Partnership pricing, fewer rounds |

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/carriers` | All carriers |
| `GET` | `/api/routes` | All routes |
| `GET` | `/api/stats` | Live dashboard stats |
| `POST` | `/api/negotiate` | Run AI negotiation |
| `GET` | `/api/negotiations/history` | Past negotiations |
| `GET` | `/api/analytics/savings-trend` | Savings over time |
| `GET` | `/api/analytics/carrier-wins` | Win rate by carrier |
| `GET` | `/api/market-rate` | Compute market rate |

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, Flask, SQLite, asyncio
- **Frontend**: Vanilla HTML/CSS/JS, Chart.js
- **AI**: Nash Bargaining theory, Bayesian inference, weighted composite scoring
- **No external ML frameworks** — all models implemented from scratch

---

## 📦 Requirements

```
flask
flask-cors
```

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<p align="center">Built with ⚡ by ProcureMind AI</p>
