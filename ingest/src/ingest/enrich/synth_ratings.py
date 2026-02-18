def synthesize_rating(price: float | None) -> float:
    if price is None:
        return 3.5
    return max(1.0, min(5.0, 5.0 - (price / 500.0)))

