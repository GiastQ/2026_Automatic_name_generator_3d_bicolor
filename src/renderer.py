"""OpenSCAD rendering helpers for the keychain generator.

Author: Giustino C. Miglionico
Date: 2026-05-01
License: MIT
"""

import subprocess
from pathlib import Path

from .models import KeychainParams
from .utils import find_openscad, safe_filename, scad_escape

# SCAD template variable names are kept in English because they are part of the
# generated OpenSCAD source, not the Python API.
_SCAD_TEMPLATE = """\
use <Chewy-Regular.ttf>
use <Lobster-Regular.ttf>
use <Pacifico-Regular.ttf>

name = "{name}";
selected_font = "{font}";

base_color = "{base_color}";
text_color = "{text_color}";

text_height = {text_height};
base_thickness = {base_thickness};
text_thickness = {text_thickness};
offset_value = {offset};

ring_outer_diameter = {ring_outer_dia};
ring_inner_diameter = {ring_inner_dia};
ring_offset_x = {ring_x};
ring_offset_y = {ring_y};

module base_shape() {{
    union() {{
        linear_extrude(height = base_thickness)
            offset(delta = offset_value)
                text(name, size = text_height, font = selected_font,
                     halign = "left", valign = "baseline");
        translate([ring_offset_x, ring_offset_y, 0])
            cylinder(d = ring_outer_diameter, h = base_thickness, $fn = 50);
    }}
}}

module ring_hole() {{
    translate([ring_offset_x, ring_offset_y, -0.1])
        cylinder(d = ring_inner_diameter, h = base_thickness + 0.2, $fn = 50);
}}

{render_block}
"""

_BLOCK_BASE = """\
color(base_color) difference() {
    base_shape();
    ring_hole();
}
"""

_BLOCK_TEXT = """\
translate([0, 0, base_thickness])
    color(text_color)
        linear_extrude(height = text_thickness)
            text(name, size = text_height, font = selected_font,
                 halign = "left", valign = "baseline");
"""


def render_scad(p: KeychainParams, part_type: str = "full") -> str:
    if part_type == "base":
        block = _BLOCK_BASE
    elif part_type == "text":
        block = _BLOCK_TEXT
    else:
        block = _BLOCK_BASE + _BLOCK_TEXT

    return _SCAD_TEMPLATE.format(
        name=scad_escape(p.name),
        font=scad_escape(p.font),
        base_color=p.base_color,
        text_color=p.text_color,
        text_height=p.text_height,
        base_thickness=p.base_thickness,
        text_thickness=p.text_thickness,
        offset=p.offset,
        ring_outer_dia=p.ring_outer_dia,
        ring_inner_dia=p.ring_inner_dia,
        ring_x=p.ring_x,
        ring_y=p.ring_y,
        render_block=block,
    )


def save_scad(p: KeychainParams, out_dir: str,
              part_type: str = "full", suffix: str = "") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / (safe_filename(p.name) + suffix + ".scad")
    path.write_text(render_scad(p, part_type), encoding="utf-8")
    return path


def run_openscad(input_scad: Path, output_file: Path,
                 openscad_cmd: str | None = None) -> bool:
    cmd = find_openscad(openscad_cmd)
    if not cmd:
        print("WARNING: OpenSCAD not found.")
        return False
    try:
        subprocess.run([cmd, "-o", str(output_file), str(input_scad)],
                       check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"OpenSCAD error: {e}")
        return False
