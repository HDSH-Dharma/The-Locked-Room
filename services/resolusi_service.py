"""
resolusi_service.py
Service — inferensi dengan resolusi (materi Reasoning, slide 6–9).

KB ⊨ α  dibuktikan dengan menunjukkan KB ∧ ¬α kontradiksi: terus melakukan resolusi
sampai muncul klausa kosong. Kalau tidak ada klausa baru lagi, KB ⊭ α.

Strategi yang dipakai (semuanya tetap langkah resolusi biasa):
1. Resolusi unit dulu  : klausa satu literal (fakta) dipakai lebih dulu, klausa yang
                         tertutup oleh fakta dibuang (subsumption).
2. Set of support      : resolusi umum hanya dilakukan dengan klausa yang berasal dari ¬α,
                         supaya pencarian tidak melebar ke hal yang tidak ditanyakan.
3. Klausa terpendek dulu.
Setiap langkah dicatat (induk kiri, induk kanan, hasil) sehingga bukti bisa ditampilkan.
Literal dan klausa diproses dalam urutan tetap (sorted), jadi jumlah langkah resolusi sama
persis di setiap run. Tanpa ini urutan set Python berubah-ubah antar-run.
"""
import heapq
from collections import defaultdict, deque

from services.fol_service import clause_str, is_tautology

# MARK: - Error

class Batas(Exception):
    """Jumlah langkah resolusi melewati batas; query dianggap tidak terjawab (hasil None)."""


# MARK: - Prover

class Prover:
    """Prover untuk satu KB. KB dasar dipropagasi sekali; setiap query bekerja di salinannya."""

    def __init__(self, base, limit=60000, pure=True):
        """base: daftar (klausa, label asal). pure=False mematikan eliminasi literal murni
        (dipakai hanya untuk eksperimen pembanding)."""
        self.limit      = limit
        self.use_pure   = pure
        self.recs       = {}  # id -> (lits, label, parents, support)
        self.active     = set()
        self.by_lits    = {}
        self.units      = {}  # atom -> (polaritas, id)
        self.occ        = defaultdict(set)
        self.next_id    = 0
        self.steps      = 0
        new             = [self._add(lits, label, None, False) for lits, label in base]
        self.empty      = self._propagate(new)
        self.base_steps = self.steps

    # MARK: - Query

    def entails_clause(self, clause, label='¬query'):
        """Apakah KB ⊨ klausa? Tambahkan negasinya (literal-literal unit) lalu cari □."""
        if self.empty is not None:
            return True, self, self.empty
        p       = self._fork()
        neg_ids = [p._add(frozenset([(a, not pol)]), label, None, True) for a, pol in clause]
        try:
            e = p._propagate(neg_ids)
            if e is None:
                if p.use_pure:
                    p._pure()
                e = p._sos()
        except Batas:
            return None, p, None
        return e is not None, p, e

    def entails(self, lit, label=None):
        return self.entails_clause(frozenset([lit]), label or '¬query')

    # MARK: - Bukti

    def proof(self, empty_id):
        """Urutan langkah resolusi yang menghasilkan klausa kosong."""
        order, seen = [], set()

        def visit(cid):
            if cid in seen:
                return
            seen.add(cid)
            parents = self.recs[cid][2]
            if parents:
                visit(parents[0])
                visit(parents[1])
                order.append(cid)
        visit(empty_id)
        steps = []
        for cid in order:
            a, b = self.recs[cid][2]
            steps.append((self._name(a), self._name(b), clause_str(self.recs[cid][0])))
        return steps

    # MARK: - Private · Penyimpanan klausa

    def _add(self, lits, label, parents, support):
        if lits in self.by_lits:
            return self.by_lits[lits]
        cid = self.next_id
        self.next_id += 1
        self.recs[cid] = (lits, label, parents, support)
        self.by_lits[lits] = cid
        self.active.add(cid)
        for lit in sorted(lits):
            self.occ[lit].add(cid)
        return cid

    def _off(self, cid):
        if cid in self.active:
            self.active.discard(cid)
            for lit in self.recs[cid][0]:
                self.occ[lit].discard(cid)

    def _resolve(self, a, b, lits):
        self.steps += 1
        if self.steps > self.limit:
            raise Batas()
        sup = self.recs[a][3] or self.recs[b][3]
        return self._add(lits, None, (a, b), sup)

    # MARK: - Private · Resolusi unit

    def _propagate(self, ids):
        """Resolusi unit sampai tidak ada perubahan. Mengembalikan id klausa kosong, atau None."""
        antre = deque(ids)
        while antre:
            cid = antre.popleft()
            if cid not in self.active:
                continue
            lits = self.recs[cid][0]
            if not lits:
                return cid
            if len(lits) > 1 and self._tertutup_fakta(lits):
                self._off(cid)
                continue
            bertentangan = [(a, p) for a, p in sorted(lits) if a in self.units and self.units[a][0] != p]
            if bertentangan:
                antre.append(self._buang_literal_bertentangan(cid, lits, bertentangan))
            elif len(lits) == 1:
                self._catat_fakta(cid, lits, antre)
        return None

    def _tertutup_fakta(self, lits):
        """Klausa sudah pasti benar karena salah satu literalnya adalah fakta yang diketahui."""
        return any(self.units.get(a, (None,))[0] == p for a, p in lits)

    def _buang_literal_bertentangan(self, cid, lits, bertentangan):
        """Resolusikan klausa dengan setiap fakta yang bertentangan; klausa lama dinonaktifkan."""
        cur, cur_lits = cid, lits
        for a, p in bertentangan:
            cur_lits = cur_lits - {(a, p)}
            cur      = self._resolve(cur, self.units[a][1], cur_lits)
        self._off(cid)
        return cur

    def _catat_fakta(self, cid, lits, antre):
        """Klausa satu literal menjadi fakta: klausa yang memuat komplemennya diproses ulang,
        klausa lain yang memuat literal ini sudah pasti benar dan dinonaktifkan."""
        a, p = next(iter(lits))
        if a in self.units:
            return
        self.units[a] = (p, cid)
        antre.extend(sorted(self.occ[(a, not p)]))
        for other in list(self.occ[(a, p)]):
            if other != cid:
                self._off(other)

    # MARK: - Private · Salinan keadaan untuk satu query

    def _fork(self):
        p            = Prover.__new__(Prover)
        p.limit      = self.limit
        p.use_pure   = self.use_pure
        p.recs       = dict(self.recs)
        p.active     = set(self.active)
        p.by_lits    = dict(self.by_lits)
        p.units      = dict(self.units)
        p.occ        = defaultdict(set, {k: set(v) for k, v in self.occ.items() if v})
        p.next_id    = self.next_id
        p.steps      = 0
        p.empty      = self.empty
        p.base_steps = 0
        return p

    # MARK: - Private · Literal murni dan subsumption

    def _pure(self):
        """Klausa yang memuat literal murni (komplemennya tidak muncul di klausa mana pun)
        tidak mungkin ikut membentuk klausa kosong, jadi aman dibuang."""
        changed = True
        while changed:
            changed = False
            for lit, ids in list(self.occ.items()):
                if ids and not self.occ.get((lit[0], not lit[1])):
                    for cid in list(ids):
                        self._off(cid)
                    changed = True

    def _subsumed(self, r):
        """Apakah ada klausa aktif yang merupakan himpunan bagian dari r?"""
        for lit in sorted(r):
            for cid in sorted(self.occ.get(lit, ())):
                c = self.recs[cid][0]
                if len(c) <= len(r) and c <= r:
                    return cid
        return None

    def _promote(self, cid, heap):
        """Klausa KB yang menggantikan resolvent dipindah ke set of support supaya
        strategi set of support tetap lengkap (complete)."""
        lits, label, parents, sup = self.recs[cid]
        if not sup and cid in self.active:
            self.recs[cid] = (lits, label, parents, True)
            heapq.heappush(heap, (len(lits), cid))

    # MARK: - Private · Set of support

    def _sos(self):
        """Resolusi umum dengan strategi set of support, klausa terpendek dulu."""
        heap = [(len(self.recs[i][0]), i) for i in sorted(self.active) if self.recs[i][3]]
        heapq.heapify(heap)
        done = set()
        while heap:
            _, g = heapq.heappop(heap)
            if g not in self.active or g in done:
                continue
            done.add(g)
            empty = self._resolusi_dengan_pasangan(g, heap)
            if empty is not None:
                return empty
        return None

    def _resolusi_dengan_pasangan(self, g, heap):
        """Resolusikan klausa g dengan setiap klausa aktif yang memuat komplemen salah satu literalnya."""
        g_lits = self.recs[g][0]
        for lit in sorted(g_lits):
            comp = (lit[0], not lit[1])
            for d in sorted(self.occ.get(comp, ())):
                if d not in self.active or g not in self.active:
                    continue
                empty = self._coba_resolvent(g, d, (g_lits - {lit}) | (self.recs[d][0] - {comp}), heap)
                if empty is not None:
                    return empty
        return None

    def _coba_resolvent(self, g, d, r, heap):
        """Simpan resolvent r kalau membawa informasi baru. Mengembalikan id klausa kosong kalau ketemu."""
        if is_tautology(r):
            return None
        if r in self.by_lits:                  # resolvent sudah ada di KB
            self._promote(self.by_lits[r], heap)
            return None
        if self._tertutup_fakta(r):
            return None
        subsumer = self._subsumed(r)
        if subsumer is not None:               # ada klausa aktif yang lebih umum
            self._promote(subsumer, heap)
            return None
        nid = self._resolve(g, d, r)
        if not r:
            return nid
        if len(r) == 1:
            empty = self._sebarkan_fakta_baru(nid, heap)
            if empty is not None:
                return empty
        heapq.heappush(heap, (len(r), nid))
        return None

    def _sebarkan_fakta_baru(self, nid, heap):
        """Resolvent satu literal langsung disebarkan dengan resolusi unit; klausa baru yang
        lahir dari situ juga masuk set of support."""
        first = self.next_id
        empty = self._propagate([nid])
        if empty is not None:
            return empty
        for cid in range(first, self.next_id):
            if cid in self.active and self.recs[cid][3]:
                heapq.heappush(heap, (len(self.recs[cid][0]), cid))
        return None

    # MARK: - Private Helpers

    def _name(self, cid):
        lits, label, parents, _ = self.recs[cid]
        s = clause_str(lits)
        return f'{s}   [{label}]' if label else s
