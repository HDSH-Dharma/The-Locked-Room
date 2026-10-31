"""
buat_pembagian.py
Script — membuat pembagian.json: 300 kasus playtest, 100 per pemain, 25 per lawan AI.

  python -m scripts.buat_pembagian      -> pembagian.json (jalankan sekali saja)
"""
import json

from models.folder_model import PATH_PEMBAGIAN
from services.pembagian_service import buat_pembagian

# MARK: - Main

def main():
    with open(PATH_PEMBAGIAN, 'w') as f:
        json.dump(buat_pembagian(), f, indent=4)    # format sama dengan pembagian.json yang di-commit


if __name__ == '__main__':
    main()
