from typing import Any


def extract_state_vars(dom: dict[str, Any], view_id: str, catalog: dict[str, Any]) -> dict[str, Any]:
    for view in catalog.get("views", []):
        if view.get("view_id") == view_id:
            vars_out: dict[str, Any] = {}
            for var in view.get("state_vars", []):
                vars_out[var["name"]] = dom.get("state_vars", {}).get(var["name"], var.get("default"))
            return vars_out
    return {}

