# event_study.py
import numpy as np
import pandas as pd
import yfinance as yf

def loadDaily(symbol, start="2012-01-01", end=None):
    df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if df is None or len(df) == 0:
        raise ValueError("No data for " + symbol)
    df = df.rename(columns=str.title)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df["ret1"] = df["Close"].pct_change()
    return df

def pickEvents(df, xPct, direction="both", cooldownDays=0):
    upMask = df["ret1"] >= xPct
    downMask = df["ret1"] <= -xPct
    if direction == "up":
        mask = upMask
    elif direction == "down":
        mask = downMask
    else:
        mask = upMask | downMask

    idx = df.index[mask]
    if cooldownDays <= 0:
        return idx

    kept = []
    last = None
    for t in idx:
        if last is None or (t - last).days > cooldownDays:
            kept.append(t)
            last = t
    return pd.DatetimeIndex(kept)

def forwardReturns(df, eventIndex, horizons=(1, 3, 5, 10, 20)):
    close = df["Close"]
    posByTs = {}
    for ts in eventIndex:
        if ts in close.index:
            posByTs[ts] = close.index.get_loc(ts)

    rows = []
    for ts, i in posByTs.items():
        row = {"t": ts}
        for h in horizons:
            j = i + h
            if j >= len(close):
                row["R+" + str(h)] = np.nan
            else:
                row["R+" + str(h)] = (close.iloc[j] / close.iloc[i] - 1.0).item()
        rows.append(row)

    if len(rows) == 0:
        return pd.DataFrame(columns=["t"] + ["R+" + str(h) for h in horizons]).set_index("t")
    return pd.DataFrame(rows).set_index("t").sort_index()

def summarize(outcomes, horizons=(1, 3, 5, 10, 20)):
    summary = []
    for h in horizons:
        col = "R+" + str(h)
        s = outcomes[col].dropna() if col in outcomes.columns else pd.Series([], dtype=float)
        n = int(s.shape[0])

        meanVal = float(s.mean()) if n > 0 else np.nan
        medianVal = float(s.median()) if n > 0 else np.nan
        stdVal = float(s.std(ddof=1)) if n > 1 else np.nan
        winRate = float((s > 0).mean()) if n > 0 else np.nan

        p5 = float(np.percentile(s, 5)) if n > 0 else np.nan
        p25 = float(np.percentile(s, 25)) if n > 0 else np.nan
        p75 = float(np.percentile(s, 75)) if n > 0 else np.nan
        p95 = float(np.percentile(s, 95)) if n > 0 else np.nan

        minVal = float(s.min()) if n > 0 else np.nan
        maxVal = float(s.max()) if n > 0 else np.nan

        summary.append({
            "Horizon": f"+{h}d",
            "N": n,
            "Mean": meanVal,
            "Median": medianVal,
            "Std": stdVal,
            "WinRate(>0)": winRate,
            "Min": minVal,
            "P5": p5,
            "P25": p25,
            "P75": p75,
            "P95": p95,
            "Max": maxVal
        })
    return pd.DataFrame(summary)

def makeEventTable(df, eventIndex):
    """
    Build a compact table of event dates and details.
    Columns: Date, EventMovePct (close/close), Open, Close, Volume
    """
    rows = []
    for ts in eventIndex:
        rows.append({
            "Date": ts.strftime("%Y-%m-%d"),
            "EventMovePct": float(df.loc[ts, "ret1"]),  # already close/close % change
            "Open": float(df.loc[ts, "Open"]),
            "Close": float(df.loc[ts, "Close"]),
            "Volume": int(df.loc[ts, "Volume"])
        })
    if not rows:
        return pd.DataFrame(columns=["Date", "EventMovePct", "Open", "Close", "Volume"])
    return pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
