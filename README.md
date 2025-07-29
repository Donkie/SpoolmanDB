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
 * **price** *(optional)*- A key:value listing of currencies and the filament cost. e.g. `{ "USD": 19.99, "AUD": 30.99 }`
 * **density** - The density of the material in g/cm3.
 * **weights** - An array of objects with `weight`, `spool_weight` and `spool_type` fields. Specify multiple here if the manufacturer sells the filament in e.g. 1 kg and 5 kg spools. `spool_weight` is optional but recommended. `spool_type` is optional and can be any of "plastic", "cardboard" or "metal".
 * **diameters** - An array of diameters in mm. Specify multiple here if the manufacturer sells the filament in both e.g. 1.75 and 2.85 mm diameters.
 * **extruder_temp** *(optional)* - Manufacturer recommended extruder temperature in °C.
 * **bed_temp** *(optional)* - Manufacturer recommended bed temperature in °C.
 * **finish** *(optional)* - The finish of the filament, e.g. "matte" or "glossy". Only set this if the filament is designed with this in mind.
 * **multi_color_direction** *(optional)* - The direction of the multi-color filament, e.g. "coaxial" for a split/dual color filament, or "longitudinal" for a filament that changes color along its length.
 * **pattern** *(optional)* - Textured pattern, either "marble" or "sparkle" is currently supported. Feel free to add additional ones in the schema if necessary.
 * **translucent** *(optional)* - Boolean true/false if this filament is at least partially see-through.
 * **glow** *(optional)* - Boolean true/false if this filament has a glow-in-the-dark effect.
 * **colors** - An array of objects with `name` and `hex` fields. Name should be what the manufacturer calls it. Hex should be the hex code of the color, can include an alpha channel if it's a transparent color. If it's a multi-color filament, specify `hexes` instead of `hex` and provide a list of hex codes. You can also set the `finish`, `multi_color_direction`, `pattern`, `translucent` and `glow` fields here if the specific color is different from the others.

## Materials
All materials are found in the `materials.json` file.

#### Source file fields
 * **material** - The material name, e.g. PLA.
 * **density** - The density of the material in g/cm3.
 * **extruder_temp** - General extruder temperature for this material.
 * **bed_temp** - General bed temperature for this material.

## Testing compile script
If you don't have python install on the host, you can use Docker to test the compile script. 
Run `docker-compose up` and the container will be built, the compile attempted and the container will immediately exit.
