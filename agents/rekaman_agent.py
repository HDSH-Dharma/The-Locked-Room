"""
rekaman_agent.py
Agent — tim rekaman: pengganti tim manusia yang memutar ulang aksi dari log playtest.
"""
from agents.kontrak_agent import Tim
from models.rumah_model import World

# MARK: - Tim rekaman

class TimRekaman(Tim):
    """Pengganti tim manusia: menjalankan ulang aksi yang tercatat di log, ronde demi ronde."""
    nama = 'rekaman log'

    def __init__(self, log):
        self.per_ronde = {}
        for ronde, d, aksi in log['aksi_tim']:
            self.per_ronde.setdefault(ronde, []).append((d, tuple(aksi)))
        self.tuduhan_log      = log.get('tuduhan_tim')
        self.konflik_teleport = 0

    def giliran(self, game):
        for d, aksi in self.per_ronde.get(game.ronde, []):
            self._putar_aksi(game, d, aksi)
        t = self.tuduhan_log
        if t and not t['sidang'] and t['ronde'] == game.ronde:
            game.tuduh('tim', World(*t['jawaban']))

    def sidang(self):
        t = self.tuduhan_log
        return World(*t['jawaban']) if t and t['sidang'] else None

    # MARK: - Private Helpers

    def _putar_aksi(self, game, d, aksi):
        if aksi[0] == 'teleport' and game.tp_holder != ('tim', d):
            # Saat main, detektif d memegang teleport. Melawan AI lain, bisa jadi AI yang
            # menemukannya lebih dulu. Aksi tim tetap diputar persis seperti di log; kejadiannya dihitung.
            game.tp_holder = ('tim', d)
            self.konflik_teleport += 1
        game.tim_aksi(d, aksi)
