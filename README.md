# Apollo 2 — Pension Fund Comparison Tool

A web application for analyzing and comparing Israeli pension funds (קופות גמל), helping identify better-performing alternatives for individual clients based on their existing fund statements.

## What It Does

1. Upload client XML statement files (mislaka format)
2. The engine scores each client's fund against all others in the same risk category using weighted performance metrics (1Y, 3Y, 5Y returns, Sharpe ratio and liquidity index)
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

## Tests

```bash
uv run pytest                      # backend: unit, integration, system
cd frontend/web && npm test        # frontend (Jest + React Testing Library)
```

| Layer | What it checks |
|-------|----------------|
| `tests/unit` | Each module in isolation, including property-based tests ([Hypothesis](https://hypothesis.readthedocs.io)) that check invariants on thousands of generated fund pools — e.g. scores stay in 0–100, the liquidity rank ignores scale, a fee paid by every fund never changes the ranking |
| `tests/unit/comparison/test_service.py` | A hand-computed "golden master" of the full comparison payload, plus the golden-option rules |
| `tests/integration` | The real pipeline from XML files to results on a small hand-made market where every figure is worked out by hand; the HTTP API end to end |
| `tests/system` | The real GemeNet data, checked against an independent re-implementation (an "oracle") that reads the raw XML itself — so it stays valid when the data is refreshed |
| `frontend/web/src/*.test.js` | Upload settings and drags, the request sent, the fee toggle across every widget, the portfolio card, bulk ranking/search/CSV, PDF content, community |

`HYPOTHESIS_PROFILE=thorough uv run pytest tests/unit` runs the property tests with 10× more examples.

## API

`POST /compare` — main endpoint (multipart form)

| Field | Type | Description |
|-------|------|-------------|
| `mislaka_file` | file(s) | Client XML statement files |
| `weight_1` | int | Weight for 1-year return (UI default 10) |
| `weight_3` | int | Weight for 3-year return (UI default 20) |
| `weight_5` | int | Weight for 5-year return (UI default 25) |
| `weight_sharp` | int | Weight for Sharpe ratio (UI default 35) |
| `weight_liquidity` | int | Weight for the liquidity index (UI default 10; optional, defaults to 0) |
| `low_exposure_threshold` / `medium_exposure_threshold` | int | Equity-exposure risk bands |
| `israel_share_min` / `israel_share_max` | float | Only recommend funds whose equity is this % Israeli (default 0–100 = no filter) |
| `bad_hevrot` | str(s) | Managing companies never to recommend |
| `override_risk_level` | str | Compare against this risk level instead |

The five weights must sum to 100. The response has `funds` (per holding: `client`,
`alternatives`, `golden`) and `portfolio` (money-weighted AmoScore and upside). Each
alternative's figures assume the client keeps paying their current management fee;
the same figures without any fee are under its `gross` key.

`POST /compare/bulk` — many clients at once. Same form fields; upload any number of
`mislaka_file`s. Files are grouped by client ID and clients come back ranked by how
much they would gain from moving, with unreadable/irrelevant files listed in
`errors` / `skipped`.

`GET /health` — health check

## Features

- **Risk-based matching** — compares funds only within the same risk tier (Low / Medium / High)
- **Fee-adjusted returns** — management fees are applied before scoring; the results page can show alternatives with or without fees (the client's own fund always net of their fee)
- **Liquidity index** — 12-month net accumulation ÷ assets (GemeNet), percentile-ranked as the fifth AmoScore metric
- **Israel / abroad equity filter** — Israeli equity = equity exposure − foreign exposure; recommend only funds whose equity split is in a chosen range
- **Portfolio score** — AmoScore weighted by the share of the client's money in each fund
- **Bulk analysis** — upload files of many clients and rank them by urgency to move, with CSV export
- **Percentile ranking** — shows how the client's fund ranks among peers
- **Financial projection** — estimates gains from switching funds
- **PDF & Word export** — generate shareable client reports
- **Hebrew RTL UI** — fully localized interface
