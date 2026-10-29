"""
Search and planning untuk Detektif AI v2: problem formulation (Lecture Note 02) dan A*.

State        : (ruangan AI, ruangan yang sudah digeledah, tersangka yang sudah ditanya,
               masih memegang teleport). KB tidak berubah selama perencanaan, jadi tidak
               disalin ke setiap state.
ACTIONS(s)   : Pindah ke ruangan sebelah.
               Teleport serong 1-2 kotak, kalau masih memegang teleport.
               Geledah ruangan tempat AI berada, kalau belum digeledah. Ruang Tamu sudah
               diperiksa polisi (isinya berkas polisi), jadi tidak bisa digeledah.
               Interogasi tersangka di ruangan yang sama yang belum ditanya.
               Tuduh hanya kalau KB sudah berisi fakta Terbukti(x, w, r).
RESULT(s, a) : state setelah aksi a.
Goal test    : satu informasi baru didapat (target ruangan digeledah atau target tersangka ditanya).
Biaya        : 1 per aksi.
Heuristik    : h(n) = d + 1, atau max(0, d - 3) + 1 saat memegang teleport, dengan d jarak
               Manhattan ke target terdekat. +1 untuk aksi geledah/interogasi. Satu lompatan
               teleport menempuh jarak Manhattan paling jauh 4 dalam 1 aksi (hemat paling banyak
               3), jadi h tidak pernah melebihi biaya sebenarnya (admissible).

Isi ruangan baru diketahui setelah digeledah, jadi AI tidak bisa merencanakan sampai Tuduh
dari awal. AI memakai online replanning: rencanakan sampai informasi baru berikutnya,
jalankan aksi pertama, amati, perbarui KB, lalu rencanakan ulang.
"""
import heapq
from collections import deque, namedtuple

from kasus import START, POS, S_IDS, neighbors, sn, rn
from denah import serong

State = namedtuple('State', 'ruang digeledah ditanya teleport')
DIPERIKSA_POLISI = START


def actions(s, lokasi, terbukti=None):
    """ACTIONS(s). lokasi: {tersangka: ruangan}. terbukti: World dari fakta Terbukti(x, w, r) atau None.
    A* tidak pernah memberi terbukti: begitu fakta itu ada, agen langsung menuduh tanpa merencanakan."""
    acts = [('tuduh', terbukti)] if terbukti else []
    acts += [('pindah', r) for r in neighbors(s.ruang)]
    if s.teleport:
        acts += [('teleport', r) for r in serong(s.ruang)]
    if s.ruang != DIPERIKSA_POLISI and s.ruang not in s.digeledah:
        acts.append(('geledah', s.ruang))
    acts += [('interogasi', x) for x in S_IDS if lokasi[x] == s.ruang and x not in s.ditanya]
    return acts


def result(s, a):
    """RESULT(s, a). Tuduh mengakhiri permainan, jadi tidak pernah dikembangkan oleh A*."""
    jenis, arg = a
    if jenis == 'pindah':
        return s._replace(ruang=arg)
    if jenis == 'teleport':
        return s._replace(ruang=arg, teleport=False)
    if jenis == 'geledah':
        return s._replace(digeledah=s.digeledah | {arg})
    if jenis == 'interogasi':
        return s._replace(ditanya=s.ditanya | {arg})
    raise ValueError(f'aksi {jenis} tidak punya state lanjutan')


def manhattan(a, b):
    (r1, c1), (r2, c2) = POS[a], POS[b]
    return abs(r1 - r2) + abs(c1 - c2)


def heuristik(tujuan, goal):
    """h(n) untuk A*. tujuan: ruangan target (ruangan yang mau digeledah dan ruangan tempat
    tersangka target berada)."""
    def h(s):
        if goal(s):
            return 0
        d = min(manhattan(s.ruang, r) for r in tujuan)
        return max(0, d - 3) + 1 if s.teleport else d + 1
    return h


def _jejak(parent, s):
    plan = []
    while parent[s]:
        s, a = parent[s]
        plan.append(a)
    return plan[::-1]


def astar(start, goal, h, lokasi):
    """A*: f(n) = g(n) + h(n). Goal test saat node diambil dari frontier, jadi rencana
    pertama yang ditemukan adalah yang terpendek. Mengembalikan (rencana, node diekspansi)."""
    frontier = [(h(start), 0, 0, start)]
    parent, best_g, tie, expanded = {start: None}, {start: 0}, 0, 0
    while frontier:
        _, neg_g, _, s = heapq.heappop(frontier)
        g = -neg_g
        if g > best_g[s]:
            continue
        if goal(s):
            return _jejak(parent, s), expanded
        expanded += 1
        for a in actions(s, lokasi):
            t = result(s, a)
            if t not in best_g or g + 1 < best_g[t]:
                best_g[t], parent[t] = g + 1, (s, a)
                tie += 1
                heapq.heappush(frontier, (g + 1 + h(t), -(g + 1), tie, t))
    return None, expanded


def bfs(start, goal, lokasi):
    """Pembanding untuk A* (uji_planning.py): breadth-first search dengan aksi yang sama."""
    if goal(start):
        return [], 0
    parent, q, expanded = {start: None}, deque([start]), 0
    while q:
        s = q.popleft()
        expanded += 1
        for a in actions(s, lokasi):
            t = result(s, a)
            if t in parent:
                continue
            parent[t] = (s, a)
            if goal(t):
                return _jejak(parent, t), expanded
            q.append(t)
    return None, expanded


def goal_info_baru(searched, asked, rooms, sus):
    """Goal test: satu informasi baru didapat, yaitu salah satu ruangan target sudah
    digeledah atau salah satu tersangka target sudah ditanya."""
    searched0, asked0 = frozenset(searched), frozenset(asked)

    def goal(s):
        return bool((s.digeledah - searched0) & rooms) or bool((s.ditanya - asked0) & sus)
    return goal


def rencanakan(pos, searched, asked, target, lokasi, *, punya_tp=False, algoritma='astar'):
    """Rencana terpendek dari posisi AI ke informasi baru berikutnya (dipakai v1 dan v2).

    target : (ruangan target, tersangka target). algoritma: 'astar' (v2) atau 'bfs' (v1).
    Teleport hanya dipakai kalau rencana dengan teleport lebih pendek; selain itu disimpan.
    Mengembalikan (rencana, node diekspansi, teleport_ditahan)."""
    rooms, sus = target
    goal = goal_info_baru(searched, asked, rooms, sus)
    h = heuristik(list(rooms) + [lokasi[x] for x in sus], goal)

    def cari(s):
        return astar(s, goal, h, lokasi) if algoritma == 'astar' else bfs(s, goal, lokasi)

    start = State(pos, frozenset(searched), frozenset(asked), False)
    plan, expanded = cari(start)
    ditahan = False
    if punya_tp:
        plan_tp, exp_tp = cari(start._replace(teleport=True))
        expanded += exp_tp
        if plan_tp and plan_tp[0][0] == 'teleport':
            if plan is None or len(plan_tp) < len(plan):
                plan = plan_tp
            else:
                ditahan = True
    return plan, expanded, ditahan


def teks_rencana(plan):
    """Rencana sebagai teks untuk trace, misalnya ['Pindah(Dapur)', 'Geledah(Dapur)']."""
    return [f'{a.capitalize()}({sn(b) if a == "interogasi" else rn(b)})' for a, b in plan]


def tampil_formulasi():
    """Teks problem formulation untuk lampiran laporan (simulasi.py)."""
    return '\n'.join([
        'State      : (ruangan AI, ruangan sudah digeledah, tersangka sudah ditanya, memegang teleport)',
        'ACTIONS(s) : Pindah(r)      r bersebelahan dengan ruangan AI',
        '             Teleport(r)    r serong 1-2 kotak, hanya kalau memegang teleport',
        '             Geledah(r)     r = ruangan AI, belum digeledah, bukan Ruang Tamu (sudah diperiksa polisi)',
        '             Interogasi(x)  x di ruangan AI dan belum ditanya',
        '             Tuduh(x,w,r)   hanya kalau KB berisi Terbukti(x, w, r)',
        'RESULT     : Pindah/Teleport mengganti ruangan AI (Teleport juga melepas teleport);',
        '             Geledah/Interogasi menambah ruangan/tersangka ke himpunan yang sudah diperiksa',
        'Goal test  : satu informasi baru didapat dari target yang topiknya belum terbukti',
        'Biaya      : 1 per aksi',
        'Heuristik  : h = d + 1, atau max(0, d - 3) + 1 saat memegang teleport (d = jarak Manhattan)',
    ])
