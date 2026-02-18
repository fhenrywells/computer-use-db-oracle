from typing import Any


def classify_view(dom: dict[str, Any], catalog: dict[str, Any]) -> tuple[str, float]:
    truth = dom.get("truth_view_id")
    if truth:
        return str(truth), 1.0
    for view in catalog.get("views", []):
        if view.get("root_selector") in dom.get("selectors", []):
            return str(view["view_id"]), 0.8
    return "UNKNOWN", 0.0

