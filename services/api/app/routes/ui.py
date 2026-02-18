from __future__ import annotations

import html
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.db.mongo import get_db

router = APIRouter()

# Lightweight in-memory cart store for local experimentation.
_CARTS: dict[str, list[str]] = {}

_VIEW_COLORS = {
    "HOME": "#ad2831",
    "SEARCH_RESULTS": "#1d4ed8",
    "EMPTY_RESULTS": "#1d4ed8",
    "PRODUCT_DETAIL": "#0f766e",
    "CART": "#b45309",
}


def _cart_for(sid: str) -> list[str]:
    return _CARTS.setdefault(sid, [])


def _base_html(view_id: str, sid: str, cart_asins: list[str], body: str) -> str:
    color = _VIEW_COLORS.get(view_id, "#334155")
    cart_count = len(cart_asins)
    cart_csv = ",".join(cart_asins)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="view-id" content="{view_id}" />
  <title>Simazon {view_id}</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; margin: 0; background: #f8fafc; }}
    .banner {{ background: {color}; color: white; padding: 12px 16px; font-weight: 700; }}
    .wrap {{ max-width: 1100px; margin: 16px auto; padding: 0 16px; }}
    .row {{ display: flex; gap: 16px; align-items: flex-start; }}
    .col {{ background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; }}
    .facet-col {{ width: 280px; }}
    .results-col {{ flex: 1; }}
    .card {{ border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; margin: 8px 0; background: #fff; }}
    .chip {{ display: inline-block; border: 1px solid #cbd5e1; border-radius: 999px; padding: 4px 8px; margin: 4px 4px 0 0; font-size: 12px; }}
    .btn {{ display: inline-block; border: 1px solid #94a3b8; border-radius: 6px; padding: 6px 10px; text-decoration: none; color: #111827; background: #f8fafc; margin-right: 6px; margin-top: 6px; }}
    .btn-primary {{ background: #2563eb; border-color: #2563eb; color: white; }}
    .muted {{ color: #64748b; font-size: 13px; }}
    input, select {{ padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; }}
  </style>
</head>
<body>
  <div class="banner" data-testid="view-banner">{view_id}</div>
  <div class="wrap">
    <div class="muted">session <span data-testid="session-id">{sid}</span></div>
    <div class="muted">cart_count <span data-testid="cart-count">{cart_count}</span></div>
    <div data-testid="cart-asins" data-asins="{html.escape(cart_csv)}" style="display:none"></div>
    {body}
  </div>
</body>
</html>"""


def _search_docs(
    q: str,
    brand: str | None,
    category: str | None,
    sort: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    db = get_db()
    col = db["products"]
    and_parts: list[dict[str, Any]] = []
    tokens = [t for t in q.strip().split() if t]
    for t in tokens:
        rx = {"$regex": t, "$options": "i"}
        and_parts.append({"$or": [{"title": rx}, {"brand": rx}, {"category_leaf": rx}]})
    if brand:
        and_parts.append({"brand": brand})
    if category:
        and_parts.append({"category_leaf": category})
    filt = {"$and": and_parts} if and_parts else {}

    cursor = col.find(
        filt,
        {"_id": 0, "asin": 1, "title": 1, "brand": 1, "price": 1, "rating_avg": 1, "category_leaf": 1},
    )
    if sort == "price_asc":
        cursor = cursor.sort([("price", 1), ("asin", 1)])
    elif sort == "rating_desc":
        cursor = cursor.sort([("rating_avg", -1), ("asin", 1)])
    else:
        cursor = cursor.sort([("rating_count", -1), ("asin", 1)])
    return list(cursor.limit(limit))


def _top_values(field: str, limit: int = 12) -> list[str]:
    db = get_db()
    col = db["products"]
    rows = list(
        col.aggregate(
            [
                {"$match": {field: {"$type": "string", "$ne": ""}}},
                {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": limit},
            ]
        )
    )
    return [r["_id"] for r in rows]


@router.get("/ui", response_class=HTMLResponse)
def ui_home(sid: str = Query(default="")):
    sid = sid or uuid.uuid4().hex[:8]
    cart = _cart_for(sid)
    body = f"""
    <main data-testid="view-home">
      <form action="/ui/search" method="get">
        <input type="hidden" name="sid" value="{sid}" />
        <input data-testid="search-input" name="q" value="" placeholder="Search products" />
        <button data-testid="search-submit" class="btn btn-primary" type="submit">Search</button>
      </form>
      <a class="btn" data-testid="nav-cart" href="/ui/cart?sid={sid}">Go to Cart</a>
    </main>
    """
    return HTMLResponse(_base_html("HOME", sid, cart, body))


@router.get("/ui/search", response_class=HTMLResponse)
def ui_search(
    sid: str = Query(...),
    q: str = Query(default=""),
    sort: str = Query(default="relevance"),
    brand: str = Query(default=""),
    category: str = Query(default=""),
):
    cart = _cart_for(sid)
    results = _search_docs(q, brand or None, category or None, sort)
    brands = _top_values("brand")
    categories = _top_values("category_leaf")
    view_id = "SEARCH_RESULTS" if results else "EMPTY_RESULTS"

    facets = "".join(
        f'<a class="chip" data-testid="facet-brand-{html.escape(b)}" href="/ui/search?sid={sid}&q={html.escape(q)}&sort={sort}&brand={html.escape(b)}&category={html.escape(category)}">{html.escape(b)}</a>'
        for b in brands
    )
    categories_html = "".join(
        f'<a class="chip" data-testid="facet-category-{html.escape(c)}" href="/ui/search?sid={sid}&q={html.escape(q)}&sort={sort}&brand={html.escape(brand)}&category={html.escape(c)}">{html.escape(c)}</a>'
        for c in categories
    )
    cards = []
    for i, r in enumerate(results, start=1):
        asin = r.get("asin", "")
        cards.append(
            f"""
            <div class="card" data-testid="result-card" data-asin="{html.escape(asin)}">
              <div><strong>{i}. {html.escape(str(r.get("title", "")))}</strong></div>
              <div class="muted">{html.escape(str(r.get("brand", "")))} | ${r.get("price")} | rating {r.get("rating_avg")}</div>
              <a class="btn btn-primary" data-testid="open-product" href="/ui/product/{html.escape(asin)}?sid={sid}&q={html.escape(q)}&sort={sort}&brand={html.escape(brand)}&category={html.escape(category)}">Open</a>
            </div>
            """
        )

    body = f"""
    <main data-testid="view-search-results">
      <form action="/ui/search" method="get">
        <input type="hidden" name="sid" value="{sid}" />
        <input data-testid="search-input" name="q" value="{html.escape(q)}" />
        <select data-testid="sort-select" name="sort">
          <option value="relevance" {"selected" if sort=="relevance" else ""}>relevance</option>
          <option value="price_asc" {"selected" if sort=="price_asc" else ""}>price_asc</option>
          <option value="rating_desc" {"selected" if sort=="rating_desc" else ""}>rating_desc</option>
        </select>
        <button class="btn btn-primary" data-testid="search-submit" type="submit">Apply</button>
      </form>
      <a class="btn" data-testid="nav-cart" href="/ui/cart?sid={sid}">Cart</a>
      <div class="row">
        <div class="col facet-col" data-testid="facet-panel">
          <h4>Brand</h4>
          {facets}
          <h4>Category</h4>
          {categories_html}
        </div>
        <div class="col results-col" data-testid="results-list">
          <div class="muted" data-testid="result-count">{len(results)}</div>
          {"".join(cards) if cards else '<div data-testid="empty-results-message">No results</div>'}
        </div>
      </div>
    </main>
    """
    return HTMLResponse(_base_html(view_id, sid, cart, body))


@router.get("/ui/product/{asin}", response_class=HTMLResponse)
def ui_product(
    asin: str,
    sid: str = Query(...),
    edge: str = Query(default="also_bought"),
    q: str = Query(default=""),
    sort: str = Query(default="relevance"),
    brand: str = Query(default=""),
    category: str = Query(default=""),
):
    cart = _cart_for(sid)
    db = get_db()
    product = db["products"].find_one({"asin": asin}, {"_id": 0})
    if not product:
        return HTMLResponse(_base_html("PRODUCT_DETAIL", sid, cart, f"<main>Product {html.escape(asin)} not found</main>"), status_code=404)

    related = product.get("related") if isinstance(product.get("related"), dict) else {}
    related_raw = related.get(edge, [])
    if isinstance(related_raw, str):
        related_asins = [related_raw]
    elif isinstance(related_raw, list):
        related_asins = [str(a) for a in related_raw if str(a).strip()]
    else:
        related_asins = []
    if related_asins:
        related_docs = list(
            db["products"].find({"asin": {"$in": related_asins}}, {"_id": 0, "asin": 1, "title": 1}).limit(10)
        )
    else:
        related_docs = []

    related_html = "".join(
        f'<a class="chip" data-testid="related-item" data-asin="{html.escape(r["asin"])}" href="/ui/product/{html.escape(r["asin"])}?sid={sid}&edge={edge}&q={html.escape(q)}&sort={sort}&brand={html.escape(brand)}&category={html.escape(category)}">{html.escape(r["title"][:60])}</a>'
        for r in related_docs
    )
    body = f"""
    <main data-testid="view-product-detail">
      <div data-testid="product-asin">{html.escape(str(product.get("asin", "")))}</div>
      <h2 data-testid="product-title">{html.escape(str(product.get("title", "")))}</h2>
      <div data-testid="product-brand">{html.escape(str(product.get("brand", "")))}</div>
      <div data-testid="product-price">{product.get("price")}</div>
      <a class="btn btn-primary" data-testid="add-to-cart" href="/ui/cart/add?sid={sid}&asin={html.escape(asin)}&next=/ui/product/{html.escape(asin)}?sid={sid}&edge={edge}&q={html.escape(q)}&sort={sort}&brand={html.escape(brand)}&category={html.escape(category)}">Add To Cart</a>
      <a class="btn" data-testid="back-to-results" href="/ui/search?sid={sid}&q={html.escape(q)}&sort={sort}&brand={html.escape(brand)}&category={html.escape(category)}">Back To Results</a>
      <a class="btn" data-testid="nav-cart" href="/ui/cart?sid={sid}">Cart</a>
      <h4>Related ({html.escape(edge)})</h4>
      <div data-testid="related-list">{related_html or '<span class="muted">None</span>'}</div>
    </main>
    """
    return HTMLResponse(_base_html("PRODUCT_DETAIL", sid, cart, body))


@router.get("/ui/cart/add")
def ui_cart_add(sid: str, asin: str, next: str = "/ui"):
    cart = _cart_for(sid)
    cart.append(asin)
    return RedirectResponse(next)


@router.get("/ui/cart", response_class=HTMLResponse)
def ui_cart(sid: str = Query(...)):
    cart = _cart_for(sid)
    db = get_db()
    docs = list(db["products"].find({"asin": {"$in": cart}}, {"_id": 0, "asin": 1, "title": 1, "price": 1}))
    rows = "".join(
        f'<div class="card" data-testid="cart-item" data-asin="{html.escape(d["asin"])}"><strong>{html.escape(d["title"][:80])}</strong><div>${d.get("price")}</div></div>'
        for d in docs
    )
    body = f"""
    <main data-testid="view-cart">
      <a class="btn" href="/ui?sid={sid}">Home</a>
      <div data-testid="cart-items">{rows or '<span class="muted">Empty cart</span>'}</div>
      <div data-testid="cart-subtotal">0.0</div>
    </main>
    """
    return HTMLResponse(_base_html("CART", sid, cart, body))


@router.get("/ui/replay", response_class=HTMLResponse)
def ui_replay(file: str = Query(default="experiments/reports/last_run.json"), idx: int = Query(default=0)):
    path = Path(file)
    if not path.exists():
        return HTMLResponse(f"<h3>Replay file not found: {html.escape(file)}</h3>", status_code=404)
    episodes = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(episodes, list) or not episodes:
        return HTMLResponse("<h3>Replay file has no episodes</h3>", status_code=400)
    idx = max(0, min(idx, len(episodes) - 1))
    ep = episodes[idx]
    steps = ep.get("steps", [])
    steps_json = json.dumps(steps)
    body = f"""
    <main>
      <h2>Episode Replay</h2>
      <div class="muted">file: {html.escape(file)} | episode {idx+1}/{len(episodes)} | task {html.escape(str(ep.get("task_id")))}</div>
      <div>
        <a class="btn" href="/ui/replay?file={html.escape(file)}&idx={max(0, idx-1)}">Prev Episode</a>
        <a class="btn" href="/ui/replay?file={html.escape(file)}&idx={min(len(episodes)-1, idx+1)}">Next Episode</a>
      </div>
      <div style="margin-top:12px;">
        <input id="stepRange" type="range" min="0" max="{max(0, len(steps)-1)}" value="0" style="width:100%;" />
      </div>
      <div id="meta" class="muted"></div>
      <img id="shot" src="" style="max-width:100%; border:1px solid #cbd5e1; border-radius:8px; margin-top:8px;" />
      <pre id="stepJson" style="white-space:pre-wrap;background:#0b1020;color:#dbeafe;padding:8px;border-radius:8px;"></pre>
    </main>
    <script>
      const steps = {steps_json};
      const range = document.getElementById('stepRange');
      const shot = document.getElementById('shot');
      const meta = document.getElementById('meta');
      const stepJson = document.getElementById('stepJson');
      function render(i) {{
        const s = steps[i] || {{}};
        const p = s.screenshot_path || "";
        shot.src = p ? '/artifacts/' + p : '';
        meta.innerText = `step ${{i}} | view=${{s.view_pred}} | action=${{(s.action||{{}}).type||'NA'}} | done=${{s.oracle_done}}`;
        stepJson.textContent = JSON.stringify(s, null, 2);
      }}
      range.addEventListener('input', () => render(parseInt(range.value, 10)));
      render(0);
    </script>
    """
    return HTMLResponse(_base_html("HOME", "replay", [], body))
