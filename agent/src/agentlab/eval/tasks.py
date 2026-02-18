from pathlib import Path
import json


def load_task_templates(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)

