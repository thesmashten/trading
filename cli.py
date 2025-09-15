# cli.py
import argparse
from event_study import (
    loadDaily,
    pickEvents,
    forwardReturns,
    summarize,
    makeEventTable,   # <-- new: build a table of event dates/details
)

def main():
    ap = argparse.ArgumentParser(description="Explicit-args event study runner")
    ap.add_argument("--symbol", required=True, help="Ticker symbol, e.g., NVDA")
    ap.add_argument("--percent", type=float, required=True, help="e.g. 5 for 5%%")
    ap.add_argument("--direction", choices=["up", "down", "both"], default="both")
    ap.add_argument("--horizons", default="1,3,5,10,20", help="Comma-separated days, e.g. 1,3,5")
    ap.add_argument("--cooldownDays", type=int, default=0, help="Gap (days) to avoid clustered events")
    ap.add_argument("--start", default="2012-01-01", help="History start date (YYYY-MM-DD)")
    # new quality-of-life flags:
    ap.add_argument("--showDates", type=int, default=0, help="Print first/last K event dates")
    ap.add_argument("--eventsOut", default=None, help="CSV path to save all event dates")

    args = ap.parse_args()

    # parse horizons
    horizons = []
    for x in args.horizons.split(","):
        x = x.strip()
        if not x:
            continue
        horizons.append(int(x))

    # load data and run study
    df = loadDaily(args.symbol, start=args.start)
    events = pickEvents(
        df,
        xPct=args.percent / 100.0,
        direction=args.direction,
        cooldownDays=args.cooldownDays,
    )
    outcomes = forwardReturns(df, events, horizons=horizons)
    summary = summarize(outcomes, horizons=horizons)

    # header
    print(
        "\nSymbol=" + args.symbol
        + "  Event: " + args.direction
        + " moves ≥ " + str(args.percent) + "%"
        + "  Sample=" + str(len(events))
        + ("  (cooldownDays=" + str(args.cooldownDays) + ")" if args.cooldownDays else "")
    )
    print(summary.to_string(index=False))

    # build event table for preview/export
    eventTable = makeEventTable(df, events)

    # optional: save CSV of all event dates/details
    if args.eventsOut and len(eventTable) > 0:
        eventTable.to_csv(args.eventsOut, index=False)
        print("\nSaved all event dates to:", args.eventsOut)

    # optional: print first/last K event dates
    if args.showDates > 0 and len(eventTable) > 0:
        k = args.showDates
        print("\nEvent dates (first {}):".format(k))
        print(eventTable.head(k).to_string(index=False))
        if len(eventTable) > k:
            print("\nEvent dates (last {}):".format(k))
            print(eventTable.tail(k).to_string(index=False))
    elif args.showDates > 0 and len(eventTable) == 0:
        print("\nNo qualifying events to show.")

if __name__ == "__main__":
    main()
