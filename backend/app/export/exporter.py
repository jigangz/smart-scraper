import csv
import json
import os
from typing import Optional

EXPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "exports")


def _ensure_export_dir():
    os.makedirs(EXPORT_DIR, exist_ok=True)


def export_csv(results: list[dict], filename: str) -> str:
    """Export results to a CSV file. Returns the filepath."""
    _ensure_export_dir()

    if not filename.endswith(".csv"):
        filename += ".csv"

    filepath = os.path.join(EXPORT_DIR, filename)

    if not results:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            f.write("")
        return filepath

    # Collect all unique keys across all result dicts
    all_keys: list[str] = []
    seen_keys: set[str] = set()
    for row in results:
        if isinstance(row, dict):
            for key in row.keys():
                if key not in seen_keys:
                    all_keys.append(key)
                    seen_keys.add(key)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        for row in results:
            if isinstance(row, dict):
                writer.writerow(row)

    return filepath


def export_json(results: list[dict], filename: str) -> str:
    """Export results to a JSON file with pretty printing. Returns the filepath."""
    _ensure_export_dir()

    if not filename.endswith(".json"):
        filename += ".json"

    filepath = os.path.join(EXPORT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    return filepath
