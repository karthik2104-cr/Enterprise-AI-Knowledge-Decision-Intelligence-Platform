"""Replay evaluation dataset against a running API (optional)."""

import json
from pathlib import Path

DATASET = Path(__file__).resolve().parents[1] / "dataset" / "golden_set.json"


def main() -> None:
    items = json.loads(DATASET.read_text(encoding="utf-8"))
    print(f"Loaded {len(items)} evaluation questions. Use POST /api/evaluation/run from the app.")


if __name__ == "__main__":
    main()
