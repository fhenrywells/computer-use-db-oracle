from pydantic import BaseModel


class Product(BaseModel):
    asin: str
    title: str
    price: float | None = None
    brand: str | None = None

