"""
Classical planning ala PDDL untuk Detektif AI v2 (materi Reasoning, slide 10–12).

State   : konjungsi fluent ground, misalnya Di(AI, Dapur) ∧ Digeledah(Gudang)
Aksi    : skema dengan PRECOND dan EFFECT (add/delete list)
Planner : forward state-space search (BFS), jadi rencana yang ditemukan paling pendek

Isi bukti baru diketahui setelah aksi dijalankan, jadi planner tidak bisa merencanakan
sampai "tuduh" dari awal. Agen memakai online replanning: rencanakan sampai mendapat
informasi baru, jalankan satu aksi, amati, perbarui KB, lalu rencanakan ulang.
"""
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
TUDUH = Schema('Tuduh', [('?s', 'orang'), ('?w', 'senjata'), ('?t', 'ruang')],
               check='KB ⊨ Pelaku(?s) ∧ Senjata(?w) ∧ TKP(?t)')


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

    def plan(self, state, goal):
        """BFS dari state sampai goal(state) benar. Mengembalikan (rencana, simpul diperiksa)."""
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
                    plan, cur = [], nxt
                    while parent[cur]:
                        cur, act = parent[cur]
                        plan.append(act)
                    return plan[::-1], expanded
                frontier.append(nxt)
        return None, expanded
