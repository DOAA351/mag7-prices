"""
Mag 7 Price Fetcher
───────────────────
Pulls REAL prices and metrics from Yahoo Finance (via yfinance) and writes
data.json, which the HTML dashboard reads.

Two ways to run it:

  # Run once and exit (this is what GitHub Actions uses):
  python fetch_prices.py --once

  # Run forever, refreshing every 30s (good for local testing):
  python fetch_prices.py

Install dependency first:
  pip install yfinance
"""

import sys
import json
import time
import datetime
import yfinance as yf

# Make stdout UTF-8 so non-ASCII chars (e.g. checkmarks) don't crash on
# Windows' cp1252 console. No-op where stdout is already UTF-8 (e.g. CI/Linux).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

REFRESH_SECONDS = 30  # only used in loop mode

DESCRIPTIONS = {
    "AAPL": "Consumer electronics, software and services. Maker of iPhone, Mac, iPad and the iOS ecosystem.",
    "MSFT": "Enterprise software, cloud computing (Azure), and productivity tools including Office 365 and Teams.",
    "GOOGL": "Parent of Google. Dominates search, digital ads, YouTube and is a major cloud provider.",
    "AMZN": "E-commerce and cloud infrastructure leader (AWS). Also expanding in advertising and AI services.",
    "NVDA": "Designs GPUs and AI accelerators. The dominant supplier of chips powering AI training and inference.",
    "META": "Social media conglomerate. Operates Facebook, Instagram, WhatsApp and invests heavily in VR/AR.",
    "TSLA": "Electric vehicles, energy storage and solar. Also developing autonomous driving and robotics (Optimus).",
}

COLORS = {
    "AAPL": "#555555",
    "MSFT": "#0078d4",
    "GOOGL": "#4285f4",
    "AMZN": "#ff9900",
    "NVDA": "#76b900",
    "META": "#0668e1",
    "TSLA": "#cc0000",
}


def get_price_and_prev_close(t):
    """
    Return (current_price, prev_close) using the most reliable source available.

    Strategy:
      1. fast_info  — fast, lightweight, rarely rate-limited. Best for live price.
      2. history()  — fallback if fast_info is missing fields. Uses the last two
                      daily closes so prev_close is genuinely the PREVIOUS session.

    'prev_close' is always the last *completed* trading session's close, so
    change_pct = (price - prev_close) / prev_close is the true daily move.
    """
    current_price = None
    prev_close = None

    # --- Source 1: fast_info ---
    try:
        fi = t.fast_info
        current_price = fi.get("last_price") or fi.get("lastPrice")
        prev_close = fi.get("previous_close") or fi.get("previousClose")
    except Exception:
        pass

    # --- Source 2: history fallback (only fills what's missing) ---
    if not current_price or not prev_close:
        hist = t.history(period="5d", interval="1d")
        closes = hist["Close"].dropna() if not hist.empty else []
        if len(closes) >= 1 and not current_price:
            current_price = float(closes.iloc[-1])
        if len(closes) >= 2 and not prev_close:
            # second-to-last completed session
            prev_close = float(closes.iloc[-2])
        elif len(closes) == 1 and not prev_close:
            prev_close = float(closes.iloc[-1])

    return current_price, prev_close


def fetch_one(ticker):
    """Fetch a single ticker. Raises on hard failure so caller can record an error."""
    t = yf.Ticker(ticker)

    current_price, prev_close = get_price_and_prev_close(t)

    if not current_price:
        raise ValueError("no price returned by Yahoo")

    # Daily % change vs the last completed close
    if prev_close and prev_close > 0:
        change_pct = ((current_price - prev_close) / prev_close) * 100
    else:
        change_pct = 0.0
        prev_close = current_price

    # Metadata (P/E, EPS, market cap, name). These come from .info, which is
    # slower / flakier — so we treat them as best-effort and never let them
    # break the price fetch above.
    name = ticker
    trailing_pe = eps = None
    market_cap = 0
    try:
        info = t.info
        name = info.get("shortName") or info.get("longName") or ticker
        trailing_pe = info.get("trailingPE")
        eps = info.get("trailingEps")
        market_cap = info.get("marketCap", 0) or 0
    except Exception as e:
        print(f"    (metadata unavailable for {ticker}: {e})")

    stock = {
        "ticker": ticker,
        "name": name,
        "description": DESCRIPTIONS.get(ticker, ""),
        "color": COLORS.get(ticker, "#888888"),
        "price": round(current_price, 2),
        "prev_close": round(prev_close, 2),
        "change_pct": round(change_pct, 2),
        "trailing_pe": round(trailing_pe, 1) if trailing_pe else None,
        "eps": round(eps, 2) if eps else None,
        "market_cap": market_cap,
    }

    # Historical monthly closes (REAL prices) for the performance chart. The
    # browser normalizes these to % return per selected window, so the chart
    # actually means something (relative performance) instead of a fake P/E.
    price_series = None
    try:
        hist = t.history(period="5y", interval="1mo")
        if not hist.empty:
            dates, closes = [], []
            for date, row in hist.iterrows():
                close = row["Close"]
                if close and close > 0:
                    closes.append(round(float(close), 2))
                    dates.append(date.strftime("%b %y"))
            if closes:
                price_series = {"dates": dates, "closes": closes,
                                "color": COLORS.get(ticker, "#888888")}
    except Exception as e:
        print(f"    (price history unavailable for {ticker}: {e})")

    return stock, price_series


def fetch_all():
    """Fetch all Mag 7 stocks and write data.json. Returns the output dict."""
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Fetching prices...")

    stock_data = []
    price_history = {}

    for ticker in TICKERS:
        try:
            stock, price_series = fetch_one(ticker)
            stock_data.append(stock)
            if price_series:
                price_history[ticker] = price_series
            print(f"  {ticker}: ${stock['price']:.2f} "
                  f"({stock['change_pct']:+.2f}%) "
                  f"prevClose ${stock['prev_close']:.2f} "
                  f"PE:{stock['trailing_pe']}")
        except Exception as e:
            print(f"  {ticker}: ERROR - {e}")
            stock_data.append({
                "ticker": ticker,
                "name": ticker,
                "description": DESCRIPTIONS.get(ticker, ""),
                "color": COLORS.get(ticker, "#888888"),
                "price": 0,
                "prev_close": 0,
                "change_pct": 0,
                "trailing_pe": None,
                "eps": None,
                "market_cap": 0,
            })

    output = {
        # ISO 8601 UTC so the browser can parse it reliably and detect staleness
        "last_updated": datetime.datetime.now(datetime.timezone.utc)
                                .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stocks": stock_data,
        "price_history": price_history,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"  [OK] data.json updated at {output['last_updated']}\n")
    return output


def main():
    once = "--once" in sys.argv

    print("=" * 50)
    print("  Mag 7 Price Fetcher" + ("  (single run)" if once else "  (loop mode)"))
    print("=" * 50)
    print()

    fetch_all()

    if once:
        return

    print(f"Looping every {REFRESH_SECONDS}s. Press Ctrl+C to stop.\n")
    while True:
        try:
            time.sleep(REFRESH_SECONDS)
            fetch_all()
        except KeyboardInterrupt:
            print("\nStopped.")
            break


if __name__ == "__main__":
    main()
