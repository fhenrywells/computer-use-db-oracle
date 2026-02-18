from fastapi import APIRouter

router = APIRouter()


@router.get("")
def search(q: str = "", sort: str = "relevance"):
    return {"query": q, "sort": sort, "results": []}

