# Move Study — “What happens after an X% move?”

A tiny research tool that answers:

> “What happens historically after an **X%** move (up/down) in **this stock** over the next **N** sessions?”

It supports **natural-language queries** (NL) and a direct **CLI flow**.

---

## 📂 Project Structure

```
move-study/
├─ README.md          # this file
├─ event_study.py     # analytics engine (core math)
├─ nlp.py             # natural language parser → params
├─ run_nl.py          # glue runner (NL → results)
└─ cli.py             # explicit CLI runner (no NLP)
```

---

## ⚙️ Installation

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install pandas numpy yfinance
```

2. You’re ready to run.

---

## 🚀 Usage

### A) Natural-language queries

```bash
# General format
python run_nl.py "YOUR QUESTION"

# Examples
python run_nl.py "What happens after a 7% down day on TSLA over the next 3 and 5 sessions?"
python run_nl.py "Show NVDA after a +5% daily move — next day and next week"
python run_nl.py "What happens after a 4% move in this stock?" --currentSymbol AAPL
python run_nl.py "After a 6% drop on MSFT next 1,3,10 days" --cooldownDays 0
```

#### Optional flags
- `--currentSymbol SYMBOL` → used when the query says *“this stock”*.
- `--start YYYY-MM-DD` → limit history start date (default `2012-01-01`).
- `--cooldownDays N` → enforce a gap between events (default `3` in `run_nl.py`).

---

### B) Explicit CLI (no NLP)

```bash
# General format
python cli.py --symbol SYMBOL --percent X --direction up|down|both [--horizons 1,3,5,...] [--cooldownDays N]

# Example
python cli.py --symbol ANET --percent 8 --direction down
```

---

## 📊 Sample Output

**Query:**
```bash
python run_nl.py "What happens after a 7% down day on TSLA over the next 3 and 5 sessions?"
```

**Output:**
```
Parsed: {'symbol': 'TSLA', 'percent': 7.0, 'direction': 'down', 'horizons': [3, 5]}
Sample: 74
 Horizon   N     Mean   Median      Std  WinRate(>0)        P5       P25      P75      P95
    +3d   74  0.0169   0.0168   0.0723     0.59    -0.097   -0.035    0.067    0.129
    +5d   74  0.0136   0.0240   0.0919     0.59    -0.129   -0.027    0.057    0.132
```

---

## ❓ What is *cooldown*?

- **Cooldown** = the minimum gap (in days) enforced between qualifying events.  
- Example: if TSLA falls 8% on Monday and 9% on Tuesday:
  - With `--cooldownDays 0`: **both** days are counted as events.
  - With `--cooldownDays 3`: only **Monday** is kept (Tuesday is skipped, since it’s within 3 days of another event).  

This prevents double-counting **clusters** (like multi-day crashes) that would otherwise overweight your stats.

---

## ✅ Summary

- `event_study.py` → the analytics brain (loads prices, finds events, computes outcomes).  
- `nlp.py` → parses natural language into parameters.  
- `run_nl.py` → glue: parse NL → run engine → print results.  
- `cli.py` → manual runner with explicit flags.  

Start with:

```bash
python run_nl.py "What happens after a 7% down day on TSLA?"
```
