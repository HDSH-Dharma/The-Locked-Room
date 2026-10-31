"""
agen_v2.py
Logic — Detektif AI v2: materi terbaru (Lecture 05 FOL + Reasoning and Planning).

Representasi : First Order Logic. Aturan umum ditulis SEKALI dengan kuantor (aturan_model.ATURAN),
               setiap bukti hanya menambah fakta, misalnya AdaAlibi(Budi) atau Kuat(Dimas).
Inferensi    : universal instantiation -> reduksi ke proposisional -> CNF -> resolusi (kb).
               KB ⊨ α dibuktikan dengan menurunkan klausa kosong dari KB ∧ ¬α.
Relevansi    : bukti tidak relevan jika predikatnya tidak dipakai aturan mana pun
               (misalnya motif), atau sudah tersirat dari aturan (KB_aturan ⊨ bukti).
Gerak        : problem formulation ACTIONS(s), RESULT(s, a), goal test (planning) dan A*
               ke ruangan belum digeledah atau tersangka belum ditanya yang terdekat. Isi ruangan
               tidak diketahui sebelum digeledah, jadi semua ruangan yang belum digeledah adalah
               target, kecuali yang topik hasil mengupingnya sudah terbukti semua.
Tuduh        : hanya ada di ACTIONS(s) kalau KB berisi fakta Terbukti(x, w, r), yang hanya
               di-TELL ketika KB ⊨ Pelaku(x) ∧ Senjata(w) ∧ TKP(r).
"""
import time

from logic.agen.kontrak import DetektifAI
from logic.agen.mixin import PengingatTopik, PerencanaLangkah
from logic.kasus.rumah import rn, sn
from logic.kasus.topik import kunci_topik, nilai_target
from logic.penalaran.fol import show
from logic.penalaran.kb import KB, QUERY_ATOMS, RULE_PREDICATES, predikat
from model.aturan_model import QUERY_LABEL
from model.fol_model import Atom
from model.planning_model import DIPERIKSA_POLISI
from model.rumah_model import R_IDS, S_IDS, C, World

# MARK: - Agen

class AgenV2(PengingatTopik, PerencanaLangkah, DetektifAI):
    nama      = 'v2 (FOL + resolusi + A*)'
    ALGORITMA = 'astar'

    def __init__(self, pure=True, limit=60000):
        self.pure, self.limit = pure, limit

    def mulai(self, case):
        super().mulai(case)
        self._lupakan_topik()
        self.kb    = KB(case['found'], self.pure, self.limit)
        self.known = []
        self.state = {(kategori, nilai): 'mungkin' for kategori, nilai, _ in QUERY_ATOMS}
        self.stats = dict(update=0, waktu_ms=0.0, query=0, langkah_resolusi=0, langkah_max=0, batas=0,
                          simpul_planner=0, rencana=0, teleport_ditahan=0)
        self.log      = []
        self.terbukti = None  # World yang sudah terbukti; diisi saat fakta Terbukti di-TELL

    # MARK: - TELL lalu ASK

    def amati(self, ids, ronde):
        entries = [self._amati_satu(cid) for cid in ids if cid not in self.known]
        self.log.extend(entries)
        return entries

    def status(self):
        return dict(self.state)

    def terbuka(self):
        """Kategori yang belum pasti menurut KB (hasil ASK yang sudah tersimpan di state)."""
        pasti = {kategori for (kategori, _), st in self.state.items() if st == 'pasti'}
        return dict(tersangka='s' not in pasti, senjata='w' not in pasti, ruangan='r' not in pasti)

    def bukti(self, kategori, nilai, positif=True):
        """Langkah resolusi untuk KB ⊨ Pelaku(nilai) (atau negasinya)."""
        atom = next(a for k, i, a in QUERY_ATOMS if k == kategori and i == nilai)
        ok, prover, empty = self.kb.ask((atom, positif))
        return prover.proof(empty) if ok else []

    # MARK: - Penjelasan untuk UI

    def trace_teks(self):
        """Reasoning trace dalam bentuk baris teks: setiap bukti yang di-TELL, penilaian
        berguna/tidak, kesimpulan baru dari ASK, lalu langkah resolusi untuk jawaban akhir."""
        lines = []
        for entry in self.log:
            lines += self._trace_bukti(entry)
        if self.terbukti:
            lines += self._trace_jawaban()
        return lines

    # MARK: - Gerak

    def tuduhan(self):
        """Tuduh(x, w, r) hanya ada di ACTIONS(s) kalau fakta Terbukti(x, w, r) sudah ada di KB."""
        return self.terbukti

    def target(self, searched, asked):
        """Ruangan dan tersangka yang layak dituju. Isi ruangan tidak diketahui sebelum
        digeledah, jadi semua ruangan yang belum digeledah ikut, kecuali Ruang Tamu (sudah
        diperiksa polisi) dan target yang topik hasil mengupingnya sudah terbukti."""
        terbuka = self.terbuka()
        rooms = {ruang for ruang in R_IDS if ruang not in searched and ruang != DIPERIKSA_POLISI
                 and nilai_target(self.topik, kunci_topik('geledah', ruang), 1, terbuka)}
        tersangka = {x for x in S_IDS if x not in asked
                     and nilai_target(self.topik, kunci_topik('interogasi', x), 1, terbuka)}
        return rooms, tersangka

    # MARK: - Private · Penalaran

    def _amati_satu(self, cid):
        self.known.append(cid)
        clue  = self.case['by_id'][cid]
        mulai = time.perf_counter()
        added = self._tell(clue)
        relevan, alasan = self._relevansi(clue, added)
        sebelum = dict(self.state)
        langkah, n_query, langkah_max = self._perbarui_status()
        self._cek_terbukti()
        waktu_ms = (time.perf_counter() - mulai) * 1000
        self._catat_statistik(waktu_ms, n_query, langkah, langkah_max)
        baru = [(k, v) for k, v in self.state.items() if sebelum[k] != v]
        return dict(id=cid, fol=[show(f) for f in clue['fol']], klausa=len(added), relevan=relevan, alasan=alasan,
                    baru=baru, waktu_ms=waktu_ms, query=n_query, langkah=langkah)

    def _tell(self, clue):
        """TELL setiap fakta FOL dari bukti. Mengembalikan klausa yang ditambahkan ke KB."""
        label = f'{clue["id"]} {_sumber_bukti(clue)}'
        added = []
        for f in clue['fol']:
            added += self.kb.tell(f, label)
        return added

    def _relevansi(self, clue, clauses):
        """Bukti tidak berguna kalau predikatnya tidak dipakai aturan mana pun, atau kalau
        semua klausanya sudah tersirat dari aturan umum. Mengembalikan (relevan, alasan)."""
        preds = set()
        for f in clue['fol']:
            predikat(f, preds)
        loose = sorted(preds - RULE_PREDICATES)
        if loose:
            return False, f'predikat {", ".join(loose)} tidak dipakai aturan mana pun'
        rules_prover = self.kb.rules_prover()
        if all(rules_prover.entails_clause(c)[0] for c, _ in clauses):
            return False, 'sudah tersirat dari aturan umum (KB_aturan ⊨ bukti)'
        return True, ''

    def _perbarui_status(self):
        """ASK setiap atom jawaban yang belum pasti: KB ⊨ ¬atom berarti gugur, KB ⊨ atom berarti
        pasti. Mengembalikan (total langkah resolusi, jumlah query, langkah terbanyak satu query)."""
        langkah = []
        for kategori, nilai, atom in QUERY_ATOMS:
            if self.state[(kategori, nilai)] != 'mungkin':
                continue
            if self._tanya(atom, False, langkah):
                self.state[(kategori, nilai)] = 'gugur'
            elif self._tanya(atom, True, langkah):
                self.state[(kategori, nilai)] = 'pasti'
        return sum(langkah), len(langkah), max(langkah, default=0)

    def _tanya(self, atom, positif, langkah):
        """Satu query resolusi. Jumlah langkahnya ditambahkan ke daftar langkah."""
        ok, prover, _ = self.kb.ask((atom, positif))
        langkah.append(prover.steps)
        if ok is None:
            self.stats['batas'] += 1
        return ok

    def _cek_terbukti(self):
        """Kalau KB ⊨ Pelaku(x) ∧ Senjata(w) ∧ TKP(r), TELL fakta Terbukti(x, w, r).
        Tuduh hanya ada di ACTIONS(s) kalau fakta ini ada, jadi AI tidak bisa menuduh tanpa bukti."""
        if self.terbukti:
            return
        pasti = {kategori: nilai for (kategori, nilai), st in self.state.items() if st == 'pasti'}
        if all(k in pasti for k in 'swr'):
            pelaku, senjata, tkp = pasti['s'], pasti['w'], pasti['r']
            self.kb.tell(Atom('Terbukti', C[pelaku], C[senjata], C[tkp]), 'inferensi: KB ⊨ jawaban')
            self.terbukti = World(pelaku, senjata, tkp)

    def _catat_statistik(self, waktu_ms, n_query, langkah, langkah_max):
        self.stats['update'] += 1
        self.stats['waktu_ms'] += waktu_ms
        self.stats['query'] += n_query
        self.stats['langkah_resolusi'] += langkah
        self.stats['langkah_max'] = max(self.stats['langkah_max'], langkah_max)

    # MARK: - Private · Trace

    def _trace_bukti(self, entry):
        clue  = self.case['by_id'][entry['id']]
        tanda = 'berguna' if entry['relevan'] else f"tidak berguna: {entry['alasan']}"
        baru  = ', '.join(f'{_KATEGORI[k]} {_STATUS[st]} {_NAMA[k](v)}' for (k, v), st in entry['baru'])
        return [f"[{entry['id']}] {clue['text']}",
                f"     TELL {'; '.join(entry['fol'])}   ({tanda})",
                f"     ASK  {entry['query']} query, {entry['langkah']} langkah resolusi -> {baru or 'belum ada kesimpulan baru'}"]

    def _trace_jawaban(self):
        t     = self.terbukti
        lines = ['', f'TELL Terbukti({C[t.s]}, {C[t.w]}, {C[t.r]})  ->  aksi Tuduh tersedia']
        for kategori, nilai in (('s', t.s), ('w', t.w), ('r', t.r)):
            lines.append(f'Bukti resolusi KB ⊨ {QUERY_LABEL[kategori]}({C[nilai]}):')
            for i, (a, b, hasil) in enumerate(self.bukti(kategori, nilai), 1):
                lines.append(f'  {i:>2}. {a}  +  {b}  =>  {hasil or "□ (klausa kosong)"}')
        return lines


# MARK: - Private Helpers

def _sumber_bukti(clue):
    """Asal bukti untuk label klausa di KB, misalnya 'kesaksian Bu Sari' atau 'bukti Dapur'."""
    if clue['kind'] == 'kesaksian':
        return f'kesaksian {sn(clue["speaker"])}'
    if clue['kind'] == 'berkas':
        return 'berkas polisi'
    return f'bukti {rn(clue["room"])}'


_NAMA     = {'s': sn, 'w': lambda i: C[i], 'r': rn}
_KATEGORI = {'s': 'pelaku', 'w': 'senjata', 'r': 'TKP'}
_STATUS   = {'pasti': 'pasti', 'gugur': 'bukan'}
