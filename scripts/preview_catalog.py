"""Renders a markdown summary of the filament entries a PR would add.

It reuses the real expansion logic from compile_filaments, so the list shown to
the author is exactly what would end up in the database. Grouping the entries by
weight, spool type and diameter is deliberate: a combination the manufacturer
does not actually sell is obvious when it appears as its own heading.

It also flags filaments that look like ones already in the catalog. The build
already rejects two entries with the same generated id, but the id keeps
punctuation, so "PLA Basic - Black" and "PLA Basic Black" sail past it as two
distinct products.

Matching works on the source fields rather than the compiled name, comparing
the product line and the colour separately within one manufacturer, material
and weight. That separation matters: in a compiled name the product line
dominates the string, so "PolyLite PETG White" and "PolyLite PETG Lime" come
out 85% similar while being different products, and a typo in a colour on a
long product line is invisible. Held apart, each field is compared only on the
words that actually differ.
"""

import argparse
import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from compile_filaments import get_filaments_from_data  # noqa: E402

COMMENT_LIMIT = 60000
PLACEHOLDER = "{color_name}"

# How alike two words must be to read as the same word misspelled. Tuned
# against the whole catalog: 0.85 flags only genuine candidates, while 0.80
# starts matching "Neonorange" with "Reinorange", which are different colours.
TYPO_RATIO = 0.85


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


def squash(text) -> str:
    """Drops separators and case, but keeps '+' so PLA+ stays distinct from PLA."""
    return re.sub(r"[^a-z0-9+]", "", str(text).lower())


def tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9+]+", str(name).lower()) if t]


def norm(name: str) -> str:
    """A name reduced to its words, so order, case and punctuation stop mattering."""
    return " ".join(sorted(tokens(name)))


def records(data: dict | None):
    """The (line, colour) pairs a source file declares, one per weight.

    Works on the source fields rather than the compiled entry, so the product
    line and the colour can be compared separately.
    """
    if not data:
        return
    for filament in data.get("filaments", []):
        try:
            line = filament["name"].replace(PLACEHOLDER, " ").strip()
            for weight in filament["weights"]:
                for color in filament["colors"]:
                    yield {
                        "manufacturer": data["manufacturer"],
                        "material": filament["material"],
                        "weight": float(weight["weight"]),
                        "line": line,
                        "color": color["name"],
                    }
        except (KeyError, TypeError, ValueError):
            continue  # schema validation reports malformed filaments


def bucket_key(rec: dict) -> tuple:
    """What must match exactly before two filaments are worth comparing."""
    return (squash(rec["manufacturer"]), squash(rec["material"]), f"{rec['weight']:.0f}")


def dup_key(rec: dict) -> tuple:
    """Identifies a filament ignoring punctuation, case and word order.

    The generated id keeps all three, so "PLA Basic - Black", "PLA Basic Black"
    and "Black PLA Basic" are three ids for one product.
    """
    return bucket_key(rec) + (norm(rec["line"]), norm(rec["color"]))


def looks_misspelled(a: str, b: str) -> bool:
    """True when two words differ only in their letters.

    Digits and '+' separate real products - TPU90 from TPU95, 85A from 98A,
    Silk from Silk+ - so a difference there is never a typo. Letters are where
    misspellings and spelling variants actually live.
    """
    if re.sub(r"[^0-9+]", "", a) != re.sub(r"[^0-9+]", "", b):
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= TYPO_RATIO


def compare_field(a: str, b: str):
    """None if the two names are the same, the differing pair if one word apart.

    Returns False when they are properly different. Only a substituted word
    counts: an extra word is usually a real variant ("Blue" vs "Sky Blue").
    """
    ta, tb = tokens(a), tokens(b)
    if sorted(ta) == sorted(tb):
        return None

    da, db = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ta, tb).get_opcodes():
        if tag != "equal":
            da += ta[i1:i2]
            db += tb[j1:j2]

    if len(da) == 1 and len(db) == 1 and looks_misspelled(da[0], db[0]):
        return (db[0], da[0])
    return False


def fuzzy_match(rec: dict, siblings: list[dict]):
    """Finds a sibling differing by a single misspelled word in one field.

    A difference in both the product line and the colour is two differences,
    which is a different product rather than a duplicate.
    """
    for other in siblings:
        line = compare_field(rec["line"], other["line"])
        color = compare_field(rec["color"], other["color"])
        if line is False or color is False:
            continue
        if (line is None) == (color is None):
            continue  # identical (caught exactly) or different in both fields
        return other, ("product line" if color is None else "colour"), (line or color)
    return None


def verbatim(rec: dict) -> tuple:
    """The record exactly as written, used to ignore filaments a PR didn't touch."""
    return (rec["manufacturer"], rec["material"], rec["weight"], rec["line"], rec["color"])


def removed_by(files: list[tuple[Path, dict]], base_dir: str | None) -> set:
    """The filaments a PR takes out of the files it touches.

    A PR that corrects a name removes the old spelling and adds the new one.
    Matching the new spelling against the old one it just deleted would report
    every such fix as a duplicate of the thing it repairs.
    """
    gone = set()
    for path, head in files:
        base = load(Path(base_dir) / path.name) if base_dir else None
        kept = {verbatim(rec) for rec in records(head)}
        gone |= {verbatim(rec) for rec in records(base) if verbatim(rec) not in kept}
    return gone


def base_index(base_dir: str | None, removed: set) -> tuple[set, set, dict, dict]:
    """Reads the catalog as it stands on the base branch, minus what the PR drops."""
    ids, unchanged, by_name, buckets = set(), set(), {}, defaultdict(list)
    for path in sorted(Path(base_dir).glob("*.json")) if base_dir else []:
        data = load(path)
        ids.update(e["id"] for e in entries(data))
        for rec in records(data):
            if verbatim(rec) in unchanged or verbatim(rec) in removed:
                continue  # already seen for another diameter, or this PR removes it
            unchanged.add(verbatim(rec))
            by_name.setdefault(dup_key(rec), rec)
            buckets[bucket_key(rec)].append(rec)
    return ids, unchanged, by_name, buckets


def describe(rec: dict) -> str:
    parts = [rec["manufacturer"], rec["material"]]
    if rec["line"]:
        parts.append(rec["line"])
    return f"{' '.join(parts)} - {rec['color']}"


def render_dupes(dupes: list[dict]) -> list[str]:
    """A GitHub alert block, so the warning is impossible to scroll past.

    The wording has to carry two things at once: this probably wants fixing,
    and it is a heuristic that can be wrong. Leaving either out means authors
    either ignore it or "fix" genuinely distinct products into one.
    """
    if not dupes:
        return []

    plural = "" if len(dupes) == 1 else "s"
    out = [
        "> [!WARNING]",
        f"> ## :rotating_light: {len(dupes)} possible duplicate{plural} - "
        "this probably needs fixing",
        ">",
        f"> {'This' if len(dupes) == 1 else 'These'} look{'s' if len(dupes) == 1 else ''} "
        "like filament the catalog already has. Nothing will fail the build: the "
        "unique-id check does not catch near-duplicates, which is exactly why a "
        "duplicate this close can get merged and is then painful to take back out.",
        ">",
        "> **It may also be a false positive.** Manufacturers really do sell "
        "products that differ by a single word or a stray letter. If you have "
        "checked the manufacturer's catalog and these are genuinely different "
        "products, nothing needs changing - just say so in the PR so a "
        "maintainer doesn't have to check it again.",
        ">",
    ]

    for d in dupes[:40]:
        weights = ", ".join(f"{w:g} g" for w in sorted(d["weights"]))
        if d["words"] is None:
            why = "same name, written differently"
        else:
            why = (f"{d['field']} differs by one word: "
                   f"**{d['words'][0]}** vs **{d['words'][1]}**")
        out.append(
            f"> - **{describe(d['new'])}** looks like **{describe(d['old'])}** "
            f"({why}) - {weights}, {d['origin']}"
        )
    if len(dupes) > 40:
        out.append(f"> - *...and {len(dupes) - 40} more*")
    out.append("")
    return out


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


def render(new_entries: list[dict], dupes: list[dict]) -> str:
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
        *render_dupes(dupes),
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

    changed = []
    for name in args.files:
        path = Path(name)
        if path.parent.name != "filaments" or path.suffix != ".json":
            continue
        head = load(path)
        if head is not None:
            changed.append((path, head))

    base_ids, unchanged, by_name, buckets = base_index(
        args.base_dir, removed_by(changed, args.base_dir)
    )

    new_entries = []
    findings = {}
    seen = set()
    for path, head in changed:
        for data_filament in head.get("filaments", []):
            single = {"manufacturer": head["manufacturer"], "filaments": [data_filament]}
            new_entries += [e for e in entries(single) if e["id"] not in base_ids]

        for rec in records(head):
            if verbatim(rec) in unchanged or verbatim(rec) in seen:
                # Already in the catalog untouched, or the same product listed
                # again for another diameter or spool type. Neither is ours.
                continue
            seen.add(verbatim(rec))

            match = by_name.get(dup_key(rec))
            field, words = None, None
            if match is None:
                near = fuzzy_match(rec, buckets[bucket_key(rec)])
                if near is not None:
                    match, field, words = near

            if match is None:
                # Indexed so that two new filaments can collide with each other.
                by_name.setdefault(dup_key(rec), rec)
                buckets[bucket_key(rec)].append(rec)
                continue

            # One product sold in several weights is one finding, not several.
            key = (verbatim(rec)[:2], rec["line"], rec["color"],
                   match["line"], match["color"], field, words)
            if key in findings:
                findings[key]["weights"].add(rec["weight"])
                continue
            findings[key] = {
                "new": rec,
                "old": match,
                "field": field,
                "words": words,
                "weights": {rec["weight"]},
                "origin": (
                    "which is already in the catalog"
                    if verbatim(match) in unchanged
                    else "which this PR also adds"
                ),
            }

    dupes = list(findings.values())
    Path(args.out).write_text(render(new_entries, dupes), encoding="utf-8")
    print(f"wrote {args.out} ({len(new_entries)} new entries, {len(dupes)} possible duplicates)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
