"""Replay: putar ulang aksi tim dari log playtest melawan Detektif AI mana pun."""
import glob
import json

from agen_baseline import AIPolisi, DetektifPenebak
from agen_v1 import AgenV1
from agen_v2 import AgenV2
from kasus import World
from permainan import Permainan

# Harus sama persis dengan LAWAN di app.py, termasuk DetektifPenebak(3, 0)
AGEN = {'v2': AgenV2, 'v1': AgenV1, 'polisi': AIPolisi, 'penebak': lambda: DetektifPenebak(3, 0)}


class TimRekaman:
    """Pengganti tim manusia: menjalankan ulang aksi yang tercatat di log, ronde demi ronde."""

    def __init__(self, log):
        self.per_ronde = {}
        for ronde, d, aksi in log['aksi_tim']:
            self.per_ronde.setdefault(ronde, []).append((d, tuple(aksi)))
        self.tuduhan_log = log.get('tuduhan_tim')
        self.konflik_teleport = 0

    def mulai(self, case): pass
    def amati(self, ids): pass
    def dengar(self, jenis, target, topik): pass

    def giliran(self, game):
        for d, aksi in self.per_ronde.get(game.ronde, []):
            if aksi[0] == 'teleport' and game.tp_holder != ('tim', d):
                # Saat main, detektif d memegang teleport. Melawan AI lain, bisa jadi AI yang
                # menemukannya lebih dulu. Aksi tim tetap diputar persis seperti di log; kejadiannya dihitung.
                game.tp_holder = ('tim', d)
                self.konflik_teleport += 1
            game.tim_aksi(d, aksi)
        t = self.tuduhan_log
        if t and not t['sidang'] and t['ronde'] == game.ronde:
            game.tuduh('tim', World(*t['jawaban']))

    def sidang(self):
        t = self.tuduhan_log
        return World(*t['jawaban']) if t and t['sidang'] else None


def replay(log, agen):
    tim = TimRekaman(log)
    g = Permainan(log['seed'], agen, tim, teleport=True, menguping=True)
    return g, g.jalan(), tim.konflik_teleport


if __name__ == '__main__':
    # Tes 1: replay melawan AI yang dilawan saat main harus memberi hasil yang sama.
    # Tes 2: replay melawan semua AI lain harus jalan tanpa error.
    beda = konflik = 0
    logs = sorted(glob.glob('logs/*.json'))
    for f in logs:
        log = json.load(open(f))
        for nama, buat in AGEN.items():
            _, h, k = replay(log, buat())
            konflik += k
            if nama == log['ai_live'] and h['tipe'] != log['hasil']:
                beda += 1
                print('BEDA', f, h['tipe'], log['hasil'])
    print(f'{len(logs)} log, beda dengan hasil live: {beda}, konflik teleport: {konflik}')

