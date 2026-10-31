"""
Daftar Detektif AI yang bisa dilawan, dipakai bersama oleh UI (app.py), replay, dan evaluasi.

Detektif AI baru cukup ditambahkan di sini: UI, pembagian kasus, replay, dan tabel evaluasi
langsung ikut memakainya. Kunci dict adalah nama yang tercatat di log (field ai_live).
"""
from agen_baseline import AIPolisi, DetektifPenebak
from agen_v1 import AgenV1
from agen_v2 import AgenV2

LAWAN_AI = {
    'v2': AgenV2,
    'v1': AgenV1,
    'polisi': AIPolisi,
    'penebak': lambda: DetektifPenebak(ambang=3, seed=0),
}
