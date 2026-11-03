"""
Pembagian kasus playtest untuk tiga pemain: 28 game per pemain, total 84.

Kasus 1–300 diacak sekali dengan seed tetap lalu dibagi rata (100 per pemain), jadi tidak ada pemain
yang kebagian kasus mudah atau sulit semua. Setiap pemain memainkan 28 game pertama dari jatahnya.
Lawan AI bergiliran mengikuti urutan game (ke-1 v2, ke-2 v1, ke-3 polisi, ke-4 penebak, dan seterusnya),
sehingga setiap pemain melawan setiap AI 7 kali. Jumlah game harus kelipatan 4 supaya seimbang.

  python buat_pembagian.py      -> pembagian.json (jalankan sekali saja)
"""
import json
import random

PEMAIN = ['GK', 'JC', 'HD']             # inisial Grevi, Jason, Dharma
LAWAN = ['v2', 'v1', 'polisi', 'penebak']
JUMLAH_KASUS = 300
GAME_PER_PEMAIN = 28                   # dipotong dari 100 karena waktu playtest; kelipatan len(LAWAN)
SEED_PEMBAGIAN = 2026


def buat_pembagian():
    kasus = list(range(1, JUMLAH_KASUS + 1))
    random.Random(SEED_PEMBAGIAN).shuffle(kasus)
    per_pemain = JUMLAH_KASUS // len(PEMAIN)
    return {nama: _jadwal(kasus[i * per_pemain:i * per_pemain + GAME_PER_PEMAIN]) for i, nama in enumerate(PEMAIN)}


def _jadwal(daftar_kasus):
    return [dict(no=j + 1, seed=seed, lawan=LAWAN[j % len(LAWAN)]) for j, seed in enumerate(daftar_kasus)]


if __name__ == '__main__':
    with open('pembagian.json', 'w') as f:
        json.dump(buat_pembagian(), f, indent=1)
