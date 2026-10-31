"""
daftar.py
Logic — daftar Detektif AI yang bisa dilawan, dipakai bersama oleh UI, replay, dan evaluasi.

Detektif AI baru cukup ditambahkan di sini: UI, pembagian kasus, replay, dan tabel evaluasi
langsung ikut memakainya. Kunci dict adalah nama yang tercatat di log (field ai_live).
"""
from logic.agen.agen_v1 import AgenV1
from logic.agen.agen_v2 import AgenV2
from logic.agen.baseline import AIPolisi, DetektifPenebak

# MARK: - Daftar lawan

LAWAN_AI = {
    'v2': AgenV2,
    'v1': AgenV1,
    'polisi': AIPolisi,
    'penebak': lambda: DetektifPenebak(ambang=3, seed=0),
}
