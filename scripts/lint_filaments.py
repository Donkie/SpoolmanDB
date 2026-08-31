"""Lints the filament source files against the conventions in CONTRIBUTING.md.

Errors are things that are mechanically certain to be wrong and fail the build.
Warnings are heuristics that need a human to judge; they never fail the build.
"""

import json
import re
import sys
from pathlib import Path

SCHEMA = Path("filaments.schema.json")
FILAMENTS_DIR = Path("filaments")

PLACEHOLDER = "{color_name}"

# Colors named these may legitimately use a pure CSS value.
PURE_HEX_OK = {"000000", "ffffff"}

# Densities outside these bounds are unusual enough to be worth a look. Wide on
# purpose: filled filaments are genuinely heavy and foaming ones genuinely light.
DENSITY_BANDS = {
    "PLA": (1.15, 1.35),
    "PETG": (1.20, 1.32),
    "ABS": (1.00, 1.10),
    "ASA": (1.02, 1.15),
    "TPU": (1.10, 1.30),
    "PC": (1.15, 1.25),
    "PVA": (1.20, 1.30),
    "HIPS": (1.00, 1.10),
    "PCTG": (1.20, 1.30),
}

TEMP_BANDS = {
    "extruder_temp": (150, 450),
    "bed_temp": (0, 160),
}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where, msg, hint=None):
        self.errors.append((where, msg, hint))

    def warn(self, where, msg, hint=None):
        self.warnings.append((where, msg, hint))


def allowed_keys(schema: dict) -> tuple[set, set, set]:
    """Reads the permitted key names straight out of the JSON schema."""
    item = schema["properties"]["filaments"]["items"]
    return (
        set(item["properties"]),
        set(item["properties"]["colors"]["items"]["properties"]),
        set(item["properties"]["weights"]["items"]["properties"]),
    )


def base_material(material: str) -> str:
    return re.split(r"[-+]", material)[0]


def squash(text: str) -> str:
    """Lowercases and drops separators, so 'PLA - ' == 'pla'."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def squash_material(text: str) -> str:
    """Like squash, but keeps '+' so that ABS+ stays distinct from ABS."""
    return re.sub(r"[^a-z0-9+]", "", text.lower())


def check_keys(rep, where, obj, permitted, kind):
    for key in obj:
        if key in permitted:
            continue
        near = [p for p in permitted if squash(p) == squash(key)]
        hint = f"did you mean {near[0]!r}?" if near else f"allowed: {', '.join(sorted(permitted))}"
        rep.error(
            where,
            f"unknown {kind} field {key!r}",
            f"{hint} Unknown fields pass schema validation and are then dropped, "
            "so this data would never reach the database.",
        )


def check_name(rep, where, name, material, manufacturer):
    if PLACEHOLDER not in name:
        rep.error(where, f"name {name!r} is missing the {PLACEHOLDER} placeholder")
        return

    if name != name.strip() or "  " in name:
        rep.error(where, f"name {name!r} has leading, trailing or doubled whitespace")

    remainder = name.replace(PLACEHOLDER, "")

    # Only an error when the name is *nothing but* the material. Real product
    # lines that contain the material (PolyLite PLA, CR-PETG) are fine.
    if squash_material(remainder) in {
        squash_material(material),
        squash_material(base_material(material)),
    }:
        rep.error(
            where,
            f"name {name!r} is just the material, which is already in the material field",
            f'use "name": "{PLACEHOLDER}"',
        )

    if squash(remainder) in {squash(manufacturer), squash(manufacturer) + squash(material)}:
        rep.error(
            where,
            f"name {name!r} is just the manufacturer, which is already in the manufacturer field",
            f'use "name": "{PLACEHOLDER}"',
        )
    elif squash(manufacturer) and squash(manufacturer) in squash(remainder):
        rep.warn(
            where,
            f"name {name!r} repeats the manufacturer name",
            "the manufacturer is already a field, drop it from the name unless "
            "it is genuinely part of the product name",
        )


def check_colors(rep, where, filament):
    seen = {}
    for i, color in enumerate(filament["colors"]):
        name = color.get("name", "")
        cwhere = f"{where} color[{i}]"

        if PLACEHOLDER in name:
            rep.error(
                cwhere,
                f"color name {name!r} contains {PLACEHOLDER}",
                "the placeholder belongs in the filament name field; this field "
                "takes the literal color name",
            )
        if name != name.strip() or "  " in name:
            rep.error(cwhere, f"color name {name!r} has leading, trailing or doubled whitespace")

        key = squash(name)
        if key in seen:
            rep.error(cwhere, f"duplicate color name {name!r} (also at color[{seen[key]}])")
        else:
            seen[key] = i

        if ("hex" in color) == ("hexes" in color):
            rep.error(cwhere, f"color {name!r} must have exactly one of hex or hexes")
        if ("hexes" in color) != ("multi_color_direction" in color or
                                  "multi_color_direction" in filament):
            rep.error(
                cwhere,
                f"color {name!r}: hexes and multi_color_direction must be set together",
            )

        for value in [color["hex"]] if "hex" in color else color.get("hexes", []):
            v = value.lower()[:6]
            if v not in PURE_HEX_OK and re.fullmatch(r"(00|ff|80|c0|40){3}", v):
                rep.warn(
                    cwhere,
                    f"color {name!r} uses the pure CSS value {value!r}",
                    "real filament rarely lands exactly on a web colour; take it "
                    "from a product photo",
                )


def check_numbers(rep, where, filament):
    material = filament["material"]
    band = DENSITY_BANDS.get(base_material(material))
    density = filament["density"]
    if band and not (band[0] <= density <= band[1]):
        rep.warn(
            where,
            f"density {density} is outside the usual {band[0]}-{band[1]} for {material}",
            "fine if the manufacturer publishes it (filled and foaming filaments "
            "differ a lot); link the source in the PR",
        )

    for field, (lo, hi) in TEMP_BANDS.items():
        if field in filament and not (lo <= filament[field] <= hi):
            rep.error(where, f"{field} {filament[field]} is outside {lo}-{hi}")
        rng = filament.get(f"{field}_range")
        if rng and rng[0] > rng[1]:
            rep.error(where, f"{field}_range {rng} is the wrong way round")
        if rng and field in filament and not (rng[0] <= filament[field] <= rng[1]):
            rep.error(
                where,
                f"{field} {filament[field]} lies outside its own {field}_range {rng}",
            )

    for i, weight in enumerate(filament["weights"]):
        net = weight["weight"]
        tare = weight.get("spool_weight")
        if tare is not None and tare >= net:
            rep.warn(
                f"{where} weights[{i}]",
                f"spool_weight {tare} is not less than the filament weight {net}",
                "weight is the net filament weight and spool_weight the empty "
                "spool; a store listing's gross weight is neither",
            )

    combos = (
        len(filament["weights"]) * len(filament["diameters"]) * len(filament["colors"])
    )
    if combos > 60:
        rep.warn(
            where,
            f"expands to {combos} database entries",
            "every weight x diameter x colour combination is generated; split the "
            "object up if some of those combinations are not actually sold",
        )


def lint_file(path: Path, keysets) -> Report:
    rep = Report()
    fil_keys, color_keys, weight_keys = keysets

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        rep.error(path.name, f"invalid JSON: {exc}")
        return rep

    manufacturer = data.get("manufacturer", "")
    expected = re.sub(r"[^a-z0-9]", "", manufacturer.lower())
    if path.stem.lower() != expected and expected:
        rep.warn(
            path.name,
            f"filename does not match manufacturer {manufacturer!r}",
            f"consider {expected}.json",
        )

    for i, filament in enumerate(data.get("filaments", [])):
        where = f"{path.name} filaments[{i}]"
        check_keys(rep, where, filament, fil_keys, "filament")
        for j, color in enumerate(filament.get("colors", [])):
            check_keys(rep, f"{where} color[{j}]", color, color_keys, "color")
        for j, weight in enumerate(filament.get("weights", [])):
            check_keys(rep, f"{where} weights[{j}]", weight, weight_keys, "weight")

        if not {"name", "material", "colors", "weights", "diameters", "density"} <= set(filament):
            continue  # schema validation reports missing required fields

        check_name(rep, where, filament["name"], filament["material"], manufacturer)
        check_colors(rep, where, filament)
        check_numbers(rep, where, filament)

    return rep


def main(argv):
    paths = [Path(a) for a in argv[1:]] or sorted(FILAMENTS_DIR.glob("*.json"))
    keysets = allowed_keys(json.loads(SCHEMA.read_text(encoding="utf-8")))

    errors = warnings = 0
    for path in paths:
        rep = lint_file(path, keysets)
        errors += len(rep.errors)
        warnings += len(rep.warnings)
        for where, msg, hint in rep.errors:
            print(f"error: {where}: {msg}")
            if hint:
                print(f"       {hint}")
        for where, msg, hint in rep.warnings:
            print(f"warning: {where}: {msg}")
            if hint:
                print(f"         {hint}")

    print(f"\n{len(paths)} file(s), {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
