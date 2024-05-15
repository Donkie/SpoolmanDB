"""This script takes in the directory of filament json files, expands them and writes them to a single output json."""

from enum import Enum
import json
from pathlib import Path
from typing import Iterator
from typing import TypedDict, NotRequired


class SpoolType(Enum):
    PLASTIC = "plastic"
    CARDBOARD = "cardboard"
    METAL = "metal"


class Finish(Enum):
    MATTE = "matte"
    GLOSSY = "glossy"


class MultiColorDirection(Enum):
    COAXIAL = "coaxial"
    LONGITUDINAL = "longitudinal"


class Pattern(Enum):
    MARBLE = "marble"
    SPARKLE = "sparkle"


class Weight(TypedDict):
    weight: float
    spool_weight: NotRequired[float]
    spool_type: NotRequired[SpoolType | None]


class Color(TypedDict):
    name: str
    hex: str | list[str]


class Filament(TypedDict):
    name: str
    material: str
    density: float
    weights: list[Weight]
    diameters: list[float]
    colors: list[Color]
    extruder_temp: NotRequired[int]
    bed_temp: NotRequired[int]
    finish: NotRequired[Finish | None]
    multi_color_direction: NotRequired[MultiColorDirection | None]
    pattern: NotRequired[Pattern | None]
    translucent: NotRequired[bool]
    glow: NotRequired[bool]


def generate_id(
    manufacturer: str, name: str, material: str, weight: float, diameter: float
) -> str:
    """Generates a unique ID for the given filament data."""
    # Remove any non-ascii from name
    name = name.encode("ascii", "ignore").decode()
    weight_s = f"{weight:.0f}"
    diameter_s = f"{diameter:.2f}".replace(".", "")
    return f"{manufacturer.lower()}_{material.lower()}_{name.lower()}_{weight_s}_{diameter_s}".replace(
        " ", ""
    )


def expand_filament_data(manufacturer: str, data: Filament) -> Iterator[dict]:
    """Expands the given filament data by generating multiple filament objects based on the weights, diameters, and colors."""
    name = data["name"]
    material = data["material"]
    density = data["density"]
    weights = data["weights"]
    diameters = data["diameters"]
    colors = data["colors"]
    extruder_temp = data.get("extruder_temp", None)
    bed_temp = data.get("bed_temp", None)
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
                color_hex = color_obj["hex"]

                formatted_name = name.format(color_name=color_name)

                if isinstance(color_hex, list):
                    if multi_color_direction is None:
                        raise ValueError(
                            f"Filament {formatted_name} by {manufacturer} has multiple colors but no multi_color_direction specified."
                        )

                yield {
                    "id": generate_id(
                        manufacturer, formatted_name, material, weight, diameter
                    ),
                    "manufacturer": manufacturer,
                    "name": formatted_name,
                    "material": material,
                    "density": density,
                    "weight": weight,
                    "spool_weight": spool_weight,
                    "spool_type": spool_type,
                    "diameter": diameter,
                    "color_hex": color_hex,
                    "extruder_temp": extruder_temp,
                    "bed_temp": bed_temp,
                    "finish": finish,
                    "multi_color_direction": multi_color_direction,
                    "pattern": pattern,
                    "translucent": translucent,
                    "glow": glow,
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

    # Sort the filaments by manufacturer, material, then name
    all_filaments.sort(key=lambda x: (x["manufacturer"], x["material"], x["name"]))

    print("Writing all filaments to 'filaments.json'")
    with Path("filaments.json").open("w") as f:
        json.dump(all_filaments, f, indent=2)


if __name__ == "__main__":
    print("Compiling all filaments...")
    compile_filaments()
    print("Done!")
