import argparse
import json
from pathlib import Path

from agentlab.eval.materialize_tasks import materialize_task


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates", required=True)
    parser.add_argument("--products", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    templates = json.loads(Path(args.templates).read_text(encoding="utf-8"))
    products = json.loads(Path(args.products).read_text(encoding="utf-8"))
    materialized = [
      materialize_task(t, products, seed=args.seed + i)
      for i, t in enumerate(templates)
    ]
    Path(args.out).write_text(json.dumps(materialized, indent=2), encoding="utf-8")
    print(f"wrote {len(materialized)} tasks to {args.out}")


if __name__ == "__main__":
    main()

