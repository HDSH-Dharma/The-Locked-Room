"""
v1_agent.py
Agent — Detektif AI v1: baseline dari materi Logical Agent (Propositional Logic).

Representasi : setiap kemungkinan jawaban adalah satu model (pelaku, senjata, TKP),
               total 4 × 4 × 4 = 64 model.
Bukti        : setiap bukti ditulis tangan sebagai fungsi Python model -> True/False.
Inferensi    : model checking. KB ⊨ α jika α benar di semua model yang memenuhi KB;
               praktiknya, model yang bertentangan dengan bukti dibuang.
Gerak        : BFS (pencarian buta) ke ruangan belum digeledah atau tersangka belum ditanya
               yang terdekat, dengan ACTIONS(s) dan RESULT(s, a) yang sama dengan v2
               (planning_service). Beda dengan v2: tanpa heuristik, dan tidak melewati target
               yang topik hasil mengupingnya sudah terbukti.
"""
import time

from agents.kontrak_agent import DetektifAI
from agents.mixin_agent import PemeriksaModel, PengingatTopik, PerencanaLangkah, kemungkinan
from models.planning_model import DIPERIKSA_POLISI
from models.rumah_model import R_IDS, S_IDS, TKP, W_IDS

# MARK: - Status jawaban

def status_model(models):
    """Hasil model checking per nilai jawaban: 'gugur', 'pasti', atau 'mungkin'."""
    status = {}
    pelaku, senjata, tkp = kemungkinan(models)
    for kategori, nilai_semua, mungkin in (('s', S_IDS, pelaku), ('w', W_IDS, senjata), ('r', TKP, tkp)):
        for nilai in nilai_semua:
            if nilai not in mungkin:
                status[(kategori, nilai)] = 'gugur'
            else:
                status[(kategori, nilai)] = 'pasti' if len(mungkin) == 1 else 'mungkin'
    return status


# MARK: - Agen

class AgenV1(PengingatTopik, PemeriksaModel, PerencanaLangkah, DetektifAI):
    nama      = 'v1 (proposisional + model checking)'
    ALGORITMA = 'bfs'

    def mulai(self, case):
        super().mulai(case)
        self._mulai_model()
        self._lupakan_topik()      # dicatat, tapi v1 tidak memakainya untuk memilih tujuan
        self.known = []
        self.stats = dict(update=0, waktu_ms=0.0, model_dicek=0, simpul_planner=0, rencana=0,
                          teleport_ditahan=0)
        self.log = []

    # MARK: - Penalaran

    def amati(self, ids, ronde):
        entries = [self._amati_satu(cid) for cid in ids if cid not in self.known]
        self.log.extend(entries)
        return entries

    def status(self):
        return status_model(self.models)

    def tuduhan(self):
        return self.models[0] if len(self.models) == 1 else None

    # MARK: - Gerak

    def target(self, searched, asked):
        """Semua ruangan yang belum digeledah (kecuali Ruang Tamu, sudah diperiksa polisi) dan
        semua tersangka yang belum ditanya. Isi ruangan tidak diketahui sebelum digeledah."""
        rooms     = {r for r in R_IDS if r not in searched and r != DIPERIKSA_POLISI}
        tersangka = {x for x in S_IDS if x not in asked}
        return rooms, tersangka

    # MARK: - Private Helpers

    def _amati_satu(self, cid):
        self.known.append(cid)
        clue    = self.case['by_id'][cid]
        mulai   = time.perf_counter()
        sebelum = len(self.models)
        self._saring(clue)
        waktu_ms = (time.perf_counter() - mulai) * 1000
        self._catat_statistik(sebelum, waktu_ms)
        return dict(id=cid, sebelum=sebelum, sesudah=len(self.models), relevan=clue['relevant'], waktu_ms=waktu_ms)

    def _catat_statistik(self, model_dicek, waktu_ms):
        self.stats['update'] += 1
        self.stats['waktu_ms'] += waktu_ms
        self.stats['model_dicek'] += model_dicek
