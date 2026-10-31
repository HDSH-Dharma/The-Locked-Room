"""
simulasi.py
Script — transkrip satu permainan dan perbandingan agen pada banyak kasus.

  python -m scripts.simulasi            # transkrip 1 kasus + perbandingan 300 kasus (± 5 menit)
  python -m scripts.simulasi 50         # perbandingan lebih cepat dengan 50 kasus

Hasil ditulis ke folder hasil/:
  transkrip_kasus_<nomor>.md  jalannya satu permainan, termasuk isi KB dan bukti resolusi
  perbandingan.md             angka perbandingan v1 vs v2 vs baseline
  angka.json                  angka yang sama dalam bentuk data
"""
import json
import os
import sys
import time

from logic.evaluasi.perbandingan import hitung_angka, teks_perbandingan
from logic.evaluasi.transkrip import pilih_kasus_demo, transkrip
from model.folder_model import FOLDER_HASIL

# MARK: - Main

def main(n=300):
    os.makedirs(FOLDER_HASIL, exist_ok=True)
    mulai = time.perf_counter()
    demo  = pilih_kasus_demo()
    teks, h2, h1 = transkrip(demo)
    _tulis(f'transkrip_kasus_{demo:06d}.md', teks)
    print(f'transkrip kasus {demo}: v2 {h2["tipe"]}@{h2["ronde"]}, v1 {h1["tipe"]}@{h1["ronde"]}', flush=True)
    angka = hitung_angka(n)
    angka['kasus_demo'] = demo
    laporan = teks_perbandingan(n, angka, time.perf_counter() - mulai)
    _tulis('angka.json', json.dumps(angka, indent=2))
    _tulis('perbandingan.md', laporan)
    print(laporan)


# MARK: - Private Helpers

def _tulis(nama_file, isi):
    with open(os.path.join(FOLDER_HASIL, nama_file), 'w', encoding='utf-8') as f:
        f.write(isi)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
