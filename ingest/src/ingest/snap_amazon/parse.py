from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Iterable


def _expand_inputs(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        if any(ch in item for ch in ["*", "?", "["]):
            paths.extend(Path(p) for p in glob.glob(item))
            continue

        p = Path(item)
        if p.is_dir():
            paths.extend(sorted(p.rglob("*.jsonl")))
        elif p.exists():
            paths.append(p)
        else:
            paths.extend(Path(x) for x in glob.glob(item))

    out = sorted({p.resolve() for p in paths if p.suffix == ".jsonl"})
    return out


def parse_records(inputs: list[str], limit: int | None = None) -> Iterable[tuple[dict, str]]:
    files = _expand_inputs(inputs)
    seen = 0
    for path in files:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                yield record, path.name
                seen += 1
                if limit is not None and seen >= limit:
                    return
