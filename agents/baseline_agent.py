"""
baseline_agent.py
Agent — Detektif AI pembanding (baseline) untuk evaluasi.

- AIPolisi        : langsung menuduh orang yang ditangkap dan ruangan tempat jasad ditemukan,
                    tanpa penalaran.
- DetektifPenebak : penalaran v1, tapi berani menuduh begitu sisa kemungkinan <= 3
                    (menebak salah satunya). Lebih cepat, tapi bisa salah tangkap.
- AIDiam          : lawan kosong, untuk mengukur apakah tim bisa selesai dalam 7 ronde.
"""
import random

from agents.kontrak_agent import DetektifAI
from agents.v1_agent import AgenV1
from models.rumah_model import W_IDS, World

# MARK: - Polisi

class AIPolisi(DetektifAI):
    """Baseline polisi: langsung menuduh orang yang ditangkap dan ruangan tempat jasad
    ditemukan, tanpa penalaran. Senjata dipilih acak, tapi selalu sama untuk kasus yang sama."""
    nama = 'polisi'

    def mulai(self, case):
        super().mulai(case)
        senjata      = random.Random(case['seed']).choice(W_IDS)
        self.jawaban = World(case['arrested'], senjata, case['found'])
        self.log     = []

    def tuduhan(self):
        return self.jawaban


# MARK: - Penebak

class DetektifPenebak(AgenV1):
    nama = 'penebak (v1, menuduh saat sisa ≤ 3)'

    def __init__(self, ambang=3, seed=0):
        self.ambang, self.rng = ambang, random.Random(seed)

    def tuduhan(self):
        if len(self.models) <= self.ambang:
            return self.rng.choice(self.models)
        return None


# MARK: - Tanpa lawan

class AIDiam(DetektifAI):
    nama = 'tanpa lawan'
