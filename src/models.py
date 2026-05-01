"""Data models for the keychain generator.

Author: Giustino C. Miglionico
Date: 2026-05-01
License: MIT
"""

from dataclasses import dataclass


@dataclass
class KeychainParams:
    name: str = "Andrea"
    font: str = "Chewy"

    # Colors (hex) — mapped to extruder 1 and 2 in Bambu Studio
    base_color: str = "#0000FF"
    text_color: str = "#FF8800"

    # Geometry (mm)
    text_height: float = 12
    base_thickness: float = 2
    text_thickness: float = 1
    offset: float = 2.3

    # Keyring
    ring_outer_dia: float = 6
    ring_inner_dia: float = 3
    ring_x: float = -2
    ring_y: float = 6
