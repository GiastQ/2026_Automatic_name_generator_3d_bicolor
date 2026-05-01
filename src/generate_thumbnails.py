"""Thumbnail generation helpers for OpenSCAD previews.

Author: Giustino C. Miglionico
Date: 2026-05-01
License: MIT
"""

import subprocess
from pathlib import Path

from .utils import find_openscad

# (camera, imgsize, projection)
_RENDERS: dict[str, tuple[str, str, str]] = {
    "plate_1.png":          ("0,0,0,55,0,25,250", "1024,768", "perspective"),
    "plate_no_light_1.png": ("0,0,0,55,0,25,250", "1024,768", "perspective"),
    "top_1.png":            ("0,0,0,0,0,0,200",   "1024,768", "orthogonal"),
    "pick_1.png":           ("0,0,0,45,0,45,200",  "500,500",  "perspective"),
    "plate_1_small.png":    ("0,0,0,55,0,25,250",  "256,256",  "perspective"),
}

_COLOR_SCHEME = "Tomorrow Night"


def generate_thumbnails(scad_file: str | Path, output_dir: str | Path,
                        openscad_cmd: str | None = None,
                        quiet: bool = False) -> dict[str, Path]:
    """Render 5 PNG thumbnails from a SCAD file using OpenSCAD.

    Returns a dict {filename: Path} for each successfully generated image.
    """
    openscad = find_openscad(openscad_cmd)
    if not openscad:
        if not quiet:
            print("WARNING: OpenSCAD not found — skipping thumbnails.")
        return {}

    scad_path = Path(scad_file)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    generated: dict[str, Path] = {}
    for filename, (camera, imgsize, projection) in _RENDERS.items():
        out_file = out_path / filename
        cmd = [
            openscad,
            "--export-format", "png",
            "-o", str(out_file),
            "--imgsize", imgsize,
            "--camera", camera,
            "--projection", projection,
            "--colorscheme", _COLOR_SCHEME,
            "--autocenter",
            "--viewall",
            str(scad_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            generated[filename] = out_file
        except subprocess.CalledProcessError as e:
            if not quiet:
                print(f"  WARNING: thumbnail {filename} failed — {e.stderr[:120]}")

    return generated
