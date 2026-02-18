from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient


@dataclass
class SimazonState:
    view_id: str = "HOME"
    search_query: str = ""
    constraints: dict[str, Any] = field(default_factory=dict)
    sort_key: str = "relevance"
    results: list[dict[str, Any]] = field(default_factory=list)
    selected_asin: str | None = None
    related_edge: str = "also_bought"
    related_asins: list[str] = field(default_factory=list)
    cart_asins: list[str] = field(default_factory=list)


class SimazonEnv:
    def __init__(self, mongo_uri: str, db: str = "simazon", collection: str = "products") -> None:
        self.client = MongoClient(mongo_uri)
        self.col = self.client[db][collection]
        self.state = SimazonState()

    def close(self) -> None:
        self.client.close()

    def _load_product(self, asin: str) -> dict[str, Any] | None:
        return self.col.find_one(
            {"asin": asin},
            {
                "_id": 0,
                "asin": 1,
                "title": 1,
                "brand": 1,
                "price": 1,
                "rating_avg": 1,
                "rating_count": 1,
                "category_leaf": 1,
                "related": 1,
            },
        )

    def _related_asins_for(self, product: dict[str, Any] | None, edge: str) -> list[str]:
        if not product:
            return []
        related = product.get("related") if isinstance(product.get("related"), dict) else {}
        edge_values = related.get(edge)
        if isinstance(edge_values, str):
            asins = [edge_values]
        elif isinstance(edge_values, list):
            asins = [str(x) for x in edge_values if str(x).strip()]
        else:
            asins = []
        if asins:
            existing = self.col.find({"asin": {"$in": asins}}, {"_id": 0, "asin": 1})
            aset = {row["asin"] for row in existing}
            return [a for a in asins if a in aset]

        # Fallback neighborhood for categories where explicit related links are sparse.
        brand = product.get("brand")
        category = product.get("category_leaf")
        asin = product.get("asin")
        if brand:
            docs = self.col.find({"asin": {"$ne": asin}, "brand": brand}, {"_id": 0, "asin": 1}).limit(10)
            found = [d["asin"] for d in docs]
            if found:
                return found
        if category:
            docs = self.col.find({"asin": {"$ne": asin}, "category_leaf": category}, {"_id": 0, "asin": 1}).limit(10)
            found = [d["asin"] for d in docs]
            if found:
                return found
        return []

    def _set_product_view(self, asin: str, edge: str | None = None) -> bool:
        product = self._load_product(asin)
        if not product:
            return False
        if edge:
            self.state.related_edge = edge
        self.state.selected_asin = asin
        self.state.related_asins = self._related_asins_for(product, self.state.related_edge)
        self.state.view_id = "PRODUCT_DETAIL"
        return True

    def reset(self, start_asin: str | None = None, related_edge: str | None = None) -> dict[str, Any]:
        self.state = SimazonState()
        if related_edge:
            self.state.related_edge = related_edge
        if start_asin:
            self._set_product_view(start_asin, related_edge)
        return self._observation()

    def _query_filter(self, query: str, constraints: dict[str, Any]) -> dict[str, Any]:
        parts: list[dict[str, Any]] = []
        tokens = [t for t in re.split(r"\s+", query.strip()) if t]
        for token in tokens:
            rx = {"$regex": re.escape(token), "$options": "i"}
            parts.append({"$or": [{"title": rx}, {"brand": rx}, {"category_leaf": rx}]})

        brand = constraints.get("brand")
        if brand:
            parts.append({"brand": brand})
        category_leaf = constraints.get("category_leaf")
        if category_leaf:
            parts.append({"category_leaf": category_leaf})
        price_lte = constraints.get("price_lte")
        if isinstance(price_lte, (int, float)):
            parts.append({"price": {"$type": "number", "$lte": float(price_lte)}})
        rating_gte = constraints.get("rating_gte")
        if isinstance(rating_gte, (int, float)):
            parts.append({"rating_avg": {"$type": "number", "$gte": float(rating_gte)}})
        rating_count_gte = constraints.get("rating_count_gte")
        if isinstance(rating_count_gte, int):
            parts.append({"rating_count": {"$type": "number", "$gte": rating_count_gte}})

        price_bucket = constraints.get("price_bucket")
        if price_bucket == "under_25":
            parts.append({"price": {"$type": "number", "$lt": 25}})

        return {"$and": parts} if parts else {}

    def search(self, query: str, constraints: dict[str, Any], sort_key: str, limit: int = 50) -> list[dict[str, Any]]:
        filt = self._query_filter(query, constraints)
        cursor = self.col.find(
            filt,
            {
                "_id": 0,
                "asin": 1,
                "title": 1,
                "brand": 1,
                "price": 1,
                "rating_avg": 1,
                "rating_count": 1,
                "category_leaf": 1,
            },
        )
        if sort_key == "price_asc":
            cursor = cursor.sort([("price", ASCENDING), ("asin", ASCENDING)])
        elif sort_key == "price_desc":
            cursor = cursor.sort([("price", DESCENDING), ("asin", ASCENDING)])
        elif sort_key == "rating_desc":
            cursor = cursor.sort([("rating_avg", DESCENDING), ("rating_count", DESCENDING), ("asin", ASCENDING)])
        else:
            cursor = cursor.sort([("rating_count", DESCENDING), ("asin", ASCENDING)])
        return list(cursor.limit(limit))

    def step(self, action: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        kind = action.get("type", "NoOp")
        args = action.get("args", {})
        info = {"postcondition_ok": True, "event": None}

        if kind == "Search":
            self.state.search_query = str(args.get("query", "")).strip()
            self.state.results = self.search(self.state.search_query, self.state.constraints, self.state.sort_key)
            self.state.view_id = "SEARCH_RESULTS" if self.state.results else "EMPTY_RESULTS"
            info["event"] = "Searched"
        elif kind == "ApplyFacet":
            facet = str(args.get("facet", ""))
            value = args.get("value")
            if facet and value is not None:
                self.state.constraints[facet] = value
                self.state.results = self.search(self.state.search_query, self.state.constraints, self.state.sort_key)
                self.state.view_id = "SEARCH_RESULTS" if self.state.results else "EMPTY_RESULTS"
                info["event"] = "FacetApplied"
            else:
                info["postcondition_ok"] = False
        elif kind == "SortBy":
            self.state.sort_key = str(args.get("key", "relevance"))
            self.state.results = self.search(self.state.search_query, self.state.constraints, self.state.sort_key)
            self.state.view_id = "SEARCH_RESULTS" if self.state.results else "EMPTY_RESULTS"
            info["event"] = "SortChanged"
        elif kind == "OpenResult":
            rank = int(args.get("rank", 1))
            idx = rank - 1
            if 0 <= idx < len(self.state.results):
                chosen_asin = self.state.results[idx]["asin"]
                ok = self._set_product_view(chosen_asin)
                info["event"] = "OpenedProduct"
                info["postcondition_ok"] = ok
            else:
                info["postcondition_ok"] = False
        elif kind == "OpenRelated":
            rank = int(args.get("rank", 1))
            idx = rank - 1
            if 0 <= idx < len(self.state.related_asins):
                chosen_asin = self.state.related_asins[idx]
                ok = self._set_product_view(chosen_asin)
                info["event"] = "OpenedRelated"
                info["postcondition_ok"] = ok
            else:
                info["postcondition_ok"] = False
        elif kind == "AddToCart":
            if self.state.selected_asin:
                self.state.cart_asins.append(self.state.selected_asin)
                info["event"] = "AddedToCart"
            else:
                info["postcondition_ok"] = False
        elif kind == "GoToCart":
            self.state.view_id = "CART"
            info["event"] = "GoToCart"
        elif kind == "BackToResults":
            self.state.view_id = "SEARCH_RESULTS" if self.state.results else "EMPTY_RESULTS"
            info["event"] = "BackToResults"
        elif kind == "NoOp":
            info["event"] = "NoOp"
        else:
            info["postcondition_ok"] = False
            info["event"] = "UnknownAction"

        return self._observation(), info

    def _observation(self) -> dict[str, Any]:
        return {
            "view_id": self.state.view_id,
            "search_query": self.state.search_query,
            "applied_constraints": dict(self.state.constraints),
            "sort_key": self.state.sort_key,
            "result_asins": [r["asin"] for r in self.state.results],
            "result_count": len(self.state.results),
            "selected_asin": self.state.selected_asin,
            "related_asins": list(self.state.related_asins),
            "related_edge": self.state.related_edge,
            "cart_asins": list(self.state.cart_asins),
        }

    def compute_oracle_target_asin(self, task: dict[str, Any]) -> str | None:
        oracle = task.get("oracle", {})
        spec = task.get("spec", {})
        otype = oracle.get("type")
        if otype == "exact_asin_in_cart":
            expected = oracle.get("expected_asin")
            return str(expected) if expected else None

        query = str(spec.get("query", "")).strip()
        constraints = spec.get("constraints", {}) if isinstance(spec.get("constraints"), dict) else {}
        if otype == "min_price_match":
            docs = self.search(query, constraints, "price_asc", limit=1)
            return docs[0]["asin"] if docs else None
        if otype == "max_rating_match":
            docs = self.search(query, constraints, "rating_desc", limit=1)
            return docs[0]["asin"] if docs else None
        if otype == "related_edge_match":
            expected = oracle.get("expected_asin")
            return str(expected) if expected else None
        return None
