"""
uji_planning.py
Test — A* pada gerak Detektif AI v2.

Setiap kali v2 merencanakan dalam permainan sungguhan (melawan tim bot, dengan teleport dan
menguping), A* dibandingkan dengan BFS pada state awal dan goal test yang sama:
- panjang rencana harus sama (A* dengan heuristik admissible selalu optimal),
- h(n) tidak boleh melebihi sisa biaya sebenarnya di setiap state pada rencana terpendek,
- jumlah node yang diekspansi A* dibandingkan dengan BFS.

  python -m tests.uji_planning [jumlah_kasus]
"""
import sys
from collections import Counter

from logic.agen.agen_v2 import AgenV2
from logic.agen.tim_bot import TimLambat
from logic.penalaran.planning import astar, bfs, goal_info_baru, heuristik, result
from logic.permainan.permainan import Permainan
from model.planning_model import State

# MARK: - Pembanding

def bandingkan(start, goal, h, lokasi, catat):
    plan, n = astar(start, goal, h, lokasi)
    plan_bfs, n_bfs = bfs(start, goal, lokasi)
    catat['rencana'] += 1
    catat['node_astar'] += n
    catat['node_bfs'] += n_bfs
    if (plan is None) != (plan_bfs is None) or (plan is not None and len(plan) != len(plan_bfs)):
        catat['beda_panjang'] += 1
    if plan_bfs is None:
        return
    s, sisa = start, len(plan_bfs)
    for a in [None] + plan_bfs:
        if a is not None:
            s, sisa = result(s, a), sisa - 1
        catat['h_dicek'] += 1
        catat['h_melebihi'] += h(s) > sisa


class AgenV2Banding(AgenV2):
    """v2 biasa, tapi setiap kali merencanakan, A* dan BFS dijalankan pada masalah yang sama."""

    def __init__(self, catat):
        super().__init__()
        self.catat = catat

    def aksi(self, pos, searched, asked, punya_tp=False):
        rooms, sus = self.target(searched, asked)
        if rooms or sus:
            lokasi = self.case['loc']
            goal   = goal_info_baru(searched, asked, rooms, sus)
            h      = heuristik(list(rooms) + [lokasi[x] for x in sus], goal)
            start  = State(pos, frozenset(searched), frozenset(asked), False)
            for tp in ((False, True) if punya_tp else (False,)):
                bandingkan(start._replace(teleport=tp), goal, h, lokasi, self.catat)
        return super().aksi(pos, searched, asked, punya_tp)


# MARK: - Main

def main(n_kasus=300):
    catat = Counter()
    for seed in range(1, n_kasus + 1):
        Permainan(seed, AgenV2Banding(catat), TimLambat(), teleport=True, menguping=True).jalan()
    hemat = 100 * (1 - catat['node_astar'] / max(catat['node_bfs'], 1))
    print(f'{n_kasus} kasus, {catat["rencana"]} rencana: panjang A* beda dengan BFS {catat["beda_panjang"]}, '
          f'h melebihi biaya sebenarnya {catat["h_melebihi"]} dari {catat["h_dicek"]} state, '
          f'node A* {catat["node_astar"]} vs BFS {catat["node_bfs"]} ({hemat:.0f}% lebih sedikit)')
    return dict(catat)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
