"""Self-check for single-color names. Requires check-jsonschema on PATH.

Run with: python3 scripts/test_filament_names.py
"""

import json
import subprocess
import tempfile
from pathlib import Path

from compile_filaments import get_filaments_from_data
from lint_filaments import allowed_keys, lint_file


def test():
    schema = Path("filaments.schema.json")
    keysets = allowed_keys(json.loads(schema.read_text()))
    cases = [
        ("eMarble", ["Natural"], ["eMarble"]),
        ("eMarble {color_name}", ["Natural"], ["eMarble Natural"]),
        ("Matte {color_name}", ["Black", "White"], ["Matte Black", "Matte White"]),
        ("eMarble", ["Black", "White"], None),
        ("eMarble {wrong}", ["Black", "White"], None),
        ("", ["Natural"], None),
    ]

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "example.json"
        for name, colors, expected_names in cases:
            data = {
                "manufacturer": "Example",
                "filaments": [{
                    "name": name,
                    "material": "PLA",
                    "density": 1.24,
                    "weights": [
                        {"weight": 500, "spool_weight": 200},
                        {"weight": 1000, "spool_weight": 200},
                    ],
                    "diameters": [1.75, 2.85],
                    "colors": [{"name": color, "hex": "888888"} for color in colors],
                }],
            }
            path.write_text(json.dumps(data))
            valid = expected_names is not None
            result = subprocess.run(
                ["check-jsonschema", "--schemafile", str(schema), str(path)],
                capture_output=True, text=True,
            )
            assert result.returncode == (0 if valid else 1), (
                name, colors, result.stdout, result.stderr,
            )
            report = lint_file(path, keysets)
            assert (not report.errors) == valid, (name, colors, report.errors)
            if valid:
                entries = list(get_filaments_from_data(data))
                assert [entry["name"] for entry in entries] == expected_names * 4
                assert len({entry["id"] for entry in entries}) == len(entries)

    print("ok (6 filament name cases)")


if __name__ == "__main__":
    test()
