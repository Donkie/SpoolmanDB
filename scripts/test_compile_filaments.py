"""Self-check for transmission distance in the compiled database.

Run with: python3 scripts/test_compile_filaments.py
"""

import json
import subprocess
import tempfile
from pathlib import Path

from compile_filaments import get_filaments_from_data


def test_country_of_origin():
    filament = {
        "name": "{color_name}", "material": "PLA", "density": 1.24,
        "weights": [{"weight": 500}, {"weight": 1000}],
        "diameters": [1.75, 2.85],
        "colors": [{"name": "Black", "hex": "1A1A1A"}],
    }
    data = {"manufacturer": "Example", "filaments": [filament]}
    original = list(get_filaments_from_data(data))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "example.json"
        for value in [None, "DE", "US", "CN", "TH", "ZZ", "UK", "de", "Germany", "", " DE", "DE\n", 42, False, []]:
            filament.pop("country_of_origin", None)
            if value is not None:
                filament["country_of_origin"] = value
            path.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                ["check-jsonschema", "--schemafile", "filaments.schema.json", str(path)],
                capture_output=True, text=True,
            )
            valid = value is None or value in ("DE", "US", "CN", "TH")
            assert (result.returncode == 0) == valid, (value, result.stdout, result.stderr)
            if valid:
                entries = list(get_filaments_from_data(data))
                assert len(entries) == 4
                assert all(entry["country_of_origin"] == value for entry in entries)
                assert [{k: v for k, v in e.items() if k != "country_of_origin"} for e in entries] == [
                    {k: v for k, v in e.items() if k != "country_of_origin"} for e in original
                ]
        filament["country_of_origin"] = None
        path.write_text(json.dumps(data), encoding="utf-8")
        assert subprocess.run(
            ["check-jsonschema", "--schemafile", "filaments.schema.json", str(path)],
            capture_output=True,
        ).returncode != 0


def test_transmission_distance():
    filament = {
        "name": "{color_name}",
        "material": "PLA",
        "density": 1.24,
        "weights": [{"weight": 500}, {"weight": 1000}],
        "diameters": [1.75, 2.85],
        "colors": [
            {"name": "Black", "hex": "1A1A1A", "transmission_distance": 0.5},
            {"name": "White", "hex": "FFFFFF", "transmission_distance": 5},
            {"name": "Red", "hex": "C01F1F"},
        ],
    }
    data = {"manufacturer": "Acme", "filaments": [filament]}
    entries = list(get_filaments_from_data(data))
    assert len(entries) == 12
    assert len({entry["id"] for entry in entries}) == 12
    for entry in entries:
        assert entry["transmission_distance"] == {
            "Black": 0.5, "White": 5, "Red": None,
        }[entry["name"]]

    # The same color can have a different TD in a separate diameter entry.
    filament["diameters"] = [1.75]
    filament["colors"] = filament["colors"][:1]
    other_diameter = {
        **filament,
        "diameters": [2.85],
        "colors": [{**filament["colors"][0], "transmission_distance": 0.7}],
    }
    data["filaments"].append(other_diameter)
    entries = list(get_filaments_from_data(data))
    assert len(entries) == 4
    assert len({entry["id"] for entry in entries}) == 4
    for entry in entries:
        assert entry["transmission_distance"] == {1.75: 0.5, 2.85: 0.7}[entry["diameter"]]


if __name__ == "__main__":
    test_country_of_origin()
    test_transmission_distance()
    print("ok")
