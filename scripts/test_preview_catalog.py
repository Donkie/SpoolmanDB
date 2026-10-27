"""Self-check for the duplicate detection in preview_catalog.

Run with: python3 scripts/test_preview_catalog.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from preview_catalog import compare_field, dup_key, looks_misspelled, main  # noqa: E402


def filament(name, colors, material="PLA", diameters=(1.75,)):
    return {
        "name": name,
        "material": material,
        "density": 1.24,
        "diameters": list(diameters),
        "weights": [{"weight": 1000}],
        "colors": [{"name": c, "hex": h} for c, h in colors],
    }


EXISTING = {
    "manufacturer": "Acme",
    "filaments": [filament("Shiny {color_name}", [("Black", "1a1a1a")])],
}

CHANGED = {
    "manufacturer": "Acme",
    "filaments": [
        # The original, left exactly as it was.
        filament("Shiny {color_name}", [("Black", "1a1a1a")]),
        # The same product again, punctuated the way someone else would write it.
        filament("Shiny - {color_name}", [("Black", "1a1a1a")]),
        # A colour typo on the same product line.
        filament("Shiny {color_name}", [("Blck", "1a1a1a")]),
        # A genuinely different colour, which must not be flagged.
        filament("Shiny {color_name}", [("Red", "c01f1f")]),
        # A different product line, which must not be flagged either.
        filament("Matte {color_name}", [("Black", "1a1a1a")]),
        # The same product split across diameters, as several manufacturers do.
        # Diameter is not part of the bucket, so these must not match each other.
        filament("Thick {color_name}", [("Green", "2a7a2a")], diameters=[1.75]),
        filament("Thick {color_name}", [("Green", "2a7a2a")], diameters=[2.85]),
    ],
}


def rec(line, color, material="PLA", weight=1000.0):
    return {"manufacturer": "Acme", "material": material, "weight": weight,
            "line": line, "color": color}


def test_dup_key():
    a = rec("Shiny", "Black")
    assert dup_key(a) == dup_key(rec("shiny", "black")), "case must not matter"
    assert dup_key(a) == dup_key(rec("- Shiny -", "Black")), "punctuation must not matter"
    assert dup_key(a) == dup_key(rec("Shiny", "Black ")), "whitespace must not matter"
    assert dup_key(a) != dup_key(rec("Shiny", "Red")), "a real colour change must show"
    assert dup_key(a) != dup_key(rec("Matte", "Black")), "a real line change must show"
    assert dup_key(a) != dup_key(rec("Shiny", "Black", weight=250)), "weight is in the key"
    assert dup_key(a) != dup_key(rec("Shiny", "Black", material="PLA+")), "PLA+ is not PLA"


def test_looks_misspelled():
    assert looks_misspelled("gray", "cgray"), "a stray letter is a typo"
    assert looks_misspelled("pla", "epla")
    assert looks_misspelled("transparent", "tansparent")

    # Every one of these was a false positive found in the real catalog.
    assert not looks_misspelled("tpu90", "tpu95"), "shore hardness is a real product"
    assert not looks_misspelled("85a", "98a")
    assert not looks_misspelled("silk", "silk+"), "Silk+ is a real product line"
    assert not looks_misspelled("white", "lime"), "different colours are not typos"
    assert not looks_misspelled("green", "grey")
    assert not looks_misspelled("neonorange", "reinorange"), "0.80 alike, still distinct"


def test_compare_field():
    assert compare_field("Sky Blue", "blue sky") is None, "word order is the same name"
    # Called as (new, existing), it reports (existing word, new word).
    assert compare_field("Blck", "Black") == ("black", "blck")
    assert compare_field("Blue", "Sky Blue") is False, "an extra word is a real variant"
    # The whole-string approach scored these 85% alike; per-word they are distinct.
    assert compare_field("Transparent Red", "Transparent Orange") is False
    assert compare_field("PolyLite PETG White", "PolyLite PETG Lime") is False


def run(tmp: Path) -> str:
    base = tmp / "base"
    base.mkdir()
    (base / "acme.json").write_text(json.dumps(EXISTING))

    head = tmp / "filaments"
    head.mkdir()
    (head / "acme.json").write_text(json.dumps(CHANGED))

    out = tmp / "preview.md"
    sys.argv = ["x", str(head / "acme.json"), "--base-dir", str(base), "--out", str(out)]
    assert main() == 0
    return out.read_text()


def test_rename_is_not_a_duplicate():
    """A PR fixing a name must not be told it duplicates the name it fixes."""
    base = {"manufacturer": "Acme",
            "filaments": [filament("{color_name}", [("Jet Black ", "1a1a1a")])]}
    # The trailing space is gone, which is a correction, not a new product.
    head = {"manufacturer": "Acme",
            "filaments": [filament("{color_name}", [("Jet Black", "1a1a1a")])]}

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "base").mkdir()
        (tmp / "base" / "acme.json").write_text(json.dumps(base))
        (tmp / "filaments").mkdir()
        (tmp / "filaments" / "acme.json").write_text(json.dumps(head))
        out = tmp / "preview.md"
        sys.argv = ["x", str(tmp / "filaments" / "acme.json"),
                    "--base-dir", str(tmp / "base"), "--out", str(out)]
        assert main() == 0
        text = out.read_text()

    assert "possible duplicate" not in text, text


def test_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        text = run(Path(d))

    assert "2 possible duplicates" in text, text
    assert "[!WARNING]" in text, "the notice must be a GitHub alert"
    assert "probably needs fixing" in text
    assert "may also be a false positive" in text
    assert "same name, written differently" in text, text
    assert "colour differs by one word: **black** vs **blck**" in text, text
    assert "already in the catalog" in text, text

    # The real colour and the real product line must not be flagged.
    flagged = [line for line in text.splitlines() if "looks like" in line]
    assert len(flagged) == 2, flagged
    assert not any("Red" in line for line in flagged), "a new colour is not a duplicate"
    assert not any("Matte" in line for line in flagged), "a new line is not a duplicate"
    assert not any("Thick" in line for line in flagged), \
        "one product split across diameters is not a duplicate of itself"
    assert "Acme - PLA Matte Black" in text, "but both must still be previewed"
    assert "Acme - PLA Shiny Red" in text


def test():
    test_dup_key()
    test_looks_misspelled()
    test_compare_field()
    test_rename_is_not_a_duplicate()
    test_end_to_end()
    print("ok")


if __name__ == "__main__":
    test()
