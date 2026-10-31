"""
daftar_agent.py
Agent — daftar Detektif AI yang bisa dilawan, dipakai bersama oleh UI, replay, dan evaluasi.

Detektif AI baru cukup ditambahkan di sini: UI, pembagian kasus, replay, dan tabel evaluasi
langsung ikut memakainya. Kunci dict adalah nama yang tercatat di log (field ai_live).
"""
from agents.baseline_agent import AIPolisi, DetektifPenebak
from agents.v1_agent import AgenV1
from agents.v2_agent import AgenV2

# MARK: - Daftar lawan

LAWAN_AI = {
    'v2': AgenV2,
    'v1': AgenV1,
    'polisi': AIPolisi,
    'penebak': lambda: DetektifPenebak(ambang=3, seed=0),
}
