"""Automatic 3D bi-color keychain generator batch entry point.

Author: Giustino C. Miglionico
Date: 2026-05-01
License: MIT
"""
from src.main import process_csv

if __name__ == "__main__":
    print("=" * 60)
    print("GENERATORE PORTACHIAVI - BATCH 3MF")
    print("=" * 60)
    process_csv("names.csv", output_dir="output", export_3mf=True)
    print("\n" + "=" * 60)
    print("COMPLETATO! File disponibili in 'output/'")
    print("=" * 60)
