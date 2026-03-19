# Apollo 2 — Pension Fund Comparison Tool

A web application for analyzing and comparing Israeli pension funds (קופות גמל), helping identify better-performing alternatives for individual clients based on their existing fund statements.

## What It Does

1. Upload client XML statement files (mislaka format)
2. The engine scores each client's fund against all others in the same risk category using weighted performance metrics (1Y, 3Y, 5Y returns + Sharpe ratio)
3. Returns top 3 alternative fund recommendations with projected gains and a percentile ranking
4. Optionally suggests a "golden option" upgrade to a higher-risk tier

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13+, FastAPI, Uvicorn |
| Frontend | React 19, JavaScript |
| Data | XML (kupot_gemel_net.xml, mislaka files) |
| Export | jsPDF, html2canvas |

## Project Structure

```
apollo2/
├── src/
│   ├── api/app.py              # FastAPI server (port 8000)
│   ├── engines/engine.py       # Core scoring & comparison logic
│   ├── parsers/                # XML parsers for fund DB and client files
│   └── engines/*.xml           # Pension fund database + risk profiles
├── frontend/web/src/
│   └── App.js                  # React UI (Hebrew RTL)
├── start.sh                    # macOS/Linux startup script
└── start.bat                   # Windows startup script
```

## Getting Started

### Prerequisites
- Python 3.13+
- Node.js 16+ & npm

### Install

```bash
# Python dependencies
pip install -e .

# Frontend dependencies
cd frontend/web && npm install
```

### Run

```bash
# macOS / Linux
./start.sh

# Windows
start.bat
```

This starts:
- Backend API at http://localhost:8000
- Frontend at http://localhost:3000 (opens automatically)

### Manual startup

```bash
# Terminal 1 — backend
python -m src.api.app

# Terminal 2 — frontend
cd frontend/web && npm start
```

## API

`POST /compare` — main endpoint (multipart form)

| Field | Type | Description |
|-------|------|-------------|
| `mislaka_file` | file(s) | Client XML statement files |
| `weight_1` | float | Weight for 1-year return (default 0.10) |
| `weight_3` | float | Weight for 3-year return (default 0.20) |
| `weight_5` | float | Weight for 5-year return (default 0.25) |
| `weight_sharp` | float | Weight for Sharpe ratio (default 0.45) |

`GET /health` — health check

## Features

- **Risk-based matching** — compares funds only within the same risk tier (Low / Medium / High)
- **Fee-adjusted returns** — management fees are applied before scoring
- **Percentile ranking** — shows how the client's fund ranks among peers
- **Financial projection** — estimates gains from switching funds
- **PDF & Word export** — generate shareable client reports
- **Hebrew RTL UI** — fully localized interface
