"""3MF assembly helpers for Bambu Studio compatibility.

Author: Giustino C. Miglionico
Date: 2026-05-01
License: MIT
"""

import os
import struct
import uuid
import zipfile
from datetime import date
from pathlib import Path
from typing import List, Tuple


class SimpleMesh:
    def __init__(self, vertices, triangles):
        self.vertices = vertices  # List of (x, y, z)
        self.triangles = triangles  # List of (v1, v2, v3) indices


def parse_ascii_stl(path: Path) -> SimpleMesh:
    vertices = []
    triangles = []
    vert_map = {}
    current_triangle = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] == "vertex":
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                p = (x, y, z)
                if p not in vert_map:
                    vert_map[p] = len(vertices)
                    vertices.append(p)
                current_triangle.append(vert_map[p])
                if len(current_triangle) == 3:
                    triangles.append(tuple(current_triangle))
                    current_triangle = []

    return SimpleMesh(vertices, triangles)


def read_stl(path: Path) -> SimpleMesh:
    is_ascii = False
    with open(path, "rb") as f:
        header = f.read(5)
        if header == b"solid":
            is_ascii = True
            try:
                f.readline()
            except Exception:
                is_ascii = False

    if is_ascii:
        try:
            return parse_ascii_stl(path)
        except Exception:
            pass

    with open(path, "rb") as f:
        f.read(80)
        count_bytes = f.read(4)
        if len(count_bytes) < 4:
            return SimpleMesh([], [])

        vertices = []
        triangles = []
        vert_map = {}
        record_size = 50
        chunk_size = 1000 * record_size

        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            num_in_chunk = len(chunk) // record_size
            for i in range(num_in_chunk):
                offset = i * record_size
                floats = struct.unpack_from("<9f", chunk, offset + 12)

                p1 = (floats[0], floats[1], floats[2])
                if p1 not in vert_map:
                    vert_map[p1] = len(vertices)
                    vertices.append(p1)

                p2 = (floats[3], floats[4], floats[5])
                if p2 not in vert_map:
                    vert_map[p2] = len(vertices)
                    vertices.append(p2)

                p3 = (floats[6], floats[7], floats[8])
                if p3 not in vert_map:
                    vert_map[p3] = len(vertices)
                    vertices.append(p3)

                triangles.append((vert_map[p1], vert_map[p2], vert_map[p3]))

    return SimpleMesh(vertices, triangles)


# Bambu Studio paint_color encoding for face-level filament assignment:
#   paint_color="8"  → filament slot 1 (base / extruder 1)
#   paint_color="4"  → filament slot 2 (text / extruder 2)
_PAINT_BASE = "8"
_PAINT_TEXT = "4"

_MODEL_NS = (
    'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
    'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
    'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
    'requiredextensions="p"'
)

# Files from template that we always regenerate; everything else is copied as-is.
_SKIP_FROM_TEMPLATE = {
    "3D/3dmodel.model",
    "3D/Objects/object_1.model",
    "Metadata/model_settings.config",
    "Metadata/slice_info.config",
    "Metadata/filament_sequence.json",
}


def _build_object_model(combined_vertices, base_tri_count, all_triangles, uuid_inner):
    """Builds the XML content for 3D/Objects/object_1.model."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<model unit="millimeter" xml:lang="en-US" {_MODEL_NS}>',
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
        ' <resources>',
        f'  <object id="1" p:UUID="{uuid_inner}" type="model">',
        '   <mesh>',
        '    <vertices>',
    ]
    for v in combined_vertices:
        lines.append(f'     <vertex x="{v[0]:.6f}" y="{v[1]:.6f}" z="{v[2]:.6f}"/>')
    lines.append('    </vertices>')
    lines.append('    <triangles>')
    for idx, t in enumerate(all_triangles):
        color = _PAINT_BASE if idx < base_tri_count else _PAINT_TEXT
        lines.append(f'     <triangle v1="{t[0]}" v2="{t[1]}" v3="{t[2]}" paint_color="{color}"/>')
    lines.append('    </triangles>')
    lines.extend([
        '   </mesh>',
        '  </object>',
        ' </resources>',
        ' <build/>',
        '</model>',
    ])
    return "\n".join(lines)


def _build_main_model(uuid_outer, uuid_component, uuid_build, uuid_item,
                      comp_transform, build_transform, obj_name):
    """Builds the XML content for 3D/3dmodel.model (thin wrapper referencing object_1.model)."""
    today = date.today().isoformat()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<model unit="millimeter" xml:lang="en-US" {_MODEL_NS}>',
        ' <metadata name="Application">BambuStudio-02.04.00.70</metadata>',
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
        ' <metadata name="Copyright"></metadata>',
        f' <metadata name="CreationDate">{today}</metadata>',
        ' <metadata name="Description"></metadata>',
        ' <metadata name="License"></metadata>',
        f' <metadata name="ModificationDate">{today}</metadata>',
        f' <metadata name="Title">{obj_name}</metadata>',
        ' <resources>',
        f'  <object id="2" p:UUID="{uuid_outer}" type="model">',
        '   <components>',
        (f'    <component p:path="/3D/Objects/object_1.model" objectid="1"'
         f' p:UUID="{uuid_component}" transform="{comp_transform}"/>'),
        '   </components>',
        '  </object>',
        ' </resources>',
        f' <build p:UUID="{uuid_build}">',
        (f'  <item objectid="2" p:UUID="{uuid_item}"'
         f' transform="{build_transform}" printable="1"/>'),
        ' </build>',
        '</model>',
    ]
    return "\n".join(lines)


def _build_model_settings(obj_name, total_faces, tx, ty, tz):
    """Builds Metadata/model_settings.config for a single painted object."""
    # 4×4 matrix (row-major) encoding the same transform as the component
    matrix = (f"1 0 0 {tx:.10f} "
               f"0 1 0 {ty:.10f} "
               f"0 0 1 {tz:.10f} "
               f"0 0 0 1")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="2">
    <metadata key="name" value="{obj_name}"/>
    <metadata key="extruder" value="1"/>
    <metadata face_count="{total_faces}"/>
    <part id="1" subtype="normal_part">
      <metadata key="name" value="{obj_name}"/>
      <metadata key="matrix" value="{matrix}"/>
      <metadata key="source_file" value="{obj_name}.stl"/>
      <metadata key="source_object_id" value="0"/>
      <metadata key="source_volume_id" value="0"/>
      <metadata key="source_offset_x" value="{tx:.10f}"/>
      <metadata key="source_offset_y" value="{ty:.10f}"/>
      <metadata key="source_offset_z" value="{tz:.10f}"/>
      <metadata key="extruder" value="1"/>
      <mesh_stat face_count="{total_faces}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value="Plate 1"/>
    <metadata key="locked" value="false"/>
    <metadata key="filament_map_mode" value="Auto For Flush"/>
    <metadata key="gcode_file" value=""/>
    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>
    <metadata key="thumbnail_no_light_file" value="Metadata/plate_no_light_1.png"/>
    <metadata key="top_file" value="Metadata/top_1.png"/>
    <metadata key="pick_file" value="Metadata/pick_1.png"/>
    <model_instance>
      <metadata key="object_id" value="2"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="1"/>
    </model_instance>
  </plate>
  <assemble>
  </assemble>
</config>
"""


_SLICE_INFO = """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <header>
    <header_item key="X-BBL-Client-Type" value="slicer"/>
    <header_item key="X-BBL-Client-Version" value="02.04.00.70"/>
  </header>
</config>
"""

# Bambu Lab X1/P1 series build plate centre (256×256 mm)
_PLATE_CX = 128.0
_PLATE_CY = 128.0


def create_3mf_from_stls(stl_files: List[Tuple[Path, str, str]], output_3mf: Path,
                          scad_file=None, work_dir=None, openscad_cmd=None,
                          quiet: bool = False):
    """
    Combines base + text STL files into a single Bambu-Studio-compatible 3MF
    using the paint_color face-painting approach (one mesh, colours per triangle).

    stl_files: [(path, hex_color, name), ...]
                index 0 → base  (extruder 1, paint_color="8")
                index 1 → text  (extruder 2, paint_color="4")
    """
    if len(stl_files) < 2:
        raise ValueError("Need at least two STL files: base and text.")

    base_mesh = read_stl(stl_files[0][0])
    text_mesh = read_stl(stl_files[1][0])
    obj_name = stl_files[0][2].rsplit("_", 1)[0]  # strip "_base" suffix

    # Merge vertices: base first, then text (offset indices)
    offset = len(base_mesh.vertices)
    combined_vertices = list(base_mesh.vertices) + list(text_mesh.vertices)
    base_triangles = list(base_mesh.triangles)
    text_triangles = [(v1 + offset, v2 + offset, v3 + offset)
                      for v1, v2, v3 in text_mesh.triangles]
    all_triangles = base_triangles + text_triangles
    total_faces = len(all_triangles)

    # Compute centroid of the combined mesh to centre on the build plate
    if combined_vertices:
        xs = [v[0] for v in combined_vertices]
        ys = [v[1] for v in combined_vertices]
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
    else:
        cx = cy = 0.0

    # Component transform: centres the geometry at the world origin
    tx, ty, tz = -cx, -cy, 0.0
    comp_transform = f"1 0 0 0 1 0 0 0 1 {tx:.6f} {ty:.6f} {tz:.6f}"

    # Build-item transform: places the centred object at the plate centre
    build_transform = (f"1 0 0 0 1 0 0 0 1 "
                       f"{_PLATE_CX:.5f} {_PLATE_CY:.5f} 0")

    # Unique UUIDs for every generated file
    uuid_outer = str(uuid.uuid4())
    uuid_component = str(uuid.uuid4())
    uuid_build = str(uuid.uuid4())
    uuid_item = str(uuid.uuid4())
    uuid_inner = str(uuid.uuid4())

    object_1_xml = _build_object_model(combined_vertices, len(base_triangles),
                                       all_triangles, uuid_inner)
    main_model_xml = _build_main_model(uuid_outer, uuid_component, uuid_build,
                                       uuid_item, comp_transform, build_transform,
                                       obj_name)
    model_settings_xml = _build_model_settings(obj_name, total_faces, tx, ty, tz)

    # ── Write ZIP ────────────────────────────────────────────────────────────
    template_path = Path(os.path.join(os.path.dirname(__file__), "Template.3mf"))

    with zipfile.ZipFile(output_3mf, "w", compression=zipfile.ZIP_DEFLATED) as zf:

        # 1. Copy files from template (skip those we generate ourselves)
        if template_path.exists():
            with zipfile.ZipFile(template_path, "r") as tmpl:
                for item in tmpl.namelist():
                    if item in _SKIP_FROM_TEMPLATE:
                        continue
                    if item.startswith("Metadata/") and item.endswith(".png"):
                        continue  # thumbnails handled separately below
                    zf.writestr(item, tmpl.read(item))

        # 2. Thumbnails: try to render from SCAD, fall back to template copies
        thumbnails_generated = False
        if scad_file and Path(scad_file).exists():
            try:
                from .generate_thumbnails import generate_thumbnails
                thumb_dir = Path(work_dir) / "thumbnails" if work_dir else Path(scad_file).parent / "thumbnails"
                thumb_dir.mkdir(parents=True, exist_ok=True)
                generated = generate_thumbnails(scad_file, thumb_dir, openscad_cmd, quiet)
                if generated:
                    for filename, thumb_path in generated.items():
                        if thumb_path.exists():
                            zf.write(str(thumb_path), f"Metadata/{filename}")
                    thumbnails_generated = True
            except Exception:
                pass

        if not thumbnails_generated and template_path.exists():
            with zipfile.ZipFile(template_path, "r") as tmpl:
                for item in tmpl.namelist():
                    if item.startswith("Metadata/") and item.endswith(".png"):
                        zf.writestr(item, tmpl.read(item))

        # 3. Write generated content
        zf.writestr("3D/Objects/object_1.model", object_1_xml)
        zf.writestr("3D/3dmodel.model", main_model_xml)
        zf.writestr("Metadata/model_settings.config", model_settings_xml)
        zf.writestr("Metadata/slice_info.config", _SLICE_INFO)

    return output_3mf
