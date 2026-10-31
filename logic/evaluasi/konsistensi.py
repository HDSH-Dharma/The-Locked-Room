"""
konsistensi.py
Logic — uji konsistensi: v1 (model checking) dan v2 (FOL + resolusi) harus menarik kesimpulan
yang sama persis setelah setiap bukti, dalam urutan bukti acak.
"""
import random
from collections import Counter

from logic.agen.agen_v1 import AgenV1
from logic.agen.agen_v2 import AgenV2
from logic.kasus.denah import pakai_denah
from logic.kasus.kasus import generate_case

# MARK: - Perbandingan

def bandingkan(n_kasus=300, seed_awal=1, denah='9', diam=False):
    pakai_denah(denah)
    rng   = random.Random(2026)
    total = Counter()
    for seed in range(seed_awal, seed_awal + n_kasus):
        total.update(_bandingkan_kasus(seed, rng))
    if not diam:
        print(f'denah {denah}: {n_kasus} kasus, {total["cek"]} pembaruan KB dicek: beda kesimpulan {total["beda"]}, '
              f'beda relevansi {total["beda_rel"]}, query kena batas {total["batas"]}')
    return total['cek'], total['beda'], total['beda_rel'], total['batas']


# MARK: - Private Helpers

def _bandingkan_kasus(seed, rng):
    """Beri v1 dan v2 bukti yang sama satu per satu dalam urutan acak, lalu bandingkan."""
    case = generate_case(seed)
    v1, v2 = AgenV1(), AgenV2()
    v1.mulai(case)
    v2.mulai(case)
    ids = [k['id'] for k in case['clues']]
    rng.shuffle(ids)
    hitung = Counter()
    for cid in ids:
        e1, e2 = v1.amati([cid], 1)[0], v2.amati([cid], 1)[0]
        hitung['cek'] += 1
        if v1.status() != v2.status():
            hitung['beda'] += 1
            print('BEDA kesimpulan', seed, cid, case['by_id'][cid]['text'])
        if e1['relevan'] != e2['relevan']:
            hitung['beda_rel'] += 1
            print('BEDA relevansi', seed, cid, case['by_id'][cid]['text'])
    hitung['batas'] += v2.stats['batas']
    return hitung
