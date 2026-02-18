from fastapi import APIRouter

router = APIRouter()


@router.get("")
def get_cart():
    return {"items": [], "count": 0}


@router.post("/items")
def add_item(asin: str, qty: int = 1):
    return {"asin": asin, "qty": qty}

