# run_nl.py
import sys
import argparse
from nlp import parseQuery
from event_study import (
    loadDaily,
    pickEvents,
    forwardReturns,
    summarize,
    makeEventTable,   # make sure this exists in event_study.py
)

def answer(query, currentSymbol=None, start="2012-01-01", cooldownDays=3, showDates=0, eventsOut=None):
    params = parseQuery(query, currentSymbol=currentSymbol)

    symbol = params.get("symbol")
    percentVal = params.get("percent")

    if symbol is None or percentVal is None:
        return {
            "ok": False,
            "message": "Need a symbol and a percent (e.g., '8% on TSLA').",
            "parsed": params,
            "sample": 0,
            "summary": None,
            "events": None,
            "preview": None,
            "eventsOut": eventsOut,
        }

    df = loadDaily(symbol, start=start)
    events = pickEvents(
        df,
        xPct=percentVal / 100.0,
        direction=params.get("direction", "both"),
        cooldownDays=cooldownDays,
    )
    outcomes = forwardReturns(df, events, horizons=params.get("horizons", (1,3,5,10,20)))
    summary = summarize(outcomes, horizons=params.get("horizons", (1,3,5,10,20)))
    eventTable = makeEventTable(df, events)

    # CSV export
    if eventsOut and len(eventTable) > 0:
        eventTable.to_csv(eventsOut, index=False)

    # Preview first/last K
    preview = None
    if showDates > 0 and len(eventTable) > 0:
        head = eventTable.head(showDates)
        tail = eventTable.tail(showDates) if len(eventTable) > showDates else eventTable.iloc[0:0]
        preview = {"head": head, "tail": tail}

    return {
        "ok": True,
        "parsed": params,
        "sample": int(len(events)),
        "summary": summary,
        "events": eventTable,
        "preview": preview,
        "eventsOut": eventsOut,
    }

def main():
    ap = argparse.ArgumentParser(description="Natural-language event study runner")
    ap.add_argument("query", nargs="?", default=None)
    ap.add_argument("--currentSymbol", default=None)
    ap.add_argument("--start", default="2012-01-01")
    ap.add_argument("--cooldownDays", type=int, default=3)
    ap.add_argument("--showDates", type=int, default=0, help="Print first/last K event dates")
    ap.add_argument("--eventsOut", default=None, help="CSV path to save all event dates")
    args = ap.parse_args()

    # Default demo query if none provided
    q = args.query or "What happens after an 8% down day on TSLA over the next 3 sessions?"

    res = answer(
        q,
        currentSymbol=args.currentSymbol,
        start=args.start,
        cooldownDays=args.cooldownDays,
        showDates=args.showDates,
        eventsOut=args.eventsOut,
    )

    # Always show how we parsed the query
    print("Parsed:", res["parsed"], flush=True)

    if not res["ok"]:
        print("Error:", res["message"], flush=True)
        return

    print("Sample:", res["sample"], flush=True)
    print(res["summary"].to_string(index=False), flush=True)

    if res["preview"] is not None:
        k = args.showDates
        print(f"\nEvent dates (first {k}):", flush=True)
        print(res["preview"]["head"].to_string(index=False), flush=True)
        if res["preview"]["tail"].shape[0] > 0:
            print(f"\nEvent dates (last {k}):", flush=True)
            print(res["preview"]["tail"].to_string(index=False), flush=True)

    if res["eventsOut"] is not None:
        print("\nSaved all event dates to:", res["eventsOut"], flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Print the error so "silent failures" are obvious
        print("Unhandled error:", repr(e), file=sys.stderr, flush=True)
        raise
