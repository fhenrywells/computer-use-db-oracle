from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import app.routes.admin as admin
import app.routes.cart as cart
import app.routes.checkout as checkout
import app.routes.products as products
import app.routes.search as search
import app.routes.ui as ui

app = FastAPI(title="simazon-api")
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(cart.router, prefix="/cart", tags=["cart"])
app.include_router(checkout.router, prefix="/checkout", tags=["checkout"])
app.include_router(ui.router, tags=["ui"])
app.include_router(admin.router)

artifacts_dir = Path("experiments/artifacts")
artifacts_dir.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=artifacts_dir), name="artifacts")
