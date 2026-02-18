from pathlib import Path
import json


def load_task_templates(path: str | Path) -> list[dict]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if text.startswith("version https://git-lfs.github.com/spec/v1"):
        raise RuntimeError(
            f"Task file is a Git LFS pointer, not JSON data: {p}. "
            "Ensure this file is not LFS-tracked for deployment, or fetch real LFS objects before running."
        )
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Task file is not valid JSON: {p} ({exc})") from exc
    if not isinstance(data, list):
        raise RuntimeError(f"Task file must contain a JSON array: {p}")
    return data
