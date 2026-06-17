# Mag 7 Live Dashboard

A dashboard for the "Magnificent 7" stocks (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA)
showing real prices from Yahoo Finance, the daily % change vs. the previous close,
and an approximate historical P/E chart.

**Live site:** https://DOAA351.github.io/mag7-prices/

## How it works

GitHub Pages is static hosting — it can't run Python. So the data pipeline is:

```
GitHub Action (every ~5 min)  ->  fetch_prices.py (yfinance)  ->  data.json  ->  commit
                                                                                    |
                                          GitHub Pages serves index.html + data.json
                                                                                    |
                                          Browser polls data.json every 30s and re-renders
```

- `fetch_prices.py` pulls **real** prices from Yahoo (no simulation / random walk).
- Daily change is `(price - previous_close) / previous_close`, where `previous_close`
  is the last completed trading session's close.
- Prices refresh roughly every 5 minutes during U.S. market hours (GitHub cron is
  best-effort and often a little late). Outside market hours Yahoo returns the last
  close, which is the correct value to show.

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

1. **Settings → Pages** → Source: *Deploy from a branch* → Branch: `master` / root.
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
