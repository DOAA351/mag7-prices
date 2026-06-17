# Mag 7 Live Dashboard

A dashboard for the "Magnificent 7" stocks (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA)
showing live prices from Yahoo Finance, the daily % change vs. the previous close,
and a normalized price-performance chart.

**Live site:** https://DOAA351.github.io/mag7-prices/

## How it works

Prices update **live in the browser** (every 15s, straight from Yahoo). Slow-moving
data (company metadata + the historical chart) comes from a GitHub Action that runs
`fetch_prices.py` and commits `data.json`. The data layer is layered like an exchange
tape — if one source breaks, the next takes over, and if everything breaks it shows
the last known price instead of going blank:

```
Browser (every 15s):  Yahoo Finance ──┐  (via CORS proxy chain: allorigins → corsproxy → …)
                       query1/query2 ──┤
                                        ├─► live price + daily %
GitHub Action (~5min): yfinance ───────┤   (data.json: metadata, chart, baseline prices)
                                        │
localStorage "tape" ───────────────────┘   (last known price — ultimate fallback)
```

- Live prices come from Yahoo's `v8/finance/chart` endpoint, relayed through public
  CORS proxies (the browser can't call Yahoo directly). Two Yahoo hosts and several
  proxies are tried in order.
- Daily change is `(price - previous_close) / previous_close`, where `previous_close`
  is the last completed trading session's close.
- If every live source is unreachable, the board falls back to `data.json` (≤5 min old)
  and then to the last value cached in `localStorage` — it never blanks out.
- The performance chart normalizes each stock to its % return from the start of the
  selected window (1Y/3Y/5Y) using real monthly closing prices.

## Run locally (true 30s refresh)

```bash
pip install -r requirements.txt

# Option A: one-shot, just write data.json once
python fetch_prices.py --once

# Option B: keep refreshing every 30s
python fetch_prices.py
```

Then serve the folder with any static server (do **not** open via `file://`, the
`fetch()` call needs HTTP):

```bash
python -m http.server 8000
# open http://localhost:8000
```

## Setup checklist (one time, on GitHub)

1. **Settings → Pages** → Source: *Deploy from a branch* → Branch: `main` / root.
2. **Settings → Actions → General → Workflow permissions** → *Read and write permissions*.
3. The price-update workflow runs on a schedule automatically. You can also trigger
   it manually from the **Actions** tab → *Update Mag 7 prices* → *Run workflow*.

## Files

| File | Purpose |
|------|---------|
| `index.html` | The dashboard (HTML + CSS + JS, reads `data.json`). |
| `fetch_prices.py` | Fetches prices/metrics from Yahoo, writes `data.json`. |
| `data.json` | Generated price data the dashboard reads. |
| `.github/workflows/update-prices.yml` | Scheduled job that refreshes `data.json`. |
| `requirements.txt` | Python dependency (`yfinance`). |
