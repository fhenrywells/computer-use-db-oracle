def oracle_satisfied(task_materialized: dict, final_state: dict, expected_asin: str | None = None) -> bool:
    oracle = task_materialized.get("oracle", {})
    otype = oracle.get("type")
    cart = final_state.get("cart_asins", [])
    if not isinstance(cart, list):
        return False

    if otype == "exact_asin_in_cart":
        target = expected_asin or oracle.get("expected_asin")
        return bool(target) and target in cart

    if otype in {"min_price_match", "max_rating_match"}:
        return bool(expected_asin) and expected_asin in cart
    if otype == "related_edge_match":
        target = expected_asin or oracle.get("expected_asin")
        return bool(target) and target in cart

    return False
