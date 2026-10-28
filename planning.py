"""
Classical planning ala PDDL untuk Detektif AI v2 (materi Reasoning, slide 10–12).

State   : konjungsi fluent ground, misalnya Di(AI, Dapur) ∧ Digeledah(Gudang)
Aksi    : skema dengan PRECOND dan EFFECT (add/delete list)
Planner : forward state-space search. BFS dipakai sekarang; A* (f(n) = g(n) + h(n)) sudah
          tersedia di Planner.astar dan akan dipakai v2 setelah heuristic-nya dipasang.

Isi bukti baru diketahui setelah aksi dijalankan, jadi planner tidak bisa merencanakan
sampai "tuduh" dari awal. Agen memakai online replanning: rencanakan sampai mendapat
informasi baru, jalankan satu aksi, amati, perbarui KB, lalu rencanakan ulang.
"""
import heapq
from collections import deque
from itertools import product


class Schema:
    def __init__(self, name, params, pre=(), pre_not=(), add=(), dele=(), check=None):
        self.name, self.params = name, params
        self.pre, self.pre_not, self.add, self.dele = pre, pre_not, add, dele
        self.check = check          # syarat tambahan dari penalaran (KB ⊨ ...)

    def show(self):
        args = ', '.join(v for v, _ in self.params)
        fmt = lambda fs: ' ∧ '.join(_fmt(f) for f in fs) or '-'
        pre = fmt(self.pre)
        if self.pre_not:
            pre += ' ∧ ' + ' ∧ '.join('¬' + _fmt(f) for f in self.pre_not)
        lines = [f'Action({self.name}({args})',
                 f'  PRECOND: {pre}' + (f' ∧ {self.check}' if self.check else ''),
                 f'  EFFECT:  ' + ' ∧ '.join([_fmt(f) for f in self.add] + ['¬' + _fmt(f) for f in self.dele]) + ')']
        return '\n'.join(lines)


def _fmt(f):
    return f'{f[0]}({", ".join(f[1:])})'


def _bind(tpl, env):
    return tuple(env.get(x, x) for x in tpl)


SCHEMAS = [
    Schema('Interogasi', [('?x', 'orang'), ('?r', 'ruang')],
           pre=[('Di', 'AI', '?r'), ('Lokasi', '?x', '?r')], pre_not=[('Ditanya', '?x')],
           add=[('Ditanya', '?x')]),
    Schema('Geledah', [('?r', 'ruang')],
           pre=[('Di', 'AI', '?r'), ('AdaBukti', '?r')], pre_not=[('Digeledah', '?r')],
           add=[('Digeledah', '?r')]),
    Schema('Pindah', [('?a', 'ruang'), ('?b', 'ruang')],
           pre=[('Di', 'AI', '?a'), ('Bersebelahan', '?a', '?b')],
           add=[('Di', 'AI', '?b')], dele=[('Di', 'AI', '?a')]),
    Schema('Teleport', [('?a', 'ruang'), ('?b', 'ruang')],
           pre=[('Di', 'AI', '?a'), ('Punya', 'AI', 'Teleport'), ('Serong', '?a', '?b')],
           add=[('Di', 'AI', '?b')], dele=[('Di', 'AI', '?a'), ('Punya', 'AI', 'Teleport')]),
]
STATIC_PRED = ('Bersebelahan', 'Lokasi', 'AdaBukti', 'Serong')
# Fakta Terbukti(x, w, r) hanya ditambahkan oleh mesin inferensi ketika
# KB ⊨ Pelaku(x) ∧ Senjata(w) ∧ TKP(r); jadi prasyarat Tuduh tetap berupa fakta di state.
TUDUH = Schema('Tuduh', [('?x', 'orang'), ('?w', 'senjata'), ('?r', 'ruang')],
               pre=[('Terbukti', '?x', '?w', '?r')], add=[('Selesai',)])


class Planner:
    def __init__(self, objects, static):
        """objects: {tipe: [objek]}, static: himpunan fakta yang tidak pernah berubah."""
        self.static = frozenset(static)
        self.ground = []
        for sch in SCHEMAS:
            doms = [objects[t] for _, t in sch.params]
            for combo in product(*doms):
                env = {v: o for (v, _), o in zip(sch.params, combo)}
                pre = [_bind(f, env) for f in sch.pre]
                # buang grounding yang prasyarat statisnya pasti gagal
                if any(f[0] in STATIC_PRED and f not in self.static for f in pre):
                    continue
                self.ground.append((sch.name, combo, pre, [_bind(f, env) for f in sch.pre_not],
                                    [_bind(f, env) for f in sch.add], [_bind(f, env) for f in sch.dele]))

    def applicable(self, state):
        for g in self.ground:
            _, _, pre, pre_not, _, _ = g
            if all(f in state or f in self.static for f in pre) and not any(f in state for f in pre_not):
                yield g

    @staticmethod
    def _jejak(parent, cur):
        plan = []
        while parent[cur]:
            cur, act = parent[cur]
            plan.append(act)
        return plan[::-1]

    def astar(self, state, goal, h):
        """A*: f(n) = g(n) + h(n), setiap aksi berbiaya 1.

        goal(state) -> bool, h(state) -> perkiraan biaya sisa (harus admissible).
        Mengembalikan (rencana, simpul diekspansi). Tes tujuan dilakukan saat simpul diambil
        dari antrean, sehingga rencana pertama yang ditemukan adalah yang terpendek.
        """
        start = frozenset(state)
        tie = 0
        frontier = [(h(start), tie, 0, start)]
        parent = {start: None}
        best_g = {start: 0}
        closed = set()
        expanded = 0
        while frontier:
            _, _, g, s = heapq.heappop(frontier)
            if s in closed:
                continue
            if goal(s):
                return self._jejak(parent, s), expanded
            closed.add(s)
            expanded += 1
            for name, combo, _, _, add, dele in self.applicable(s):
                nxt = (s - frozenset(dele)) | frozenset(add)
                ng = g + 1
                if nxt in closed or ng >= best_g.get(nxt, float('inf')):
                    continue
                best_g[nxt] = ng
                parent[nxt] = (s, (name, combo))
                tie += 1
                heapq.heappush(frontier, (ng + h(nxt), tie, ng, nxt))
        return None, expanded

    def plan(self, state, goal):
        """BFS dari state sampai goal(state) benar. Mengembalikan (rencana, simpul diekspansi)."""
        start = frozenset(state)
        if goal(start):
            return [], 1
        frontier = deque([start])
        parent = {start: None}
        expanded = 0
        while frontier:
            s = frontier.popleft()
            expanded += 1
            for g in self.applicable(s):
                name, combo, _, _, add, dele = g
                nxt = (s - frozenset(dele)) | frozenset(add)
                if nxt in parent:
                    continue
                parent[nxt] = (s, (name, combo))
                if goal(nxt):
                    return self._jejak(parent, nxt), expanded
                frontier.append(nxt)
        return None, expanded
