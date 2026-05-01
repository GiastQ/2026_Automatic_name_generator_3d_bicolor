"""Shared utility helpers for the keychain generator.

Author: Giustino C. Miglionico
Date: 2026-05-01
License: MIT
"""

import re
import shutil
from pathlib import Path


def safe_filename(s: str) -> str:
    s = re.sub(r"\s+", "_", s.strip())
    return re.sub(r"[^a-zA-Z0-9_\-]", "", s) or "keychain"


def scad_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def find_openscad(custom_path: str | None = None) -> str | None:
    """Return the OpenSCAD executable path, or None if not found."""
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return str(p)
        raise FileNotFoundError(f"OpenSCAD not found at: {custom_path}")

    cmd = shutil.which("openscad")
    if cmd:
        return cmd

    candidates = [
        # Windows
        r"C:\Program Files\OpenSCAD\openscad.exe",
        r"C:\Program Files (x86)\OpenSCAD\openscad.exe",
        # Linux
        "/usr/bin/openscad",
        "/usr/local/bin/openscad",
        "/snap/bin/openscad",
        # macOS
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None
