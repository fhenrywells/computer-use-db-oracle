def score_action(action_type: str, priors: dict[str, float]) -> float:
    return float(priors.get(action_type, 0.0))

