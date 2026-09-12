import unittest

from scripts.compile_filaments import expand_filament_data


class FilamentOriginTests(unittest.TestCase):
    def test_country_of_origin_is_preserved_in_compiled_output(self):
        filament = {
            "name": "PLA {color_name}",
            "material": "PLA",
            "density": 1.24,
            "weights": [{"weight": 1000}],
            "diameters": [1.75],
            "colors": [{"name": "Red", "hex": "FF0000"}],
            "country_of_origin": "Germany",
        }

        compiled = list(expand_filament_data("Example", filament))

        self.assertEqual(len(compiled), 1)
        self.assertEqual(
            compiled[0]["country_of_origin"], filament["country_of_origin"]
        )


if __name__ == "__main__":
    unittest.main()
