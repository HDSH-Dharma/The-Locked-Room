"""
rumah.py
Logic — nama tampil tersangka, senjata, dan ruangan, serta tetangga ruangan di denah.
"""
from model.rumah_model import NAMA_RUANGAN, NAMA_SENJATA, NAMA_TERSANGKA, POS, R_IDS

# MARK: - Nama tampil

def sn(i):
    """Nama tersangka untuk ditampilkan."""
    return NAMA_TERSANGKA[i]


def wn(i):
    """Nama senjata untuk ditampilkan."""
    return NAMA_SENJATA[i]


def rn(i):
    """Nama ruangan untuk ditampilkan."""
    return NAMA_RUANGAN[i]


# MARK: - Denah

def neighbors(room):
    r, c = POS[room]
    return [x for x in R_IDS if abs(POS[x][0] - r) + abs(POS[x][1] - c) == 1]
