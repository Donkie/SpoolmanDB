"""This script takes in the directory of filament json files, expands them and writes them to a single output json."""

from enum import StrEnum
import json
from pathlib import Path
from typing import Iterator
from typing import TypedDict, NotRequired


class SpoolType(StrEnum):
    PLASTIC = "plastic"
    CARDBOARD = "cardboard"
    METAL = "metal"


class Finish(StrEnum):
    MATTE = "matte"
    GLOSSY = "glossy"


class MultiColorDirection(StrEnum):
    COAXIAL = "coaxial"
    LONGITUDINAL = "longitudinal"


class Pattern(StrEnum):
    MARBLE = "marble"
    SPARKLE = "sparkle"


class Weight(TypedDict):
    weight: float
    spool_weight: NotRequired[float]
    spool_type: NotRequired[SpoolType | None]


class Color(TypedDict):
    name: str
    hex: NotRequired[str]
    hexes: NotRequired[list[str]]
    finish: NotRequired[Finish | None]
    multi_color_direction: NotRequired[MultiColorDirection | None]
    pattern: NotRequired[Pattern | None]
    translucent: NotRequired[bool]
    glow: NotRequired[bool]

class Prices(TypedDict):
    USD: NotRequired[float]
    EUR: NotRequired[float]
    GBP: NotRequired[float]
    AUD: NotRequired[float]
    CAD: NotRequired[float]
    JPY: NotRequired[float]
    KRW: NotRequired[float]

class Filament(TypedDict):
    name: str
    material: str
    prices: NotRequired[Prices | None]
    density: float
    weights: list[Weight]
    diameters: list[float]
    colors: list[Color]
    extruder_temp: NotRequired[int]
    extruder_temp_range: NotRequired[list[int]]
    bed_temp: NotRequired[int]
    bed_temp_range: NotRequired[list[int]]
    finish: NotRequired[Finish | None]
    multi_color_direction: NotRequired[MultiColorDirection | None]
    pattern: NotRequired[Pattern | None]
    translucent: NotRequired[bool]
    glow: NotRequired[bool]


SPOOL_TYPE_MAP = {
    None: "n",
    SpoolType.PLASTIC: "p",
    SpoolType.CARDBOARD: "c",
    SpoolType.METAL: "m",
}


def generate_id(
    *,
    manufacturer: str,
    name: str,
    material: str,
    weight: float,
    diameter: float,
    spool_type: SpoolType | None,
) -> str:
    """Generates a unique ID for the given filament data."""
    # Remove any non-ascii from name
    name = name.encode("ascii", "ignore").decode()
    weight_s = f"{weight:.0f}"
    diameter_s = f"{diameter:.2f}".replace(".", "")
    spooltype_s = SPOOL_TYPE_MAP[spool_type]
    return f"{manufacturer.lower()}_{material.lower()}_{name.lower()}_{weight_s}_{diameter_s}_{spooltype_s}".replace(
        " ", ""
    )


def expand_filament_data(manufacturer: str, data: Filament) -> Iterator[dict]:
    """Expands the given filament data by generating multiple filament objects based on the weights, diameters, and colors."""
    name = data["name"]
    material = data["material"]
    prices = data.get("prices", None)
    density = data["density"]
    weights = data["weights"]
    diameters = data["diameters"]
    colors = data["colors"]
    extruder_temp = data.get("extruder_temp", None)
    extruder_temp_range = data.get("extruder_temp_range", None)
    bed_temp = data.get("bed_temp", None)
    bed_temp_range = data.get("bed_temp_range", None)
    finish = data.get("finish", None)
    multi_color_direction = data.get("multi_color_direction", None)
    pattern = data.get("pattern", None)
    translucent = data.get("translucent", False)
    glow = data.get("glow", False)

    for weight_obj in weights:
        weight = weight_obj["weight"]
        spool_weight = weight_obj.get("spool_weight", None)
        spool_type = weight_obj.get("spool_type", None)

        for diameter in diameters:
            for color_obj in colors:
                color_name = color_obj["name"]
                color_hex = color_obj.get("hex", None)
                color_hexes = color_obj.get("hexes", None)
                color_finish = color_obj.get("finish", None)
                color_multi_color_direction = color_obj.get(
                    "multi_color_direction", None
                )
                color_pattern = color_obj.get("pattern", None)
                color_translucent = color_obj.get("translucent", None)
                color_glow = color_obj.get("glow", None)

                if color_finish is None:
                    color_finish = finish

                if color_multi_color_direction is None:
                    color_multi_color_direction = multi_color_direction

                if color_pattern is None:
                    color_pattern = pattern

                if color_translucent is None:
                    color_translucent = translucent

                if color_glow is None:
                    color_glow = glow

                formatted_name = name.format(color_name=color_name)

                if color_hex is None and color_hexes is None:
                    raise ValueError(
                        f"Filament {formatted_name} by {manufacturer} has no hex or hexes specified."
                    )

                if color_hex is not None and color_hexes is not None:
                    raise ValueError(
                        f"Filament {formatted_name} by {manufacturer} has both hex and hexes specified."
                    )

                if color_multi_color_direction is not None and color_hexes is None:
                    raise ValueError(
                        f"Filament {formatted_name} by {manufacturer} has no hexes specified but multi_color_direction is set."
                    )

                if color_multi_color_direction is None and color_hexes is not None:
                    raise ValueError(
                        f"Filament {formatted_name} by {manufacturer} has hexes specified but no multi_color_direction is set."
                    )

                yield {
                    "id": generate_id(
                        manufacturer=manufacturer,
                        name=formatted_name,
                        material=material,
                        weight=weight,
                        diameter=diameter,
                        spool_type=spool_type,
                    ),
                    "manufacturer": manufacturer,
                    "name": formatted_name,
                    "material": material,
                    "prices": prices,
                    "density": density,
                    "weight": weight,
                    "spool_weight": spool_weight,
                    "spool_type": spool_type,
                    "diameter": diameter,
                    "color_hex": color_hex,
                    "color_hexes": color_hexes,
                    "extruder_temp": extruder_temp,
                    "extruder_temp_range": extruder_temp_range,
                    "bed_temp": bed_temp,
                    "bed_temp_range": bed_temp_range,
                    "finish": color_finish,
                    "multi_color_direction": color_multi_color_direction,
                    "pattern": color_pattern,
                    "translucent": color_translucent,
                    "glow": color_glow,
                }


def get_filaments_from_data(data: dict) -> Iterator[dict]:
    """Retrieves filaments from the provided data, assigns the manufacturer to each filament, and returns the list of filaments."""
    for filament_data in data["filaments"]:
        yield from expand_filament_data(data["manufacturer"], filament_data)


def load_json(file: Path) -> dict:
    """A function that loads JSON data from a file and returns it as a dictionary."""
    with file.open() as f:
        return json.load(f)


def compile_filaments():
    """Compiles all filament data from JSON files in the "filaments" directory and writes it to a single output JSON file."""
    all_filaments = []
    for file in Path("filaments").glob("*.json"):
        print(f"Compiling {file}")
        all_filaments.extend(get_filaments_from_data(load_json(file)))

    # Validate that all ids are unique. Find the non-unique ones and print them.
    seen_ids = set()
    duplicates = [
        f for f in all_filaments if f["id"] in seen_ids or seen_ids.add(f["id"])
    ]
    if duplicates:
        print("ERROR: Non-unique filament IDs found:")
        for f in duplicates:
            print(f["id"])
        raise ValueError("Found non-unique ids")

    # Sort the filaments by manufacturer, material, then name
    all_filaments.sort(key=lambda x: (x["manufacturer"], x["material"], x["name"]))

    print("Writing all filaments to 'filaments.json'")
    with Path("filaments.json").open("w") as f:
        json.dump(all_filaments, f, indent=2)


if __name__ == "__main__":
    print("Compiling all filaments...")
    compile_filaments()
    print("Done!")
