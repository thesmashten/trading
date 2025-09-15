# nlp.py
import re

dirUp = {"up", "green", "rally", "rip", "spike", "pop", "gain", "pump"}
dirDown = {"down", "red", "dump", "selloff", "sell-off", "drop", "fall", "plunge"}

def parseQuery(text, currentSymbol=None):
    low = text.lower()

    # percent like "7%" or "at least 5%"
    pctMatch = re.search(r'(?:>=|≥|at least\s+)?(\d+(?:\.\d+)?)\s*%', low)
    percentVal = float(pctMatch.group(1)) if pctMatch else None

    # direction
    hasUp = False
    for w in dirUp:
        if w in low:
            hasUp = True
            break
    hasDown = False
    for w in dirDown:
        if w in low:
            hasDown = True
            break
    if hasUp and not hasDown:
        direction = "up"
    elif hasDown and not hasUp:
        direction = "down"
    else:
        direction = "both"

    # symbol like $NVDA or NVDA (very simple heuristic)
    sym = None
    tokens = re.findall(r'\$?[A-Z]{1,5}', text)
    for tok in tokens:
        t = tok.lstrip("$")
        if t not in {"AND", "FOR", "WITH", "THE"} and len(t) >= 2:
            sym = t
            break
    if sym is None:
        sym = currentSymbol

    # horizons: "next 3 days", "next 5 sessions", "next day", "next week"
    horizons = set()
    for m in re.finditer(r'next\s+(\d{1,3})\s*(days?|sessions?)', low):
        horizons.add(int(m.group(1)))
    if "next day" in low or "tomorrow" in low:
        horizons.add(1)
    if "next week" in low:
        horizons.add(5)
    if len(horizons) == 0:
        horizons = {1, 3, 5, 10, 20}

    return {
        "symbol": sym,
        "percent": percentVal,
        "direction": direction,
        "horizons": sorted(list(horizons))
    }
