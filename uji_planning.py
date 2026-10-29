"""
Uji A* pada gerak Detektif AI v2.

Setiap kali v2 merencanakan dalam permainan sungguhan (melawan tim bot, dengan teleport dan
menguping), rencana A* dibandingkan dengan BFS pada state dan goal test yang sama:
- panjang rencana harus sama (A* dengan heuristik admissible selalu optimal),
- h(n) tidak boleh melebihi sisa biaya sebenarnya di setiap state pada rencana terpendek,
- jumlah node yang diekspansi A* dibandingkan dengan BFS.

  python uji_planning.py [jumlah_kasus]
"""
import sys
from collections import Counter

import agen_v2
import planning
from agen_baseline import TimLambat
from permainan import Permainan

catat = Counter()


def astar_banding(start, goal, h, lokasi):
    plan, n = planning.astar(start, goal, h, lokasi)
    plan_bfs, n_bfs = planning.bfs(start, goal, lokasi)
    catat['rencana'] += 1
    catat['node_astar'] += n
    catat['node_bfs'] += n_bfs
    if (plan is None) != (plan_bfs is None) or (plan is not None and len(plan) != len(plan_bfs)):
        catat['beda_panjang'] += 1
    if plan_bfs is not None:
        s, sisa = start, len(plan_bfs)
        for a in [None] + plan_bfs:
            if a is not None:
                s, sisa = planning.result(s, a), sisa - 1
            catat['h_dicek'] += 1
            if h(s) > sisa:
                catat['h_melebihi'] += 1
    return plan, n


def main(n_kasus=300):
    agen_v2.astar = astar_banding
    try:
        for seed in range(1, n_kasus + 1):
            Permainan(seed, agen_v2.AgenV2(), TimLambat(), teleport=True, menguping=True).jalan()
    finally:
        agen_v2.astar = planning.astar
    hemat = 100 * (1 - catat['node_astar'] / max(catat['node_bfs'], 1))
    print(f'{n_kasus} kasus, {catat["rencana"]} rencana: panjang A* beda dengan BFS {catat["beda_panjang"]}, '
          f'h melebihi biaya sebenarnya {catat["h_melebihi"]} dari {catat["h_dicek"]} state, '
          f'node A* {catat["node_astar"]} vs BFS {catat["node_bfs"]} ({hemat:.0f}% lebih sedikit)')
    return dict(catat)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
