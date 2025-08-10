import os, sys, datetime, requests, pandas as pd, matplotlib.pyplot as plt

def toOccSymbol(ticker, expiryYmd, callPut, strike):
    y = expiryYmd[2:4]; m = expiryYmd[5:7]; d = expiryYmd[8:10]
    strikeInt = int(round(float(strike) * 1000))
    strikePart = str(strikeInt).rjust(8, "0")
    return f"{ticker.upper()}{y}{m}{d}{callPut.upper()}{strikePart}"

def polygonBars(occWithPrefix, startDate, endDate, apiKey):
    url = f"https://api.polygon.io/v2/aggs/ticker/{occWithPrefix}/range/1/minute/{startDate}/{endDate}"
    params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": apiKey}
    r = requests.get(url, params=params)
    r.raise_for_status()
    j = r.json()
    if "results" not in j or not j["results"]:
        return pd.DataFrame()
    df = pd.DataFrame(j["results"])
    df["ts"] = pd.to_datetime(df["t"], unit="ms")
    df.rename(columns={"o":"open","h":"high","l":"low","c":"close","v":"volume"}, inplace=True)
    return df[["ts","open","high","low","close","volume"]]

def tradierBars(tradierSym, startIso, endIso, apiKey):
    url = "https://api.tradier.com/v1/markets/timesales"
    params = {"symbol": tradierSym, "interval": "1min", "start": startIso, "end": endIso, "session_filter": "all"}
    headers = {"Authorization": f"Bearer {apiKey}", "Accept": "application/json"}
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    j = r.json()
    # avoid .get() per your style; do key checks explicitly
    if "series" not in j: return pd.DataFrame()
    series = j["series"]
    if not series or "data" not in series or not series["data"]:
        return pd.DataFrame()
    df = pd.DataFrame(series["data"])
    df["ts"] = pd.to_datetime(df["time"])
    return df[["ts","open","high","low","close","volume"]]

def makeChart(df, title, pngPath):
    plt.figure(figsize=(10,4.5))
    plt.plot(df["ts"], df["close"])
    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.tight_layout()
    plt.savefig(pngPath, dpi=160)
    plt.close()

def main():
    if len(sys.argv) < 5:
        print("Usage: python optionIntraday.py <ticker> <YYYY-MM-DD> <C|P> <strike>")
        sys.exit(1)

    ticker = sys.argv[1]
    expiryYmd = sys.argv[2]
    callPut = sys.argv[3]
    strike = sys.argv[4]

    today = datetime.date.today().isoformat()
    startIso = today + " 09:30"
    endIso = today + " 16:00"

    occCore = toOccSymbol(ticker, expiryYmd, callPut, strike)  # e.g., GOOGL240920C00185000
    occPolygon = "O:" + occCore

    polygonKey = os.environ.get("POLYGON_KEY")
    tradierKey = os.environ.get("TRADIER_KEY")

    if polygonKey:
        df = polygonBars(occPolygon, today, today, polygonKey)
        provider = "Polygon"
    elif tradierKey:
        df = tradierBars(occCore, startIso, endIso, tradierKey)
        provider = "Tradier"
    else:
        print("Set POLYGON_KEY or TRADIER_KEY in your environment.")
        sys.exit(2)

    if df.empty:
        print(f"No data returned for {occCore} from {provider} (market closed or contract illiquid?).")
        sys.exit(3)

    base = f"{occCore}_{today}"
    csvPath = base + ".csv"
    pngPath = base + ".png"
    df.to_csv(csvPath, index=False)
    title = f"{ticker} {expiryYmd} {callPut.upper()} {strike} — {provider} minute bars"
    makeChart(df, title, pngPath)

    first = df.iloc[0]["close"]
    last = df.iloc[-1]["close"]
    changePct = (last - first) / first * 100 if first else 0.0

    print(f"Wrote {csvPath} ({len(df)} rows)")
    print(f"Wrote {pngPath}")
    print(f"Open: {round(first,2)}  Last: {round(last,2)}  Change: {round(changePct,2)}%")

if __name__ == "__main__":
    main()
