#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import yfinance as yf

# -------------- Data fetch utils --------------

def getPastEarningsDates(ticker, maxFetch=40, count=6):
    t = yf.Ticker(ticker)
    df = None
    try:
        df = t.get_earnings_dates(limit=maxFetch)
    except Exception:
        pass

    dates = []
    if df is not None and len(df) > 0:
        try:
            if isinstance(df.index, pd.DatetimeIndex):
                dates = [d.date() for d in pd.to_datetime(df.index)]
            elif "Earnings Date" in df.columns:
                dates = [d.date() for d in pd.to_datetime(df["Earnings Date"])]
            else:
                tmp = df.reset_index()
                dates = [d.date() for d in pd.to_datetime(tmp["Earnings Date"])]
        except Exception:
            dates = []

    # Fallback: module-level (present in newer yfinance)
    if not dates:
        try:
            df2 = yf.get_earnings_dates(ticker, limit=maxFetch)
            if df2 is not None and len(df2) > 0:
                if isinstance(df2.index, pd.DatetimeIndex):
                    dates = [d.date() for d in pd.to_datetime(df2.index)]
                else:
                    tmp = df2.reset_index()
                    dates = [d.date() for d in pd.to_datetime(tmp["Earnings Date"])]
        except Exception:
            pass

    if not dates:
        return []

    today = datetime.now(timezone.utc).date()
    past = [d for d in dates if d < today]
    pastSorted = sorted(set(past), reverse=True)[:count]
    return list(reversed(pastSorted))  # chronological

def loadHistory(ticker, startDate, endDate):
    df = yf.download(ticker, start=startDate, end=endDate, auto_adjust=True, progress=False)
    if df.empty:
        return pd.DataFrame()
    # prefer Adj Close if available, else Close (auto_adjust=True already adjusts Close)
    col = "Adj Close" if "Adj Close" in df.columns else "Close"
    df = df[[col]].rename(columns={col: "adjClose"})
    df.index = pd.to_datetime(df.index)
    return df.sort_index()

# -------------- Trading-day anchors --------------

def lastCloseBefore(df, targetDate):
    ts = pd.Timestamp(targetDate)
    sub = df.loc[df.index < ts]
    if sub.empty:
        return None, None
    lastTs = sub.index.max()
    price = sub.loc[lastTs, "adjClose"]
    if hasattr(price, "iloc"):
        price = price.iloc[0]
    return lastTs, float(price)

def nTradingDaysBefore(df, anchorTs, n):
    # strictly before anchorTs; pick the nth from the end
    before = df.loc[df.index < anchorTs]
    if len(before) < n:
        return None, None
    ts = before.index[-n]
    price = before.loc[ts, "adjClose"]
    if hasattr(price, "iloc"):
        price = price.iloc[0]
    return ts, float(price)

# -------------- Core backtest --------------

def computeRunupsForTicker(ticker, xCount, yValues):
    earningsDates = getPastEarningsDates(ticker, maxFetch=60, count=xCount)
    if not earningsDates:
        return [], []

    # Pull enough history to cover the earliest window
    earliest = min(earningsDates)
    # Max Y we’ll need (trading days). Approx pad calendar by ~ (Y * 1.7) to cover weekends/holidays.
    maxY = max(yValues) if yValues else 20
    padDays = int(maxY * 2) + 15
    start = (earliest - timedelta(days=padDays)).isoformat()
    end = (max(earningsDates) + timedelta(days=5)).isoformat()
    prices = loadHistory(ticker, start, end)
    if prices.empty:
        return [], []

    # Pre-compute the pre-earnings close timestamps for each earnings date
    anchors = []
    for ed in earningsDates:
        preTs, preClose = lastCloseBefore(prices, ed)
        if preClose is None:
            anchors.append((ed, None, None))
        else:
            anchors.append((ed, preTs, preClose))

    # Build per-earnings rows for each Y and summary rows per Y
    perRows = []
    summaryRows = []
    for y in yValues:
        runups = []
        samples = 0
        wins = 0
        for ed, preTs, preClose in anchors:
            if preClose is None:
                continue
            baseTs, baseClose = nTradingDaysBefore(prices, preTs, y)
            if baseClose is None:
                continue
            pct = (preClose - baseClose) / baseClose * 100.0
            perRows.append({
                "ticker": ticker,
                "earningsDate": ed.isoformat(),
                "yTradingDays": y,
                "startAnchorDate": baseTs.date().isoformat(),
                "startAnchorClose": round(baseClose, 4),
                "preEarningsDate": preTs.date().isoformat(),
                "preEarningsClose": round(preClose, 4),
                "runupPct": round(pct, 2),
                "status": "ok"
            })
            runups.append(pct)
            samples += 1
            if pct > 0:
                wins += 1

        if samples > 0:
            avg = float(np.mean(runups))
            std = float(np.std(runups, ddof=1)) if samples > 1 else 0.0
            winRate = wins / samples
            summaryRows.append({
                "ticker": ticker,
                "xCount": xCount,
                "yTradingDays": y,
                "avgRunupPct": round(avg, 3),
                "stdRunupPct": round(std, 3),
                "winRate": round(winRate, 3),
                "samples": samples
            })
    return perRows, summaryRows

def pickBestYPerTicker(summaryDf, minWin=0.0, minSamples=2, score="sharpe"):
    # score options: 'avg', 'sharpe' (avg/std), 'avg_with_win'
    df = summaryDf.copy()
    df = df[df["samples"] >= minSamples]
    df = df[df["winRate"] >= minWin]
    if df.empty:
        return df

    if score == "avg":
        df["score"] = df["avgRunupPct"]
    elif score == "avg_with_win":
        df["score"] = df["avgRunupPct"] * (0.5 + 0.5 * df["winRate"])
    else:
        # sharpe-like: penalize volatility; avoid divide-by-zero
        df["score"] = df["avgRunupPct"] / df["stdRunupPct"].replace(0, np.nan)
        df["score"] = df["score"].fillna(df["avgRunupPct"])  # if std=0, fall back to avg

    # pick best row per ticker
    idx = df.groupby("ticker")["score"].idxmax()
    return df.loc[idx].sort_values("score", ascending=False)

# -------------- CLI --------------

def main():
    ap = argparse.ArgumentParser(description="Bulk pre-earnings run-up backtester (TRADING days).")
    ap.add_argument("--tickers", help="Comma-separated tickers, e.g. AAPL,MSFT,NVDA")
    ap.add_argument("--tickers-file", help="Path to a text file with one ticker per line")
    ap.add_argument("--x", type=int, default=6, help="X = number of past earnings to analyze (default 6)")
    ap.add_argument("--ys", default="5,10,15,20", help="Comma-separated Y values in TRADING days (e.g. 5,10,15,20)")
    ap.add_argument("--min-win", type=float, default=0.0, help="Minimum win rate filter (0..1)")
    ap.add_argument("--min-samples", type=int, default=2, help="Minimum samples required per Y")
    ap.add_argument("--score", choices=["avg", "sharpe", "avg_with_win"], default="sharpe", help="Ranking metric")
    ap.add_argument("--out", default="best.csv", help="CSV for best Y per ticker")
    ap.add_argument("--grid", default="all_results.csv", help="CSV for all Y results")
    ap.add_argument("--per", default="per_rows.csv", help="CSV for per-earnings rows")
    args = ap.parse_args()

    if not args.tickers and not args.tickers_file:
        raise SystemExit("Provide --tickers or --tickers-file")

    tickers = []
    if args.tickers:
        tickers += [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if args.tickers_file:
        with open(args.tickers_file, "r") as f:
            tickers += [line.strip().upper() for line in f if line.strip()]

    yValues = sorted({int(v.strip()) for v in args.ys.split(",") if v.strip()})

    allPer = []
    allSummary = []
    for t in tickers:
        perRows, summaryRows = computeRunupsForTicker(t, xCount=args.x, yValues=yValues)
        allPer.extend(perRows)
        allSummary.extend(summaryRows)

    perDf = pd.DataFrame(allPer)
    summaryDf = pd.DataFrame(allSummary)

    if not summaryDf.empty:
        bestDf = pickBestYPerTicker(
            summaryDf, minWin=args.min_win, minSamples=args.min_samples, score=args.score
        )
    else:
        bestDf = pd.DataFrame(columns=["ticker","xCount","yTradingDays","avgRunupPct","stdRunupPct","winRate","samples","score"])

    summaryDf.to_csv(args.grid, index=False)
    bestDf.to_csv(args.out, index=False)

    print(f"\nWrote grid results to {args.grid} ({len(summaryDf)} rows)")
    print(f"Wrote best-per-ticker to {args.out} ({len(bestDf)} tickers)")
    if len(bestDf) > 0:
        print("\nTop picks (head):")
        print(bestDf.head(10).to_string(index=False))
    
    perDf.to_csv(args.per, index=False)
    print(f"Wrote per-earnings rows to {args.per} ({len(perDf)} rows)")

if __name__ == "__main__":
    main()
