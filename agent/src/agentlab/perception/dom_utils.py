from hashlib import sha256


def dom_fingerprint(raw_dom: str) -> str:
    return sha256(raw_dom.encode("utf-8")).hexdigest()

