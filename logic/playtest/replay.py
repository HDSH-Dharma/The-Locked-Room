"""
replay.py
Logic — memutar ulang aksi tim dari log playtest melawan Detektif AI mana pun.
"""
from logic.agen.rekaman import TimRekaman
from logic.permainan.permainan import Permainan

# MARK: - Replay

def replay(log, agen):
    """Mainkan ulang satu log melawan agen. Mengembalikan (game, hasil, jumlah konflik teleport)."""
    tim  = TimRekaman(log)
    game = Permainan(log['seed'], agen, tim, teleport=True, menguping=True)
    return game, game.jalan(), tim.konflik_teleport
