"""
uji_konsistensi.py
Test — v1 (model checking) dan v2 (FOL + resolusi) harus menarik kesimpulan yang sama persis
setelah setiap bukti, dalam urutan bukti acak.

  python -m tests.uji_konsistensi [jumlah_kasus] [denah]
"""
import sys

from services.konsistensi_service import bandingkan

if __name__ == '__main__':
    bandingkan(int(sys.argv[1]) if len(sys.argv) > 1 else 300, denah=sys.argv[2] if len(sys.argv) > 2 else '9')
