"""OpenSCAD rendering helpers for the keychain generator.

Author: Giustino C. Miglionico
Date: 2026-05-01
License: MIT
"""

import subprocess
from pathlib import Path

from .models import KeychainParams
from .utils import find_openscad, safe_filename, scad_escape

# SCAD template — variable names stay in Italian because they are part of the
# OpenSCAD source (Customizer labels), not the Python API.
_SCAD_TEMPLATE = """\
use <Chewy-Regular.ttf>
use <Lobster-Regular.ttf>
use <Pacifico-Regular.ttf>

nome = "{name}";
font_utilizzato = "{font}";

colore_unico = "{base_color}";
colore_testo  = "{text_color}";

altezza_testo          = {text_height};
spessore_base          = {base_thickness};
spessore_testo         = {text_thickness};
offset_val             = {offset};

diametro_esterno_gancio = {ring_outer_dia};
diametro_interno_gancio = {ring_inner_dia};
spostamento_x           = {ring_x};
spostamento_y           = {ring_y};

module base_shape() {{
    union() {{
        linear_extrude(height = spessore_base)
            offset(delta = offset_val)
                text(nome, size = altezza_testo, font = font_utilizzato,
                     halign = "left", valign = "baseline");
        translate([spostamento_x, spostamento_y, 0])
            cylinder(d = diametro_esterno_gancio, h = spessore_base, $fn = 50);
    }}
}}

module ring_hole() {{
    translate([spostamento_x, spostamento_y, -0.1])
        cylinder(d = diametro_interno_gancio, h = spessore_base + 0.2, $fn = 50);
}}

{render_block}
"""

_BLOCK_BASE = """\
color(colore_unico) difference() {
    base_shape();
    ring_hole();
}
"""

_BLOCK_TEXT = """\
translate([0, 0, spessore_base])
    color(colore_testo)
        linear_extrude(height = spessore_testo)
            text(nome, size = altezza_testo, font = font_utilizzato,
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
