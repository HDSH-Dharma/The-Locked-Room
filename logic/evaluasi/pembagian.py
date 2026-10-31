"""
pembagian.py
Logic — pembagian 300 kasus playtest dan jatah game berikutnya tiap pemain.

Nomor kasus diacak sekali dengan seed tetap lalu dibagi rata, jadi tidak ada pemain yang kebagian
kasus mudah atau sulit semua. Lawan AI bergiliran mengikuti urutan game (ke-1 v2, ke-2 v1, ke-3
polisi, ke-4 penebak, dan seterusnya), sehingga setiap pemain melawan setiap AI 25 kali.
"""
import json
import os
import random

from logic.evaluasi.log import log_ada
from model.folder_model import PATH_PEMBAGIAN
from model.pembagian_model import JUMLAH_KASUS, LAWAN, PEMAIN, SEED_PEMBAGIAN

# MARK: - Pembagian

def buat_pembagian():
    kasus = list(range(1, JUMLAH_KASUS + 1))
    random.Random(SEED_PEMBAGIAN).shuffle(kasus)
    per_pemain = JUMLAH_KASUS // len(PEMAIN)
    return {nama: _jadwal(kasus[i * per_pemain:(i + 1) * per_pemain]) for i, nama in enumerate(PEMAIN)}


def muat_pembagian():
    """Isi pembagian.json: {inisial: [{no, seed, lawan}, ...]}. Kosong kalau file belum ada."""
    if not os.path.exists(PATH_PEMBAGIAN):
        return {}
    with open(PATH_PEMBAGIAN, encoding='utf-8') as f:
        return json.load(f)


def jatah_berikutnya(pembagian, pemain):
    """Game test mode berikutnya dari pembagian: entri pertama yang belum punya log."""
    for e in pembagian.get(pemain, []):
        if not log_ada(pemain, e['seed']):
            return e
    return None


# MARK: - Private Helpers

def _jadwal(daftar_kasus):
    return [dict(no=j + 1, seed=seed, lawan=LAWAN[j % len(LAWAN)]) for j, seed in enumerate(daftar_kasus)]
