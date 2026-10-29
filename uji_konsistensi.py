"""
Uji konsistensi: v1 (model checking) dan v2 (FOL + resolusi) harus menarik
kesimpulan yang sama persis setelah setiap bukti, dalam urutan bukti acak.
"""
import random
import sys
from kasus import generate_case
from agen_v1 import AgenV1
from agen_v2 import AgenV2
from denah import pakai_denah


def main(n_kasus=300, seed_awal=1, denah='9', diam=False):
    pakai_denah(denah)
    rng = random.Random(2026)
    cek = beda = beda_rel = batas = 0
    for seed in range(seed_awal, seed_awal + n_kasus):
        c = generate_case(seed)
        a1, a2 = AgenV1(), AgenV2()
        a1.mulai(c)
        a2.mulai(c)
        ids = [k['id'] for k in c['clues']]
        rng.shuffle(ids)
        for cid in ids:
            e1 = a1.amati([cid], 1)[0]
            e2 = a2.amati([cid], 1)[0]
            cek += 1
            if a1.status() != a2.status():
                beda += 1
                print('BEDA kesimpulan', seed, cid, c['by_id'][cid]['text'])
            if e1['relevan'] != e2['relevan']:
                beda_rel += 1
                print('BEDA relevansi', seed, cid, c['by_id'][cid]['text'])
        batas += a2.stats['batas']
    if not diam:
        print(f'denah {denah}: {n_kasus} kasus, {cek} pembaruan KB dicek: beda kesimpulan {beda}, beda relevansi {beda_rel}, query kena batas {batas}')
    return cek, beda, beda_rel, batas


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300, denah=sys.argv[2] if len(sys.argv) > 2 else '9')
