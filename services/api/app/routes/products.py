from fastapi import APIRouter

router = APIRouter()


@router.get("/{asin}")
def get_product(asin: str):
    return {"asin": asin}

