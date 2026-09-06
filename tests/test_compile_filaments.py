import unittest

from scripts.compile_filaments import expand_filament_data


class FilamentDocumentLinkTests(unittest.TestCase):
    def test_document_links_are_preserved_in_compiled_output(self):
        filament = {
            "name": "PLA {color_name}",
            "material": "PLA",
            "density": 1.24,
            "weights": [{"weight": 1000}],
            "diameters": [1.75],
            "colors": [{"name": "Red", "hex": "FF0000"}],
            "sds_url": "https://example.com/pla-sds.pdf",
            "tds_url": "https://example.com/pla-tds.pdf",
        }

        compiled = list(expand_filament_data("Example", filament))

        self.assertEqual(len(compiled), 1)
        self.assertEqual(compiled[0]["sds_url"], filament["sds_url"])
        self.assertEqual(compiled[0]["tds_url"], filament["tds_url"])


if __name__ == "__main__":
    unittest.main()
