"""
AGEN v1 — kode awal (materi Logical Agent: Propositional Logic).

Representasi : setiap kemungkinan jawaban adalah satu model (pelaku, senjata, TKP),
               total 4 × 4 × 4 = 64 model.
Bukti        : setiap bukti ditulis tangan sebagai fungsi Python model -> True/False.
Inferensi    : model checking. KB ⊨ α jika α benar di semua model yang memenuhi KB.
               Praktiknya: buang model yang bertentangan dengan bukti.
Gerak        : heuristik buatan sendiri, (jarak BFS + 1) / banyak bukti di ruangan.
"""
import time
from collections import deque
from kasus import ALL_WORLDS, S_IDS, W_IDS, TKP, R_IDS, neighbors, sn, wn, rn
from denah import jarak, langkah_pertama, nilai_target


def bfs_dist(start):
    dist = {start: 0}
    q = deque([start])
    while q:
        cur = q.popleft()
        for nb in neighbors(cur):
            if nb not in dist:
                dist[nb] = dist[cur] + 1
                q.append(nb)
    return dist


def bfs_path(start, goal):
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        for nb in neighbors(cur):
            if nb not in prev:
                prev[nb] = cur
                q.append(nb)
    path, cur = [], goal
    while cur != start:
        path.append(cur)
        cur = prev[cur]
    return path[::-1]


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
        self.stats = dict(update=0, waktu_ms=0.0, model_dicek=0)
        self.log = []
        self.topik = {}           # hasil menguping: ('r', ruangan) / ('s', tersangka) -> [topik]

    def dengar(self, jenis, target, topik):
        """Menguping lawan: hanya topik bukti, bukan isinya. Tidak mengubah KB."""
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
        """Heuristik (jarak + 1) / nilai target. Teleport dipakai begitu memperpendek rute."""
        d0, d1 = jarak(pos, punya_tp)
        terbuka = self.terbuka()
        cands = []
        for r in R_IDS:
            n = len(self.case['room_clues'][r])
            if n and r not in searched:
                n = nilai_target(self.topik, ('r', r), n, terbuka)
                if n:
                    cands.append((('geledah', r), r, n))
        for s in S_IDS:
            if s not in asked:
                n = nilai_target(self.topik, ('s', s), 1.2, terbuka)
                if n:
                    cands.append((('interogasi', s), self.case['loc'][s], n))
        if not cands:
            return None, {}
        cands.sort(key=lambda c: ((d1[c[1]] + 1) / c[2], d1[c[1]]))
        act, room, _ = cands[0]
        if room == pos:
            return act, dict(target=act)
        return langkah_pertama(pos, room, d1[room] < d0[room]), dict(target=act)
