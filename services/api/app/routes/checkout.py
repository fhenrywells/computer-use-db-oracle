from fastapi import APIRouter

router = APIRouter()


@router.post("")
def checkout():
    return {"status": "ok"}

