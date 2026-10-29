"""
AGEN v2 — materi terbaru (Lecture 05 FOL + Reasoning and Planning).

Representasi : First Order Logic. Aturan umum ditulis SEKALI dengan kuantor (ATURAN di bawah),
               setiap bukti hanya menambah fakta, misalnya AdaAlibi(Budi) atau Kuat(Dimas).
Inferensi    : universal instantiation -> reduksi ke proposisional -> CNF -> resolusi.
               KB ⊨ α dibuktikan dengan menurunkan klausa kosong dari KB ∧ ¬α.
Relevansi    : bukti tidak relevan jika predikatnya tidak dipakai aturan mana pun
               (misalnya motif), atau sudah tersirat dari aturan (KB_aturan ⊨ bukti).
Gerak        : problem formulation ACTIONS(s), RESULT(s, a), goal test (planning.py) dan A*
               ke ruangan belum digeledah atau tersangka belum ditanya yang terdekat. Isi ruangan
               tidak diketahui sebelum digeledah, jadi semua ruangan yang belum digeledah adalah
               target, kecuali yang topik hasil mengupingnya sudah terbukti semua.
Tuduh        : hanya ada di ACTIONS(s) kalau KB berisi fakta Terbukti(x, w, r), yang hanya
               di-TELL ketika KB ⊨ Pelaku(x) ∧ Senjata(w) ∧ TKP(r).
"""
import time
from fol import (Atom, Not, And, Or, Imp, Iff, ForAll, Exists, Neq, instantiate, to_cnf, show, atom_str)
from kasus import S_IDS, W_IDS, TKP, R_IDS, C, DOMAIN, World
from resolusi import Prover
from planning import State, DIPERIKSA_POLISI, astar, heuristik
from denah import nilai_target

x, y, w, r = '?x', '?y', '?w', '?r'
P = lambda a: Atom('Pelaku', a)
S = lambda a: Atom('Senjata', a)
T = lambda a: Atom('TKP', a)

# ---------- Basis pengetahuan umum (aturan berkuantor) ----------
ATURAN = [
    ('R1', 'Pasti ada tepat satu pelaku',
     And(Exists(x, 'orang', P(x)), ForAll(x, 'orang', ForAll(y, 'orang', Imp(Neq(x, y), Not(And(P(x), P(y)))))))),
    ('R2', 'Pasti ada tepat satu senjata',
     And(Exists(w, 'senjata', S(w)), ForAll(w, 'senjata', ForAll(y, 'senjata', Imp(Neq(w, y), Not(And(S(w), S(y)))))))),
    ('R3', 'Pasti ada tepat satu TKP',
     And(Exists(r, 'ruang', T(r)), ForAll(r, 'ruang', ForAll(y, 'ruang', Imp(Neq(r, y), Not(And(T(r), T(y)))))))),
    ('R4', 'Saksi pembohong: jujur jika dan hanya jika bukan pelaku',
     ForAll(x, 'orang', Iff(Atom('Jujur', x), Not(P(x))))),
    ('R5', 'Punya alibi berarti bukan pelaku',
     ForAll(x, 'orang', Imp(Atom('AdaAlibi', x), Not(P(x))))),
    ('R6', 'Benda yang utuh bukan senjata',
     ForAll(w, 'senjata', Imp(Atom('Utuh', w), Not(S(w))))),
    ('R7', 'Ruangan yang kosong semalaman bukan TKP',
     ForAll(r, 'ruang', Imp(Atom('Kosong', r), Not(T(r))))),
    ('R8', 'Luka berdarah jika dan hanya jika senjatanya senjata berdarah',
     Iff(Atom('LukaBerdarah'), Exists(w, 'senjata', And(S(w), Atom('Berdarah', w))))),
    ('R9', 'Serpihan kayu berarti TKP berlantai kayu',
     Imp(Atom('SerpihanKayu'), Exists(r, 'ruang', And(T(r), Atom('LantaiKayu', r))))),
    ('R10', 'Noda tanah dan air berarti TKP berlantai basah',
     Imp(Atom('NodaBasah'), Exists(r, 'ruang', And(T(r), Atom('LantaiBasah', r))))),
    ('R11', 'Jasad dipindahkan jika dan hanya jika tempat ditemukan bukan TKP',
     ForAll(r, 'ruang', Imp(Atom('DitemukanDi', r), Iff(Atom('Dipindahkan'), Not(T(r)))))),
    ('R12', 'Lebam tidak sesuai posisi berarti jasad dipindahkan',
     Imp(Atom('LebamTidakSesuai'), Atom('Dipindahkan'))),
    ('R13', 'Lebam sesuai posisi berarti jasad tidak dipindahkan',
     Imp(Atom('LebamSesuai'), Not(Atom('Dipindahkan')))),
    ('R14', 'Bekas seretan berarti jasad dipindahkan',
     Imp(Atom('AdaSeretan'), Atom('Dipindahkan'))),
    ('R15', 'Seretan berasal dari TKP',
     ForAll(r, 'ruang', Imp(And(T(r), Atom('AdaSeretan')), Atom('AsalSeretan', r)))),
    ('R16', 'Kalau jasad dipindahkan, pelakunya orang yang kuat',
     ForAll(x, 'orang', Imp(And(P(x), Atom('Dipindahkan')), Atom('Kuat', x)))),
    ('R17', 'Kalau senjatanya racun, pelakunya memegang kunci lemari',
     ForAll(x, 'orang', Imp(And(P(x), S('Racun')), Atom('PegangKunci', x)))),
    ('R18', 'Jejak sepatu 43 di TKP berarti pelaku bersepatu 43',
     Imp(Atom('JejakSepatu43'), ForAll(x, 'orang', Imp(P(x), Atom('Ukuran43', x))))),
]

# Pengetahuan latar yang tetap (bukan bukti)
LATAR = [Atom('Berdarah', 'Pisau'), Atom('Berdarah', 'Vas'), Not(Atom('Berdarah', 'Racun')), Not(Atom('Berdarah', 'Tali')),
         Atom('LantaiKayu', 'Perpustakaan'), Atom('LantaiKayu', 'KamarTidur'),
         Not(Atom('LantaiKayu', 'Dapur')), Not(Atom('LantaiKayu', 'Taman')),
         Atom('LantaiBasah', 'Dapur'), Atom('LantaiBasah', 'Taman'),
         Not(Atom('LantaiBasah', 'Perpustakaan')), Not(Atom('LantaiBasah', 'KamarTidur'))]


def _predicates(f, out):
    if f[0] == 'atom':
        out.add(f[1])
    elif f[0] in ('not',):
        _predicates(f[1], out)
    elif f[0] in ('and', 'or'):
        for g in f[1]:
            _predicates(g, out)
    elif f[0] in ('imp', 'iff'):
        _predicates(f[1], out)
        _predicates(f[2], out)
    elif f[0] in ('forall', 'exists'):
        _predicates(f[3], out)
    return out


RULE_PREDICATES = set()
for _, _, _f in ATURAN:
    _predicates(_f, RULE_PREDICATES)

# Atom yang ditanyakan untuk menentukan jawaban
QUERY_LABEL = {'s': 'Pelaku', 'w': 'Senjata', 'r': 'TKP'}
QUERY_ATOMS = [('s', i, atom_str('Pelaku', (C[i],))) for i in S_IDS] \
    + [('w', i, atom_str('Senjata', (C[i],))) for i in W_IDS] \
    + [('r', i, atom_str('TKP', (C[i],))) for i in TKP]


def ground_clauses(formula, label):
    return [(c, label) for c in to_cnf(instantiate(formula, DOMAIN))]


class KB:
    """Basis pengetahuan FOL: TELL menambah formula, ASK memakai resolusi."""

    def __init__(self, found, pure=True, limit=60000):
        self.pure, self.limit = pure, limit
        self.clauses = []
        self.rule_clauses = []
        for name, _, f in ATURAN:
            self.rule_clauses += ground_clauses(f, name)
        for f in LATAR:
            self.rule_clauses += ground_clauses(f, 'latar')
        self.clauses = list(self.rule_clauses)
        # Informasi publik: tempat jasad ditemukan
        for t in TKP:
            f = Atom('DitemukanDi', C[t]) if t == found else Not(Atom('DitemukanDi', C[t]))
            self.clauses += ground_clauses(f, 'jasad ditemukan')
        self._prover = None
        self._rules_prover = None

    def tell(self, formula, label):
        new = ground_clauses(formula, label)
        self.clauses += new
        self._prover = None
        return new

    def prover(self):
        if self._prover is None:
            self._prover = Prover(self.clauses, self.limit, self.pure)
        return self._prover

    def rules_prover(self):
        if self._rules_prover is None:
            self._rules_prover = Prover(self.rule_clauses, self.limit, self.pure)
        return self._rules_prover

    def ask(self, lit):
        ok, p, empty = self.prover().entails(lit)
        return ok, p, empty

    def atoms(self):
        return {a for c, _ in self.clauses for a, _ in c}


class AgenV2:
    nama = 'v2 (FOL + resolusi + A*)'

    def __init__(self, pure=True, limit=60000):
        self.pure, self.limit = pure, limit

    def mulai(self, case):
        self.case = case
        self.kb = KB(case['found'], self.pure, self.limit)
        self.known = []
        self.state = {(cat, v): 'mungkin' for cat, v, _ in QUERY_ATOMS}
        self.stats = dict(update=0, waktu_ms=0.0, query=0, langkah_resolusi=0, langkah_max=0, batas=0,
                          simpul_planner=0, rencana=0)
        self.log = []
        self.topik = {}           # hasil menguping: ('r', ruangan) / ('s', tersangka) -> [topik]
        self.terbukti = None      # World yang sudah terbukti; diisi saat fakta Terbukti di-TELL
        self.stats.update(teleport_ditahan=0)

    def dengar(self, jenis, target, topik):
        """Menguping lawan: hanya topik bukti. Bukan fakta logika, jadi tidak di-TELL ke KB."""
        self.topik[('r' if jenis == 'geledah' else 's', target)] = list(topik)

    def terbuka(self):
        """Kategori yang belum pasti menurut KB (hasil ASK yang sudah tersimpan di state)."""
        pasti = {cat for (cat, _), st in self.state.items() if st == 'pasti'}
        return dict(tersangka='s' not in pasti, senjata='w' not in pasti, ruangan='r' not in pasti)

    @staticmethod
    def _nama(i):
        from kasus import sn
        return sn(i)

    @staticmethod
    def _ruang(i):
        from kasus import rn
        return rn(i)

    # ---- relevansi bukti ----
    def _relevansi(self, clue, clauses):
        preds = set()
        for f in clue['fol']:
            _predicates(f, preds)
        loose = sorted(preds - RULE_PREDICATES)
        if loose:
            return False, f'predikat {", ".join(loose)} tidak dipakai aturan mana pun'
        rp = self.kb.rules_prover()
        if all(rp.entails_clause(c)[0] for c, _ in clauses):
            return False, 'sudah tersirat dari aturan umum (KB_aturan ⊨ bukti)'
        return True, ''

    # ---- TELL lalu ASK ----
    def amati(self, ids, ronde):
        entries = []
        for cid in ids:
            if cid in self.known:
                continue
            self.known.append(cid)
            clue = self.case['by_id'][cid]
            t0 = time.perf_counter()
            label = f'{cid} ' + (f'kesaksian {self._nama(clue["speaker"])}' if clue['kind'] == 'kesaksian'
                                 else 'berkas polisi' if clue['kind'] == 'berkas' else f'bukti {self._ruang(clue["room"])}')
            added = []
            for f in clue['fol']:
                added += self.kb.tell(f, label)
            relevan, alasan = self._relevansi(clue, added)
            before = dict(self.state)
            steps, nq, mx = self._update_state()
            self._cek_terbukti()
            dt = (time.perf_counter() - t0) * 1000
            self.stats['update'] += 1
            self.stats['waktu_ms'] += dt
            self.stats['query'] += nq
            self.stats['langkah_resolusi'] += steps
            self.stats['langkah_max'] = max(self.stats['langkah_max'], mx)
            baru = [(k, v) for k, v in self.state.items() if before[k] != v]
            entries.append(dict(id=cid, fol=[show(f) for f in clue['fol']], klausa=len(added),
                                relevan=relevan, alasan=alasan, baru=baru, waktu_ms=dt, query=nq, langkah=steps))
        self.log.extend(entries)
        return entries

    def _update_state(self):
        total = mx = nq = 0
        for cat, v, atom in QUERY_ATOMS:
            if self.state[(cat, v)] != 'mungkin':
                continue
            ok, p, _ = self.kb.ask((atom, False))      # KB ⊨ ¬atom ?
            nq += 1
            total += p.steps
            mx = max(mx, p.steps)
            if ok is None:
                self.stats['batas'] += 1
            if ok:
                self.state[(cat, v)] = 'gugur'
                continue
            ok, p, _ = self.kb.ask((atom, True))       # KB ⊨ atom ?
            nq += 1
            total += p.steps
            mx = max(mx, p.steps)
            if ok is None:
                self.stats['batas'] += 1
            if ok:
                self.state[(cat, v)] = 'pasti'
        return total, nq, mx

    def _cek_terbukti(self):
        """Kalau KB ⊨ Pelaku(x) ∧ Senjata(w) ∧ TKP(r), TELL fakta Terbukti(x, w, r).
        Tuduh hanya ada di ACTIONS(s) kalau fakta ini ada, jadi AI tidak bisa menuduh tanpa bukti."""
        if self.terbukti:
            return
        pasti = {cat: v for (cat, v), st in self.state.items() if st == 'pasti'}
        if all(k in pasti for k in 'swr'):
            xs, ws, rs = pasti['s'], pasti['w'], pasti['r']
            self.kb.tell(Atom('Terbukti', C[xs], C[ws], C[rs]), 'inferensi: KB ⊨ jawaban')
            self.terbukti = World(xs, ws, rs)

    def status(self):
        return dict(self.state)

    def bukti(self, cat, v, positif=True):
        """Langkah resolusi untuk KB ⊨ Pelaku(v) (atau negasinya)."""
        atom = next(a for c, i, a in QUERY_ATOMS if c == cat and i == v)
        ok, p, empty = self.kb.ask((atom, positif))
        return p.proof(empty) if ok else []

    # ---- penjelasan untuk UI ----
    def trace_teks(self):
        """Reasoning trace dalam bentuk baris teks: setiap bukti yang di-TELL, penilaian
        berguna/tidak, kesimpulan baru dari ASK, lalu langkah resolusi untuk jawaban akhir."""
        nama = {'s': self._nama, 'w': lambda i: C[i], 'r': self._ruang}
        teks_st = {'pasti': 'pasti', 'gugur': 'bukan'}
        kat = {'s': 'pelaku', 'w': 'senjata', 'r': 'TKP'}
        lines = []
        for e in self.log:
            clue = self.case['by_id'][e['id']]
            tanda = 'berguna' if e['relevan'] else f"tidak berguna: {e['alasan']}"
            lines.append(f"[{e['id']}] {clue['text']}")
            lines.append(f"     TELL {'; '.join(e['fol'])}   ({tanda})")
            baru = ', '.join(f'{kat[c]} {teks_st[st]} {nama[c](v)}' for (c, v), st in e['baru'])
            lines.append(f"     ASK  {e['query']} query, {e['langkah']} langkah resolusi -> {baru or 'belum ada kesimpulan baru'}")
        if self.terbukti:
            t = self.terbukti
            lines.append('')
            lines.append(f'TELL Terbukti({C[t.s]}, {C[t.w]}, {C[t.r]})  ->  aksi Tuduh tersedia')
            for cat, v in (('s', t.s), ('w', t.w), ('r', t.r)):
                lines.append(f'Bukti resolusi KB ⊨ {QUERY_LABEL[cat]}({C[v]}):')
                for i, (a, b, hasil) in enumerate(self.bukti(cat, v), 1):
                    lines.append(f'  {i:>2}. {a}  +  {b}  =>  {hasil or "□ (klausa kosong)"}')
        return lines

    # ---- planning ----
    def tuduhan(self):
        """Tuduh(x, w, r) hanya ada di ACTIONS(s) kalau fakta Terbukti(x, w, r) sudah ada di KB."""
        return self.terbukti

    def target(self, searched, asked):
        """Ruangan dan tersangka yang layak dituju. Isi ruangan tidak diketahui sebelum
        digeledah, jadi semua ruangan yang belum digeledah ikut, kecuali Ruang Tamu (sudah
        diperiksa polisi) dan target yang topik hasil mengupingnya sudah terbukti."""
        terbuka = self.terbuka()
        rooms = {rr for rr in R_IDS if rr not in searched and rr != DIPERIKSA_POLISI
                 and nilai_target(self.topik, ('r', rr), 1, terbuka)}
        sus = {s for s in S_IDS if s not in asked and nilai_target(self.topik, ('s', s), 1, terbuka)}
        return rooms, sus

    def aksi(self, pos, searched, asked, punya_tp=False):
        rooms, sus = self.target(searched, asked)
        if not rooms and not sus:
            return None, {}
        lokasi = self.case['loc']
        searched0, asked0 = frozenset(searched), frozenset(asked)

        def goal(st):          # goal test: satu informasi baru didapat
            return bool((st.digeledah - searched0) & rooms) or bool((st.ditanya - asked0) & sus)

        h = heuristik(list(rooms) + [lokasi[s] for s in sus], goal)
        start = State(pos, searched0, asked0, False)
        plan, expanded = astar(start, goal, h, lokasi)
        if punya_tp:
            # Rencana dengan teleport hanya dipakai kalau lebih pendek; selain itu teleport disimpan.
            plan_tp, exp_tp = astar(start._replace(teleport=True), goal, h, lokasi)
            expanded += exp_tp
            if plan_tp and plan_tp[0][0] == 'teleport':
                if plan is None or len(plan_tp) < len(plan):
                    plan = plan_tp
                else:
                    self.stats['teleport_ditahan'] += 1
        self.stats['simpul_planner'] += expanded
        self.stats['rencana'] += 1
        if not plan:
            return None, {}
        info = dict(rencana=[f'{a.capitalize()}({self._ruang(b) if a in ("pindah", "teleport", "geledah") else self._nama(b)})'
                             for a, b in plan], simpul=expanded)
        return plan[0], info


def tampil_aturan():
    lines = []
    for name, ket, f in ATURAN:
        lines.append(f'{name}  {show(f)}    # {ket}')
    return '\n'.join(lines)
