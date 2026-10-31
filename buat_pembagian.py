"""
Pembagian 300 kasus playtest untuk tiga pemain.

Nomor kasus diacak sekali dengan seed tetap lalu dibagi rata, jadi tidak ada pemain yang kebagian
kasus mudah atau sulit semua. Lawan AI bergiliran mengikuti urutan game (ke-1 v2, ke-2 v1, ke-3 polisi,
ke-4 penebak, dan seterusnya), sehingga setiap pemain melawan setiap AI 25 kali.

  python buat_pembagian.py      -> pembagian.json (jalankan sekali saja)
"""
import json
import random

PEMAIN = ['GK', 'JC', 'HD']             # inisial Grevi, Jason, Dharma
LAWAN = ['v2', 'v1', 'polisi', 'penebak']
JUMLAH_KASUS = 300
SEED_PEMBAGIAN = 2026


def buat_pembagian():
    kasus = list(range(1, JUMLAH_KASUS + 1))
    random.Random(SEED_PEMBAGIAN).shuffle(kasus)
    per_pemain = JUMLAH_KASUS // len(PEMAIN)
    return {nama: _jadwal(kasus[i * per_pemain:(i + 1) * per_pemain]) for i, nama in enumerate(PEMAIN)}


def _jadwal(daftar_kasus):
    return [dict(no=j + 1, seed=seed, lawan=LAWAN[j % len(LAWAN)]) for j, seed in enumerate(daftar_kasus)]


if __name__ == '__main__':
    with open('pembagian.json', 'w') as f:
        json.dump(buat_pembagian(), f, indent=1)
