from __future__ import annotations

from typing import Iterable


def _chunked(items: Iterable[dict], size: int) -> Iterable[list[dict]]:
    batch: list[dict] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def ensure_indexes(collection) -> None:
    collection.create_index("asin", unique=True, name="asin_unique")
    collection.create_index("brand", name="brand_idx")
    collection.create_index("category_leaf", name="category_leaf_idx")
    collection.create_index("price", name="price_idx")
    collection.create_index("rating_avg", name="rating_avg_idx")
    collection.create_index("rating_count", name="rating_count_idx")


def load_products(
    products: Iterable[dict],
    mongo_uri: str,
    db_name: str = "simazon",
    collection_name: str = "products",
    batch_size: int = 1000,
) -> int:
    try:
        from pymongo import MongoClient, UpdateOne
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "pymongo is required for MongoDB ingest. Install with `pip install pymongo`."
        ) from exc

    client = MongoClient(mongo_uri)
    try:
        collection = client[db_name][collection_name]
        ensure_indexes(collection)

        written = 0
        for batch in _chunked(products, batch_size):
            ops = [
                UpdateOne(
                    {"asin": product["asin"]},
                    {"$set": product},
                    upsert=True,
                )
                for product in batch
            ]
            if not ops:
                continue
            collection.bulk_write(ops, ordered=False)
            written += len(ops)
        return written
    finally:
        client.close()
