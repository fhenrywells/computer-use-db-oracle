from typing import Any


def next_action(task: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    _ = (task, observation)
    return {"type": "NoOp", "args": {"reason": "baseline random-freeform placeholder"}}
