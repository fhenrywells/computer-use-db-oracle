import argparse

from ingest.snap_amazon.load_mongo import load_products
from ingest.snap_amazon.normalize import normalize_record
from ingest.snap_amazon.parse import parse_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Amazon Reviews 2023 item metadata into MongoDB.")
    parser.add_argument("--input", nargs="+", required=True, help="One or more .jsonl files, dirs, or globs.")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db", default="simazon")
    parser.add_argument("--collection", default="products")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    total = 0
    normalized = 0

    def iter_docs():
        nonlocal total, normalized
        for raw, source_file in parse_records(args.input, limit=args.limit):
            total += 1
            doc = normalize_record(raw, source_file)
            if doc is None:
                continue
            normalized += 1
            yield doc

    if args.dry_run:
        sample = []
        for idx, doc in enumerate(iter_docs()):
            if idx < 3:
                sample.append(doc)
        print(f"dry_run total_raw={total} normalized={normalized}")
        for i, item in enumerate(sample, start=1):
            print(f"sample_{i} asin={item['asin']} title={item['title'][:80]!r} price={item.get('price')}")
        return

    written = load_products(
        iter_docs(),
        mongo_uri=args.mongo_uri,
        db_name=args.db,
        collection_name=args.collection,
        batch_size=args.batch_size,
    )
    print(f"ingest_complete total_raw={total} normalized={normalized} written={written}")


if __name__ == "__main__":
    main()
