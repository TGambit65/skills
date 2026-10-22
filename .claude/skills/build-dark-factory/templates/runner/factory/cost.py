"""Token accounting, on from the first run. FACTORY_RULES.md 8.

Instrumented on day one rather than added after the first surprising invoice, because
cost projections for this are wrong by 10-20x in the same direction every time. One
"implement an issue" run is five agent sessions plus a mutation suite plus a soak, and
from the outside it looks like one prompt.

    python factory/cost.py record <run-id>          # fold node usage into the run record
    python factory/cost.py report                   # per-run and per-node totals
    python factory/cost.py daily [<cap-usd>]        # today's total; exit 1 when >= cap

THE AGGREGATE GUARD. `--max-budget-usd` caps ONE agent invocation. Nothing capped the day:
a dispatcher on a 30-minute cron with a stuck fix loop runs 48 laps, each under its own
cap, and the first anyone hears of it is the invoice. `daily` folds every run record
whose id starts with today's UTC date and the orchestrator refuses to dispatch at or
above FACTORY_MAX_DAILY_USD. The run records ARE the durable counter - one JSON per run,
written by the EXIT trap in run-workflow.sh, so a run that died mid-lap still counts.

What it cannot see: a lap that is still running has not written its record yet, so the
real ceiling is FACTORY_MAX_DAILY_USD plus FACTORY_MAX_PARALLEL x FACTORY_MAX_BUDGET_USD.
And it counts what the agent REPORTED: an agent whose JSON carries no cost figure
produces a day that reads as unmeasured, which is printed, not silently treated as zero.

Node usage is read from .factory/runs/<run>/nodes/*.json, which each node writes from the
`--output-format json` envelope its agent returns. No estimation, no modelling: if a
number is not measured it is not reported, because an invented cost figure is worse than
no cost figure -- it gets believed.
"""
from __future__ import annotations
import glob
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, ".factory", "runs")


def node_usage(run: str) -> list[dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(RUNS, run, "nodes", "*.json"))):
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        u = d.get("usage", d)
        out.append({
            "node": os.path.splitext(os.path.basename(path))[0],
            "model": d.get("model", "?"),
            "input": u.get("input_tokens", 0),
            "output": u.get("output_tokens", 0),
            "cache_read": u.get("cache_read_input_tokens", 0),
            "cost_usd": d.get("total_cost_usd"),
        })
    return out


def cmd_record(argv: list[str]) -> int:
    run = argv[0]
    rec_path = os.path.join(RUNS, f"{run}.json")
    record = {}
    if os.path.exists(rec_path):
        with open(rec_path, encoding="utf-8") as fh:
            record = json.load(fh)
    nodes = node_usage(run)
    record["nodes"] = nodes
    record["tokens"] = {
        "input": sum(n["input"] for n in nodes),
        "output": sum(n["output"] for n in nodes),
        "cache_read": sum(n["cache_read"] for n in nodes),
    }
    costs = [n["cost_usd"] for n in nodes if isinstance(n["cost_usd"], (int, float))]
    #  Reported only when every node reported one. A partial total reads as a full total
    #  and is the number somebody will quote later.
    record["cost_usd"] = round(sum(costs), 4) if len(costs) == len(nodes) and nodes else None
    record["cost_complete"] = bool(nodes) and len(costs) == len(nodes)
    os.makedirs(RUNS, exist_ok=True)
    with open(rec_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    t = record["tokens"]
    print(f"COST_RECORDED run={run} nodes={len(nodes)} "
          f"in={t['input']} out={t['output']} cached={t['cache_read']} "
          f"usd={record['cost_usd'] if record['cost_complete'] else 'incomplete'}")
    return 0


def cmd_report(_argv: list[str]) -> int:
    runs = sorted(glob.glob(os.path.join(RUNS, "*.json")))
    total_in = total_out = 0
    per_node: dict[str, dict] = {}
    counted = 0
    print(f"{'run':<20} {'nodes':>5} {'input':>10} {'output':>9} {'usd':>8}")
    for path in runs:
        if os.path.basename(path) == "last.json":
            continue
        with open(path, encoding="utf-8") as fh:
            r = json.load(fh)
        t = r.get("tokens")
        if not t:
            continue
        counted += 1
        total_in += t["input"]
        total_out += t["output"]
        usd = r.get("cost_usd")
        print(f"{r.get('run','?'):<20} {len(r.get('nodes',[])):>5} "
              f"{t['input']:>10,} {t['output']:>9,} "
              f"{(f'{usd:.2f}' if usd is not None else '  --'):>8}")
        for n in r.get("nodes", []):
            d = per_node.setdefault(n["node"], {"input": 0, "output": 0, "runs": 0})
            d["input"] += n["input"]
            d["output"] += n["output"]
            d["runs"] += 1

    print(f"\nRUNS_COUNTED={counted}")
    if not counted:
        print("No instrumented runs yet. This is a report of nothing, not a report of "
              "zero cost.")
        return 0
    print(f"TOTAL input={total_in:,} output={total_out:,}")
    print("\nper node, averaged across runs:")
    for name, d in sorted(per_node.items(), key=lambda kv: -kv[1]["output"]):
        print(f"  {name:<12} runs={d['runs']:<3} "
              f"avg_in={d['input'] // d['runs']:>9,} "
              f"avg_out={d['output'] // d['runs']:>8,}")
    print("\nThe plan node should dominate output tokens and cost. If it does not, the "
          "premium model is in the wrong slot (FACTORY_RULES.md 8).")
    return 0


def today_utc() -> str:
    """Today's date as YYYYMMDD in UTC, matching the run ids run-workflow.sh stamps."""
    import datetime
    # UTC, because run-workflow.sh stamps the run id with `date -u`.
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")


def daily_total(day: str) -> "tuple[float, int, int]":
    """(usd, runs counted, runs with no cost figure at all) for run ids dated `day`.

    Run ids are `<YYYYMMDD>T<HHMMSS>-<workflow>`, so the date is in the filename and no
    clock on the record is trusted. Partial records count what they have: a node that
    reported a cost is spend whether or not its siblings did. Under-counting is the
    direction this must not err in.
    """
    usd = 0.0
    counted = unmeasured = 0
    for path in sorted(glob.glob(os.path.join(RUNS, f"{day}T*.json"))):
        try:
            with open(path, encoding="utf-8") as fh:
                r = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        counted += 1
        costs = [n.get("cost_usd") for n in r.get("nodes", [])]
        costs = [c for c in costs if isinstance(c, (int, float))]
        if costs:
            usd += sum(costs)
        elif isinstance(r.get("cost_usd"), (int, float)):
            usd += r["cost_usd"]
        else:
            unmeasured += 1
    return round(usd, 4), counted, unmeasured


def cmd_daily(argv: "list[str]") -> int:
    """Print today's spend; exit 1 when it has reached the cap or the cap is not a finite number."""
    cap = None
    if argv:
        try:
            cap = float(argv[0])
        except ValueError:
            print(f"DAILY_CAP_INVALID {argv[0]!r} is not a number; refusing rather than guessing")
            return 1
        # float() accepts "nan" and "inf". NaN compares false both ways, so `usd >= cap`
        # never fires and the cap is silently off while reading as on.
        if not math.isfinite(cap):
            print(f"DAILY_CAP_INVALID {argv[0]!r} is not a finite number; refusing rather than guessing")
            return 1
    day = today_utc()
    usd, counted, unmeasured = daily_total(day)
    line = f"DAILY_SPEND day={day} usd={usd:.2f} runs={counted} unmeasured={unmeasured}"
    if cap is None or cap <= 0:
        print(line + " cap=off")
        return 0
    if usd >= cap:
        print(line + f" cap={cap:.2f} OVER")
        return 1
    print(line + f" cap={cap:.2f} ok")
    return 0


COMMANDS = {"record": cmd_record, "report": cmd_report, "daily": cmd_daily}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(COMMANDS[sys.argv[1]](sys.argv[2:]))
