# Automatic 3D Bi-color Keychain Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![OpenSCAD](https://img.shields.io/badge/OpenSCAD-required-orange.svg)](https://openscad.org/)

Python tool to generate personalized keychains in **bi-color 3MF format** compatible with **Bambu Studio**.

Starting from a CSV file with names, fonts, and quantities, it creates print-ready keychains with a shaped base, raised text, generated SCAD/STL intermediates, and a final 3MF package that can be opened directly in Bambu Studio.

## What It Produces

For each requested name, the tool can generate:

- A SCAD preview of the geometry
- Two STL files, one for the base and one for the raised text
- A final 3MF file with Bambu Studio-compatible paint-color metadata
- Five PNG thumbnails embedded in the 3MF when OpenSCAD is available

The project is designed for batch generation, but it also supports single-name generation from the command line.

---

## Requirements

- **Python 3.9+**
- **OpenSCAD** installed ([download](https://openscad.org/downloads.html))
- Python dependency: `tqdm`

```bash
pip install tqdm
```

OpenSCAD is required only when you want to generate STL/3MF files. If you run the pipeline without `--export-3mf`, the script will stop after producing the SCAD file.

---

## Installation

1. Clone or download the repository.
2. Install Python dependencies.
3. Make sure OpenSCAD is available in your PATH, or keep it in a standard installation folder.

If OpenSCAD is not in PATH, you can pass its executable path with `--openscad`.

---

## Quick Start

### Batch generation from `names.csv`

1. Edit [names.csv](names.csv) with the names you want.
2. Run:

```bash
python main.py
```

The script reads the CSV in the project root and writes the generated files to `output/`.

### Generate a single keychain

```bash
python -m src.main --name "Laura" --font "Chewy" --out "output" --export-3mf
```

### Use a custom OpenSCAD path

```bash
python -m src.main --name "Laura" --export-3mf --openscad /usr/bin/openscad
```

On Windows, the path may look like `C:\Program Files\OpenSCAD\openscad.exe`.

---

## Project Structure

```
├── main.py                     # Entry point: runs batch generation from names.csv
├── names.csv                   # Input: list of names to generate
│
├── src/
│   ├── main.py                 # Pipeline orchestration (process_csv, generate_keychain)
│   ├── renderer.py             # SCAD generation and OpenSCAD render to STL
│   ├── mesh_utils.py           # 3MF creation with Bambu Studio paint_color format
│   ├── generate_thumbnails.py  # PNG preview rendering via OpenSCAD
│   ├── models.py               # KeychainParams dataclass
│   ├── utils.py                # Shared utilities (safe_filename, find_openscad, etc.)
│   └── Template.3mf            # Template with Bambu Studio project_settings and metadata
│
├── Fonts/
│   ├── Chewy/                  # Chewy-Regular.ttf + license
│   ├── Lobster/                # Lobster-Regular.ttf + license
│   └── Pacifico/               # Pacifico-Regular.ttf + license
│
└── output/                     # Auto-created - finished 3MF files ready for printing
```

The `output/` folder is ignored by Git. Intermediate files are created in the system temp directory and are removed automatically when the run finishes.

---

## Command Line Options

The main entry point is [src/main.py](src/main.py), which exposes both batch and single-item generation.

| Flag | Default | Description |
|------|---------|-------------|
| `--name` | none | Generate a single keychain for the given name |
| `--font` | `Chewy` | Font used for the name text |
| `--csv` | none | CSV file for batch generation |
| `--out` | `output` | Output directory for generated files |
| `--export-3mf` | off | Enable STL and 3MF generation |
| `--openscad` | auto-detect | Path to the OpenSCAD executable |

Behavior:

- If `--csv` is provided, the script processes the whole file in batch.
- If `--name` is provided, it generates just one keychain.
- If neither is provided, the CLI shows the help text.
- If `--export-3mf` is omitted, the script creates the SCAD file only.

---

## CSV Format

The batch CSV uses `;` as delimiter. The supported columns are:

- `name`: text to print on the keychain
- `font`: one of the bundled fonts
- `quantity`: how many copies to generate for that row
- `text_height`: optional override for the text size in millimeters

Example:

```csv
name;font;quantity
Andrea;Chewy;1
Marco;Lobster;1
Giulia;Pacifico;1
```

Example with text size override:

```csv
name;font;quantity;text_height
Andrea;Chewy;2;12
Marco;Lobster;1;14
```

The `quantity` column creates multiple output files with numbered suffixes.

Supported bundled fonts:

- `Chewy`
- `Lobster`
- `Pacifico`

The font files are copied into the temporary render directory automatically, so no system-wide font installation is needed.

---

## Technical Pipeline

```
names.csv
   │
   ▼
process_csv()            - reads CSV, starts thread pool
   │
   ▼ (per name, in parallel - 3 threads)
generate_keychain()      - all work in a temporary directory (auto-deleted)
   ├─ save_scad("full")  -> tmp/Name.scad        (base + text, used for thumbnails)
   ├─ save_scad("base")  -> tmp/Name_base.scad
   ├─ save_scad("text")  -> tmp/Name_text.scad
   ├─ run_openscad(base) -> tmp/Name_base.stl
   ├─ run_openscad(text) -> tmp/Name_text.stl
   └─ create_3mf_from_stls()
        ├─ merge base + text vertices into a single mesh
        ├─ paint_color="8" on base triangles  (extruder 1)
        ├─ paint_color="4" on text triangles  (extruder 2)
        ├─ render 5 PNG previews with OpenSCAD
        └─ write output/Name.3mf
```

   The pipeline works like this:

   1. The CSV is parsed and expanded into individual jobs, one per requested copy.
   2. Each job creates a temporary working directory.
   3. The SCAD source is generated from the selected parameters.
   4. OpenSCAD renders the base and text STLs.
   5. The STLs are merged into a single 3MF mesh with triangle-level paint colors.
   6. Thumbnails are rendered when possible and embedded into the final 3MF.

   Generation is parallelized with a thread pool. The default worker count is 3.

---

## Generated 3MF Format

Files are compatible with Bambu Studio's native format:

- **Single mesh** in `3D/Objects/object_1.model` with `paint_color` per triangle
- **`3D/3dmodel.model`** - thin wrapper (~1 KB) referencing geometry via `p:path`
- **`Metadata/model_settings.config`** - single object, extruder 1 as default
- **`Metadata/project_settings.config`** - copied from Template.3mf (bi-color print settings)
- **Unique UUIDs** generated for each file

The 3MF metadata includes the current creation and modification date, a title, and the Bambu Studio object structure needed for direct import.

Color encoding (paint_color):

| Value | Meaning |
|-------|---------|
| `8` | Filament 1 - keychain base |
| `4` | Filament 2 - raised text |

---

## KeychainParams

The geometry and visual parameters are defined in [src/models.py](src/models.py).

| Parameter | Default | Description |
|-----------|---------|-------------|
| `text_height` | `12` mm | Text size |
| `base_thickness` | `2` mm | Base thickness |
| `text_thickness` | `1` mm | Text relief height |
| `offset` | `2.3` mm | Base margin around text |
| `ring_outer_dia` | `6` mm | Keyring outer diameter |
| `ring_inner_dia` | `3` mm | Keyring hole diameter |
| `ring_x` | `-2` mm | Keyring X position |
| `ring_y` | `6` mm | Keyring Y position |
| `base_color` | `#0000FF` | Base color (extruder 1) |
| `text_color` | `#FF8800` | Text color (extruder 2) |

These values control both the SCAD geometry and the generated 3MF metadata.

---

## Thumbnails

Each 3MF includes 5 PNG previews generated by OpenSCAD:

| File | Size | View |
|------|------|------|
| `plate_1.png` | 1024×768 | 3/4 perspective |
| `plate_no_light_1.png` | 1024×768 | Perspective (no light) |
| `top_1.png` | 1024×768 | Top orthogonal |
| `pick_1.png` | 500×500 | Selection view |
| `plate_1_small.png` | 256×256 | Thumbnail |

If OpenSCAD is not available, the generator falls back to the preview images already present in `Template.3mf`.

---

## Output and Naming

By default, generated files are written to `output/` with a safe filename derived from the name in the CSV or CLI input.

If a row in the CSV has `quantity > 1`, the outputs are numbered with a suffix such as `_1`, `_2`, and so on.

---

## Notes

- Fonts are automatically copied to the temp directory before rendering - no system-level font installation needed
- Generation is multi-threaded (3 keychains in parallel); configurable via `max_workers` in `process_csv()`
- Names with accented characters (à, è, ì, etc.) are supported through automatic CSV encoding detection
- OpenSCAD is auto-detected on Windows, Linux, and macOS; use `--openscad` for a custom path
- If OpenSCAD is missing and `--export-3mf` is used, STL and 3MF generation will fail for that job

---

## License

This project is released under the MIT License.

The bundled font files keep their own upstream licenses in the corresponding folders under `Fonts/`.

---

## Troubleshooting

- If `python main.py` does nothing useful, check that `names.csv` exists in the repository root and uses `;` as separator.
- If OpenSCAD is not found, pass the executable path with `--openscad`.
- If a font name is incorrect, the generator may still run, but the resulting SCAD/OpenSCAD output may not match the intended style.
- If Bambu Studio shows unexpected colors, verify the imported filament mapping and the `paint_color` values in the generated 3MF.

---

## Workflow Summary

For a typical batch run:

1. Edit `names.csv`.
2. Run `python main.py`.
3. Open the generated 3MF files from `output/` in Bambu Studio.
4. Slice and print with the appropriate two-filament setup.
