# Contributing

Field descriptions are in the [README](README.md). This page is the rules that
come up most in review.

## Before you open a PR

- One manufacturer per PR. Size doesn't matter, a full catalog in one PR is fine.
- Link your sources in the PR description.
- Check the [open PRs](https://github.com/Donkie/SpoolmanDB/pulls) for the same
  manufacturer first. Duplicates are common.
- Run the validation below.
- Make sure the diff contains only your manufacturer's file.

To update a PR, push to the same branch. Don't open a new one.

## Sources

Link where each product's data came from: product page, technical data sheet, or
spec sheet. A PR without sources will be closed.

**Don't use AI to generate the data.** It will fill in density, spool weight and
hex codes with plausible values whether or not the manufacturer publishes them,
and once merged nobody can tell those apart from real ones. This data is used to
work out how much filament people have left. Read the values off a real source
yourself.

If you can't find a value, leave the field out. An empty optional field is fine,
a guessed one is a bug.

## Naming

**Don't repeat the material in the name.** It's already its own field.

```jsonc
"material": "PLA", "name": "PLA {color_name}"   // no
"material": "PLA", "name": "{color_name}"       // yes
```

**Don't put the manufacturer in the name.** Also already its own field.

**Product lines go in `name`.** Series names, finishes and variants:

```jsonc
"name": "Matte {color_name}"
"name": "Silk {color_name}"
"name": "{color_name} Metallic"
"name": "Hyper {color_name}"
```

Spell it the way the manufacturer does, including their capitalisation.

## The material field

`material` is the plastic, not the branding. It's used to group and filter across
every manufacturer, so it has to mean the same thing everywhere.

| They call it | You write                                             |
| ------------ | ----------------------------------------------------- |
| PETG-Tough   | `"material": "PETG"`, `"name": "Tough {color_name}"`  |
| PETG HF      | `"material": "PETG"`, `"name": "HF {color_name}"`     |
| TPU for AMS  | `"material": "TPU"`, `"name": "{color_name} for AMS"` |

`-CF` and `-GF` mean a real carbon or glass fiber additive: `PETG-CF`, `ASA-GF`,
`PETG-CF10`. `-95A` and `-55D` on TPU are shore hardness. Don't use that pattern
for anything else.

Some blends really are their own material and keep a compound name, like `PA6-GF`
or `PC+ABS`. If the term describes what the plastic is, it goes in `material`. If
it describes a product line, it goes in `name`.

## Colors

Use the manufacturer's own color name, translated to English if needed. Don't
invent nicer ones.

`{color_name}` is a placeholder for the `name` field. Never put it in a color's
`name`, that field takes the literal color.

`hex` is six hex digits, no leading `#`, optionally two more for alpha on
transparent filaments. Use the manufacturer's code if they publish one, otherwise
take it off a product photo. Don't default to `FF0000` for "Red".

Multi-color filaments use `hexes` instead of `hex`, plus `multi_color_direction`:
`coaxial` if the colors run side by side, `longitudinal` if the color changes
along the spool.

## Weights, diameters and colors multiply

The build generates every combination of `weights` × `diameters` × `colors`. Two
weights, two diameters and ten colors gives you forty database entries.

So only group things in one object if every combination is actually sold. If the
1 kg spool comes in ten colors but the 5 kg only comes in black, that's two
filament objects, not one object with two weights.

Same for spool types. A filament sold on both cardboard and plastic gets a second
entry under `weights`, but only if every color is available on both.

`weight` is the filament's net weight and `spool_weight` is the empty spool.
Don't use the shipping weight from a store listing for either.

## Temperatures

`extruder_temp` and `bed_temp` are single values: the temperature to start at
that works in most cases. If the manufacturer publishes a range you can also add
`extruder_temp_range` and `bed_temp_range` as two-element arrays. Leave the bed
temperature out if none is needed.

## Keep the diff clean

- **Don't commit `filaments.json`.** It's generated and gitignored. Committing it
  adds a six-figure line count to your diff.
- Don't commit editor files like `.vscode/` or `.DS_Store`.
- Don't change the workflows, schema or compile script in a data PR. If the
  schema needs changing, open a separate PR and say why.
- Watch your line endings. Some files are CRLF and a Windows editor converting
  one to LF rewrites every line.
- Spell the field names exactly. Unknown keys pass validation and then get
  dropped silently, so `extruder_temp_rang` or a trailing space means your data
  never lands.
- 4-space indent.

## Things we don't store

Already been asked, already declined:

- **Price.** Too variable across countries, retailers and sales.
- **`silk` and `metallic` finishes.** They look like `glossy`, and nobody
  filtering a list would know which one to pick. Put it in the name and use
  `"finish": "glossy"`.
- **Diameter tolerance.** Not consistently published.
- **Scraping scripts.** Commit the data they produce, not the script. Scripts
  here become something that has to be maintained here.

## New manufacturer

Create `filaments/<manufacturer>.json`, lowercase, no spaces.

```jsonc
{
    "manufacturer": "Example Filaments",
    "filaments": [
        {
            "name": "{color_name}",
            "material": "PLA",
            "density": 1.24,
            "weights": [
                { "weight": 1000, "spool_weight": 220, "spool_type": "plastic" }
            ],
            "diameters": [1.75],
            "extruder_temp": 210,
            "bed_temp": 60,
            "colors": [
                { "name": "Black", "hex": "1A1A1A" }
            ]
        }
    ]
}
```

## Validating

```bash
pipx install check-jsonschema

check-jsonschema --schemafile filaments.schema.json filaments/*
python3 scripts/lint_filaments.py filaments/yourfile.json
python3 scripts/compile_filaments.py
```

All three have to pass, CI runs the same thing. The compile step catches what
the schema can't, like duplicate IDs. The linter checks the conventions on this
page, and also prints warnings that don't fail the build but are usually worth
a look.

When you open the PR, a bot comments with every entry your change would add to
Spoolman. Read it against the manufacturer's catalog before asking for review.
