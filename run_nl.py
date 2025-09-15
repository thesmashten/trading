# run_nl.py
import argparse
from nlp import parseQuery
from event_study import loadDaily, pickEvents, forwardReturns, summarize

def answer(query, currentSymbol=None, start="2012-01-01", cooldownDays=3):
    params = parseQuery(query, currentSymbol=currentSymbol)
    symbol = params["symbol"]
    percentVal = params["percent"]
    if symbol is None or percentVal is None:
        return {
            "ok": False,
            "message": "Need a symbol and a percent (e.g., '7% on NVDA').",
            "parsed": params
        }

    df = loadDaily(symbol, start=start)
    events = pickEvents(df, xPct=percentVal / 100.0, direction=params["direction"], cooldownDays=cooldownDays)
    outcomes = forwardReturns(df, events, horizons=params["horizons"])
    summary = summarize(outcomes, horizons=params["horizons"])

    return {"ok": True, "parsed": params, "sample": int(len(events)), "summary": summary}

def main():
    ap = argparse.ArgumentParser(description="Natural-language event study runner")
    ap.add_argument("query", nargs="?", default=None, help="e.g. \"What happens after a 7% down day on TSLA next 3 days?\"")
    ap.add_argument("--currentSymbol", default=None, help="Used when query says 'this stock'")
    ap.add_argument("--start", default="2012-01-01")
    ap.add_argument("--cooldownDays", type=int, default=3)
    args = ap.parse_args()

    q = args.query if args.query is not None else "What happens after a 7% down day on TSLA over the next 3 and 5 sessions?"
    res = answer(q, currentSymbol=args.currentSymbol, start=args.start, cooldownDays=args.cooldownDays)

    print("Parsed:", res["parsed"])
    if not res["ok"]:
        print("Error:", res["message"])
        return
    print("Sample:", res["sample"])
    print(res["summary"].to_string(index=False))

if __name__ == "__main__":
    main()
