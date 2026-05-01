"""Core pipeline for the automatic 3D bi-color keychain generator.

Author: Giustino C. Miglionico
Date: 2026-05-01
License: MIT
"""

import argparse
import csv
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from pathlib import Path
from threading import Lock

from tqdm import tqdm

from .mesh_utils import create_3mf_from_stls
from .models import KeychainParams
from .renderer import run_openscad, save_scad
from .utils import safe_filename

_FONTS_DIR = Path(__file__).parent.parent / "Fonts"


def generate_keychain(params: KeychainParams, output_dir: str,
                      export_3mf: bool, quiet: bool = False,
                      openscad_cmd: str | None = None,
                      output_name: str | None = None) -> None:
    """Generate a single keychain 3MF.

    output_name overrides the output filename stem (used for copies).
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        for ttf in _FONTS_DIR.glob("**/*.ttf"):
            dest = tmp_path / ttf.name
            if not dest.exists():
                shutil.copy2(ttf, dest)

        scad_path = save_scad(params, tmp, part_type="full")

        if not export_3mf:
            if not quiet:
                print(f"  -> SCAD: {scad_path.name}")
            return

        base_scad = save_scad(params, tmp, part_type="base", suffix="_base")
        text_scad = save_scad(params, tmp, part_type="text", suffix="_text")
        base_stl = base_scad.with_suffix(".stl")
        text_stl = text_scad.with_suffix(".stl")

        ok_base = run_openscad(base_scad, base_stl, openscad_cmd)
        ok_text = run_openscad(text_scad, text_stl, openscad_cmd)

        if ok_base and ok_text:
            work_3mf = scad_path.with_suffix(".3mf")
            create_3mf_from_stls(
                [
                    (base_stl, params.base_color, f"{params.name}_base"),
                    (text_stl, params.text_color,  f"{params.name}_text"),
                ],
                work_3mf,
                scad_file=scad_path,
                work_dir=tmp,
                openscad_cmd=openscad_cmd,
                quiet=quiet,
            )
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            stem = output_name or safe_filename(params.name)
            final = Path(output_dir) / f"{stem}.3mf"
            shutil.move(str(work_3mf), str(final))
            if not quiet:
                print(f"  -> 3MF: {final}")
        else:
            if not quiet:
                print("  -> ERROR: STL generation failed.")


def process_csv(csv_path: str, output_dir: str = "output",
                export_3mf: bool = False, max_workers: int = 3,
                openscad_cmd: str | None = None) -> None:
    path = Path(csv_path)
    if not path.exists():
        print(f"Error: {csv_path} not found.")
        return

    csv_content = None
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            csv_content = path.read_text(encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if csv_content is None:
        raise ValueError(f"Cannot decode {csv_path}")

    # Build task list: each copy becomes an independent task with its own output name
    tasks: list[tuple[KeychainParams, str]] = []  # (params, output_stem)
    for row in csv.DictReader(StringIO(csv_content), delimiter=";"):
        p = KeychainParams(
            name=row.get("name", "Unknown"),
            font=row.get("font", "Chewy"),
        )
        if "text_height" in row:
            p.text_height = float(row["text_height"])
        quantity = int(row.get("quantity", 1) or 1)
        base_stem = safe_filename(p.name)
        for i in range(1, quantity + 1):
            tasks.append((p, f"{base_stem}_{i}"))

    if not tasks:
        print("No tasks found.")
        return

    print(f"Processing: {csv_path}  ({len(tasks)} files, {max_workers} workers)\n")

    lock = Lock()

    def worker(p: KeychainParams, stem: str) -> bool:
        try:
            generate_keychain(p, output_dir, export_3mf, quiet=True,
                              openscad_cmd=openscad_cmd, output_name=stem)
            with lock:
                tqdm.write(f"  OK  {stem}.3mf")
            return True
        except Exception as e:
            with lock:
                tqdm.write(f"  ERR {stem}: {e}")
            return False

    success = 0
    with tqdm(total=len(tasks), desc="Progress",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(worker, p, stem): stem for p, stem in tasks}
            for fut in as_completed(futures):
                if fut.result():
                    success += 1
                pbar.update(1)

    print(f"\nDone: {success}/{len(tasks)} files generated.")
    print(f"Output: '{output_dir}/'")


def main() -> None:
    parser = argparse.ArgumentParser(description="3D Keychain Generator")
    parser.add_argument("--name", type=str)
    parser.add_argument("--font", type=str, default="Chewy")
    parser.add_argument("--csv",  type=str)
    parser.add_argument("--out",  type=str, default="output")
    parser.add_argument("--export-3mf", action="store_true")
    parser.add_argument("--openscad", type=str, default=None,
                        metavar="PATH", help="Custom OpenSCAD executable path")
    args = parser.parse_args()

    if args.csv:
        process_csv(args.csv, args.out, export_3mf=args.export_3mf,
                    openscad_cmd=args.openscad)
    elif args.name:
        generate_keychain(
            KeychainParams(name=args.name, font=args.font),
            args.out, args.export_3mf, openscad_cmd=args.openscad,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
