"""Renders a markdown summary of the filament entries a PR would add.

It reuses the real expansion logic from compile_filaments, so the list shown to
the author is exactly what would end up in the database. Grouping the entries by
weight, spool type and diameter is deliberate: a combination the manufacturer
does not actually sell is obvious when it appears as its own heading.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from compile_filaments import get_filaments_from_data  # noqa: E402

COMMENT_LIMIT = 60000


def load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def entries(data: dict | None) -> list[dict]:
    if not data:
        return []
    try:
        return list(get_filaments_from_data(data))
    except (KeyError, ValueError):
        return []


def describe_spool(entry: dict) -> str:
    parts = [f"{entry['diameter']} mm", f"{entry['weight']:g} g"]
    spool = entry.get("spool_type")
    tare = entry.get("spool_weight")
    if spool and tare:
        parts.append(f"{spool} spool ({tare:g} g tare)")
    elif spool:
        parts.append(f"{spool} spool")
    elif tare:
        parts.append(f"spool {tare:g} g tare")
    else:
        parts.append("spool type not set")
    return " · ".join(parts)


def render(new_entries: list[dict]) -> str:
    if not new_entries:
        return (
            "## Catalog preview\n\n"
            "This PR doesn't add any new filament entries. It may still be "
            "correcting existing ones, which this comment doesn't cover.\n"
        )

    total = len(new_entries)
    out = [
        "## Catalog preview",
        "",
        f"This PR would add **{total} entr{'y' if total == 1 else 'ies'}** to Spoolman, "
        "listed below as they will appear to users.",
        "",
        "**Please check this against the manufacturer's product catalog.** Every "
        "combination of weight, diameter and colour is generated automatically, so "
        "a spool size or diameter that only exists for some colours will show up "
        "here as products that aren't really sold. If you see any, split the "
        "filament into separate objects so only real combinations are produced.",
        "",
    ]

    new_entries.sort(key=lambda e: (e["manufacturer"], e["material"], e["name"]))
    bullets = [
        f"- {e['manufacturer']} - {e['material']} {e['name']} · {describe_spool(e)}"
        for e in new_entries
    ]

    # Keep as many entries as fit, and be explicit about any that don't.
    header = "\n".join(out)
    budget = COMMENT_LIMIT - len(header) - 200
    kept = []
    for bullet in bullets:
        budget -= len(bullet) + 1
        if budget < 0:
            break
        kept.append(bullet)

    text = header + "\n".join(kept) + "\n"
    dropped = len(bullets) - len(kept)
    if dropped:
        text += (
            f"\n*Showing {len(kept)} of {len(bullets)} entries. The remaining "
            f"{dropped} don't fit in a single comment.*\n"
        )
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*", help="changed filament json files")
    parser.add_argument("--base-dir", help="directory holding the base versions")
    parser.add_argument("--out", default="preview.md")
    args = parser.parse_args()

    new_entries = []
    for name in args.files:
        path = Path(name)
        if path.parent.name != "filaments" or path.suffix != ".json":
            continue

        head = load(path)
        if head is None:
            continue

        base_ids = set()
        if args.base_dir:
            base = load(Path(args.base_dir) / path.name)
            base_ids = {e["id"] for e in entries(base)}

        for data_filament in head.get("filaments", []):
            single = {"manufacturer": head["manufacturer"], "filaments": [data_filament]}
            for e in entries(single):
                if e["id"] in base_ids:
                    continue
                new_entries.append(e)

    Path(args.out).write_text(render(new_entries), encoding="utf-8")
    print(f"wrote {args.out} ({len(new_entries)} new entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
