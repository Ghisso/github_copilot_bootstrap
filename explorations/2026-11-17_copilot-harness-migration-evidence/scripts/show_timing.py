"""Hook phase durations (start to end of each hook event) for one or more runs."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse(stamp: str) -> float:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


for run in sys.argv[1:]:
    events = [json.loads(line) for line in (Path(run) / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    starts: dict[str, tuple[str, float]] = {}
    durations: dict[str, list[float]] = defaultdict(list)
    failures: list[str] = []
    for event in events:
        data = event.get("data", {})
        if event.get("type") == "hook.start":
            starts[data.get("hookInvocationId")] = (data.get("hookType"), parse(event["timestamp"]))
        elif event.get("type") == "hook.end":
            hook_type, begin = starts.get(data.get("hookInvocationId"), (data.get("hookType"), None))
            if begin is not None:
                durations[hook_type].append(parse(event["timestamp"]) - begin)
            if data.get("success") is False or data.get("error"):
                failures.append(f"{hook_type}: {json.dumps(data.get('error'))[:260]}")
    print(f"== {Path(run).name}")
    for hook_type, values in sorted(durations.items()):
        print(f"  {hook_type:22s} n={len(values):3d} max={max(values):6.2f}s mean={sum(values) / len(values):6.2f}s")
    for failure in failures[:8]:
        print("  FAILED", failure)
