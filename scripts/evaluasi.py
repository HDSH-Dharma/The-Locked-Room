"""
evaluasi.py
Script — tabel evaluasi dari replay semua log test mode melawan setiap Detektif AI.

  python -m scripts.evaluasi      -> hasil/evaluasi.csv (semua baris) dan hasil/evaluasi.md (tabel laporan)
"""
import os

from models.folder_model import FOLDER_HASIL
from services.evaluasi_service import baca_log, jalankan, per_pemain, ringkas, tabel_markdown, tulis_csv

# MARK: - Main

def main():
    baris = jalankan(baca_log())
    os.makedirs(FOLDER_HASIL, exist_ok=True)
    tulis_csv(baris, os.path.join(FOLDER_HASIL, 'evaluasi.csv'))
    teks = tabel_markdown(ringkas(baris), per_pemain(baris))
    with open(os.path.join(FOLDER_HASIL, 'evaluasi.md'), 'w', encoding='utf-8') as f:
        f.write(teks + '\n')
    print(teks)


if __name__ == '__main__':
    main()
