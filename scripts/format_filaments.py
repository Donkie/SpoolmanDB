"""Format filament JSON files with the Python standard library."""

import argparse
import json
from pathlib import Path

FILAMENTS_DIR = Path("filaments")


def format_json(source: str) -> str:
    """Return JSON with preserved key order, four-space indentation, and LF endings."""
    data = json.loads(source)
    return json.dumps(data, ensure_ascii=False, indent=4)


def format_file(path: Path, check: bool) -> bool:
    source = path.read_bytes().decode("utf-8")
    formatted = format_json(source)
    if source == formatted:
        return True
    if check:
        return False
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(formatted)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report files that need formatting without changing them",
    )
    parser.add_argument("files", nargs="*", type=Path, help="filament JSON files")
    args = parser.parse_args()

    paths = args.files or sorted(FILAMENTS_DIR.glob("*.json"))
    if not paths:
        parser.error("no filament JSON files found")

    failed = []
    for path in paths:
        if not format_file(path, args.check):
            failed.append(path)

    if failed:
        for path in failed:
            print(f"{path}: not formatted")
        print("Run python3 scripts/format_filaments.py to format these files.")
    return failed and 1 or 0


if __name__ == "__main__":
    raise SystemExit(main())