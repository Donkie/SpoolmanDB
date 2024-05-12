# SpoolmanDB
A centralized place to store information about 3D printing filaments and their manufacturers.

The database is hosted using GitHub Pages, you can browse it at: [https://donkie.github.io/SpoolmanDB/](https://donkie.github.io/SpoolmanDB/)

You can contribute to this database by adding/editing files and submitting pull requests in this repository.

## Filaments
The source files are in the `filaments` folder. When this database is deployed, they will be expanded/compiled into a single JSON file called `filaments.json`.

To limit the amount of duplication needed in the source files, each combination of weight, color and diameter will be represented in the compiled JSON. For example, if you specify two diameters, two weights, and two colors, you will get eight combinations in the JSON. There isn't currently any way to exclude specific combinations; either you will have to live with the database having invalid
entries or you can split up the filament object into multiple ones.

#### Source file fields
 * **name** - The product name. Should probably contain the format code `{color_name}` to automatically insert the color name.
 * **material** - The material name, e.g. PLA.
 * **density** - The density of the material in g/cm3.
 * **weights** - An array of objects with `weight` and `spool_weight` fields. Specify multiple here if the manufacturer sells the filament in e.g. 1 kg and 5 kg spools. `spool_weight` is optional but recommended.
 * **diameters** - An array of diameters in mm. Specify multiple here if the manufacturer sells the filament in both e.g. 1.75 and 2.85 mm diameters.
 * **extruder_temp** *(optional)* - Manufacturer recommended extruder temperature in °C.
 * **bed_temp** *(optional)* - Manufacturer recommended bed temperature in °C.
 * **colors** - An array of objects with `name` and `hex` fields. Name should be what the manufacturer calls it. Hex should be the hex code of the color, can include an alpha channel if it's a transparent color.

## Materials
All materials are found in the `materials.json` file.

#### Source file fields
 * **material** - The material name, e.g. PLA.
 * **density** - The density of the material in g/cm3.
 * **extruder_temp** - General extruder temperature for this material.
 * **bed_temp** - General bed temperature for this material.
