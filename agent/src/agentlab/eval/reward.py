def progress_events(prev_state: dict, next_state: dict) -> list[str]:
    events: list[str] = []
    if len(next_state.get("cart_asins", [])) > len(prev_state.get("cart_asins", [])):
        events.append("AddedToCart")
    return events

