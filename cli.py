# cli.py
import argparse
from event_study import loadDaily, pickEvents, forwardReturns, summarize

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--percent", type=float, required=True, help="e.g. 5 for 5%")
    ap.add_argument("--direction", choices=["up", "down", "both"], default="both")
    ap.add_argument("--horizons", default="1,3,5,10,20")
    ap.add_argument("--cooldownDays", type=int, default=0)
    ap.add_argument("--start", default="2012-01-01")
    args = ap.parse_args()

    horizons = []
    for x in args.horizons.split(","):
        horizons.append(int(x))

    df = loadDaily(args.symbol, start=args.start)
    events = pickEvents(df, xPct=args.percent / 100.0, direction=args.direction, cooldownDays=args.cooldownDays)
    outcomes = forwardReturns(df, events, horizons=horizons)
    summary = summarize(outcomes, horizons=horizons)

    print("\nSymbol=" + args.symbol + "  Event: " + args.direction + " moves ≥ " + str(args.percent) + "%  Sample=" + str(len(events)))
    print(summary.to_string(index=False))

if __name__ == "__main__":
    main()
