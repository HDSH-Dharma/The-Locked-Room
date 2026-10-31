"""
planning_service.py
Service — search and planning Detektif AI: problem formulation (Lecture Note 02), A* (v2), dan BFS (v1).

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
from collections import deque

from models.planning_model import DIPERIKSA_POLISI, State
from models.rumah_model import POS, S_IDS
from services.denah_service import serong
from services.rumah_service import neighbors

# MARK: - ACTIONS dan RESULT

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


# MARK: - Heuristik

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


# MARK: - Pencarian

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
            child = result(s, a)
            if child not in best_g or g + 1 < best_g[child]:
                best_g[child], parent[child] = g + 1, (s, a)
                tie += 1
                heapq.heappush(frontier, (g + 1 + h(child), -(g + 1), tie, child))
    return None, expanded


def bfs(start, goal, lokasi):
    """Breadth-first search dengan ACTIONS dan RESULT yang sama: gerak v1, dan pembanding A* di tests/uji_planning.py."""
    if goal(start):
        return [], 0
    parent, frontier, expanded = {start: None}, deque([start]), 0
    while frontier:
        s = frontier.popleft()
        expanded += 1
        for a in actions(s, lokasi):
            child = result(s, a)
            if child in parent:
                continue
            parent[child] = (s, a)
            if goal(child):
                return _jejak(parent, child), expanded
            frontier.append(child)
    return None, expanded


# MARK: - Goal test dan rencana

def goal_info_baru(searched, asked, ruangan_target, tersangka_target):
    """Goal test: satu informasi baru didapat, yaitu salah satu ruangan target sudah
    digeledah atau salah satu tersangka target sudah ditanya."""
    sudah_digeledah, sudah_ditanya = frozenset(searched), frozenset(asked)

    def goal(s):
        return bool((s.digeledah - sudah_digeledah) & ruangan_target) \
            or bool((s.ditanya - sudah_ditanya) & tersangka_target)
    return goal


def rencanakan(pos, searched, asked, target, lokasi, *, punya_tp=False, algoritma='astar'):
    """Rencana terpendek dari posisi AI ke informasi baru berikutnya (dipakai v1 dan v2).

    target : (ruangan target, tersangka target). algoritma: 'astar' (v2) atau 'bfs' (v1).
    Teleport hanya dipakai kalau rencana dengan teleport lebih pendek; selain itu disimpan.
    Mengembalikan (rencana, node diekspansi, teleport_ditahan)."""
    ruangan_target, tersangka_target = target
    goal = goal_info_baru(searched, asked, ruangan_target, tersangka_target)
    h    = heuristik(list(ruangan_target) + [lokasi[x] for x in tersangka_target], goal)

    def cari(start):
        return astar(start, goal, h, lokasi) if algoritma == 'astar' else bfs(start, goal, lokasi)

    start = State(pos, frozenset(searched), frozenset(asked), False)
    plan, expanded = cari(start)
    if not punya_tp:
        return plan, expanded, False
    plan_tp, expanded_tp = cari(start._replace(teleport=True))
    plan, ditahan = _pilih_rencana(plan, plan_tp)
    return plan, expanded + expanded_tp, ditahan


# MARK: - Private Helpers

def _jejak(parent, s):
    plan = []
    while parent[s]:
        s, a = parent[s]
        plan.append(a)
    return plan[::-1]


def _pilih_rencana(tanpa_teleport, dengan_teleport):
    """Rencana dengan teleport dipakai hanya kalau aksi pertamanya teleport dan rencananya
    lebih pendek. Mengembalikan (rencana terpilih, teleport ditahan untuk nanti)."""
    if not dengan_teleport or dengan_teleport[0][0] != 'teleport':
        return tanpa_teleport, False
    if tanpa_teleport is None or len(dengan_teleport) < len(tanpa_teleport):
        return dengan_teleport, False
    return tanpa_teleport, True
