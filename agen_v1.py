"""
AGEN v1 — kode awal (materi Logical Agent: Propositional Logic).

Representasi : setiap kemungkinan jawaban adalah satu model (pelaku, senjata, TKP),
               total 4 × 4 × 4 = 64 model.
Bukti        : setiap bukti ditulis tangan sebagai fungsi Python model -> True/False.
Inferensi    : model checking. KB ⊨ α jika α benar di semua model yang memenuhi KB.
               Praktiknya: buang model yang bertentangan dengan bukti.
Gerak        : BFS (pencarian buta) ke ruangan belum digeledah atau tersangka belum ditanya
               yang terdekat, dengan ACTIONS(s) dan RESULT(s, a) yang sama dengan v2
               (planning.py). Beda dengan v2: tanpa heuristik, dan tidak melewati target yang
               topik hasil mengupingnya sudah terbukti.
"""
import time
from kasus import ALL_WORLDS, S_IDS, W_IDS, TKP, R_IDS, sn, rn
from planning import State, DIPERIKSA_POLISI, bfs


def possible(models):
    return ({m.s for m in models}, {m.w for m in models}, {m.r for m in models})


def status_of(models):
    """Hasil model checking per nilai: 'gugur', 'pasti', atau 'mungkin'."""
    ps, pw, pr = possible(models)
    out = {}
    for cat, vals, pset in (('s', S_IDS, ps), ('w', W_IDS, pw), ('r', TKP, pr)):
        for v in vals:
            out[(cat, v)] = 'gugur' if v not in pset else ('pasti' if len(pset) == 1 else 'mungkin')
    return out


class AgenV1:
    nama = 'v1 (proposisional + model checking)'

    def mulai(self, case):
        self.case = case
        self.models = list(ALL_WORLDS)
        self.known = []
        self.stats = dict(update=0, waktu_ms=0.0, model_dicek=0, simpul_planner=0, rencana=0)
        self.log = []
        self.topik = {}           # hasil menguping: ('r', ruangan) / ('s', tersangka) -> [topik]

    def dengar(self, jenis, target, topik):
        """Menguping lawan: hanya topik bukti, bukan isinya. Tidak mengubah KB.
        Dicatat untuk trace saja; v1 tidak memakainya untuk memilih tujuan (proposal)."""
        self.topik[('r' if jenis == 'geledah' else 's', target)] = list(topik)

    def terbuka(self):
        ps, pw, pr = possible(self.models)
        return dict(tersangka=len(ps) > 1, senjata=len(pw) > 1, ruangan=len(pr) > 1)

    def amati(self, ids, ronde):
        entries = []
        for cid in ids:
            if cid in self.known:
                continue
            self.known.append(cid)
            clue = self.case['by_id'][cid]
            t0 = time.perf_counter()
            before = len(self.models)
            self.models = [m for m in self.models if clue['prop'](m)]
            dt = (time.perf_counter() - t0) * 1000
            self.stats['update'] += 1
            self.stats['waktu_ms'] += dt
            self.stats['model_dicek'] += before
            entries.append(dict(id=cid, sebelum=before, sesudah=len(self.models),
                                relevan=clue['relevant'], waktu_ms=dt))
        self.log.extend(entries)
        return entries

    def status(self):
        return status_of(self.models)

    def tuduhan(self):
        return self.models[0] if len(self.models) == 1 else None

    def aksi(self, pos, searched, asked, punya_tp=False):
        """BFS ke target terdekat: ruangan yang belum digeledah (kecuali Ruang Tamu, sudah
        diperiksa polisi) atau tersangka yang belum ditanya. Isi ruangan tidak diketahui
        sebelum digeledah. Teleport hanya dipakai kalau rencananya lebih pendek."""
        rooms = {r for r in R_IDS if r not in searched and r != DIPERIKSA_POLISI}
        sus = {x for x in S_IDS if x not in asked}
        if not rooms and not sus:
            return None, {}
        lokasi = self.case['loc']
        searched0, asked0 = frozenset(searched), frozenset(asked)

        def goal(st):          # goal test: satu informasi baru didapat
            return bool((st.digeledah - searched0) & rooms) or bool((st.ditanya - asked0) & sus)

        start = State(pos, searched0, asked0, False)
        plan, expanded = bfs(start, goal, lokasi)
        if punya_tp:
            plan_tp, exp_tp = bfs(start._replace(teleport=True), goal, lokasi)
            expanded += exp_tp
            if plan_tp and plan_tp[0][0] == 'teleport' and (plan is None or len(plan_tp) < len(plan)):
                plan = plan_tp
        self.stats['simpul_planner'] += expanded
        self.stats['rencana'] += 1
        if not plan:
            return None, {}
        info = dict(rencana=[f'{a.capitalize()}({sn(b) if a == "interogasi" else rn(b)})' for a, b in plan],
                    simpul=expanded)
        return plan[0], info
