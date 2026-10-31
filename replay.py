"""
Replay: putar ulang aksi tim dari log playtest melawan Detektif AI mana pun.

  python replay.py      -> tes: replay melawan AI yang dilawan saat main harus memberi hasil yang sama
"""
import glob
import json
import os

from antarmuka import Tim
from daftar_ai import LAWAN_AI
from kasus import World
from permainan import Permainan


class TimRekaman(Tim):
    """Pengganti tim manusia: menjalankan ulang aksi yang tercatat di log, ronde demi ronde."""
    nama = 'rekaman log'

    def __init__(self, log):
        self.per_ronde = {}
        for ronde, d, aksi in log['aksi_tim']:
            self.per_ronde.setdefault(ronde, []).append((d, tuple(aksi)))
        self.tuduhan_log = log.get('tuduhan_tim')
        self.konflik_teleport = 0

    def giliran(self, game):
        for d, aksi in self.per_ronde.get(game.ronde, []):
            self._putar_aksi(game, d, aksi)
        t = self.tuduhan_log
        if t and not t['sidang'] and t['ronde'] == game.ronde:
            game.tuduh('tim', World(*t['jawaban']))

    def _putar_aksi(self, game, d, aksi):
        if aksi[0] == 'teleport' and game.tp_holder != ('tim', d):
            # Saat main, detektif d memegang teleport. Melawan AI lain, bisa jadi AI yang
            # menemukannya lebih dulu. Aksi tim tetap diputar persis seperti di log; kejadiannya dihitung.
            game.tp_holder = ('tim', d)
            self.konflik_teleport += 1
        game.tim_aksi(d, aksi)

    def sidang(self):
        t = self.tuduhan_log
        return World(*t['jawaban']) if t and t['sidang'] else None


def replay(log, agen):
    """Mainkan ulang satu log melawan agen. Mengembalikan (game, hasil, jumlah konflik teleport)."""
    tim = TimRekaman(log)
    game = Permainan(log['seed'], agen, tim, teleport=True, menguping=True)
    return game, game.jalan(), tim.konflik_teleport


def muat_log(folder='logs'):
    """Semua log di folder (tidak termasuk subfolder latihan), urut nama file."""
    logs = []
    for path in sorted(glob.glob(os.path.join(folder, '*.json'))):
        with open(path, encoding='utf-8') as f:
            logs.append((path, json.load(f)))
    return logs


def uji_replay(folder='logs'):
    """Replay melawan AI yang dilawan saat main harus memberi hasil yang sama, dan replay
    melawan semua AI lain harus jalan tanpa error."""
    beda = konflik = 0
    logs = muat_log(folder)
    for path, log in logs:
        for nama, buat_agen in LAWAN_AI.items():
            _, hasil, k = replay(log, buat_agen())
            konflik += k
            if nama == log['ai_live'] and hasil['tipe'] != log['hasil']:
                beda += 1
                print('BEDA', path, hasil['tipe'], log['hasil'])
    print(f'{len(logs)} log, beda dengan hasil live: {beda}, konflik teleport: {konflik}')


if __name__ == '__main__':
    uji_replay()
