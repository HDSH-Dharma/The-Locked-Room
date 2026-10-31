"""
rumah_model.py
Model — data rumah, tersangka, senjata, dan konstanta permainan. Data saja, tanpa logika.

ROOMS, R_IDS, NAMA_RUANGAN, dan POS diganti isinya (in-place) oleh denah_service.pakai_denah(),
jadi semua modul yang sudah mengimpornya ikut memakai denah yang aktif.
"""
from collections import namedtuple

from models.denah_model import LAYOUTS

# MARK: - Tipe

World = namedtuple('World', 's w r')        # satu kemungkinan jawaban: (pelaku, senjata, TKP)

# MARK: - Tersangka, senjata, dan ruangan

SUSPECTS = [
    ('budi', 'Pak Budi', 'Tukang kebun', 'Budi'),
    ('sari', 'Bu Sari', 'Koki', 'Sari'),
    ('dimas', 'Dimas', 'Keponakan korban', 'Dimas'),
    ('nadia', 'Nadia', 'Sekretaris', 'Nadia'),
]
WEAPONS = [('pisau', 'Pisau'), ('racun', 'Racun'), ('tali', 'Tali'), ('vas', 'Vas')]
ROOMS   = list(LAYOUTS['9'])  # salinan, karena isinya diganti saat denah diganti
TKP     = ['perpus', 'dapur', 'kamar', 'taman']

# MARK: - Aturan permainan

START          = 'rtamu'  # Ruang Tamu: titik awal, sudah diperiksa polisi
MAX_ROUNDS     = 7
WAKTU_KEMATIAN = '21.00–23.00'

# MARK: - Indeks turunan

S_IDS          = [s[0] for s in SUSPECTS]
W_IDS          = [w[0] for w in WEAPONS]
R_IDS          = [r[0] for r in ROOMS]
NAMA_TERSANGKA = {s[0]: s[1] for s in SUSPECTS}
NAMA_SENJATA   = dict(WEAPONS)
NAMA_RUANGAN   = {r[0]: r[1] for r in ROOMS}
POS            = {r[0]: (r[2], r[3]) for r in ROOMS}
ALL_WORLDS     = [World(s, w, r) for s in S_IDS for w in W_IDS for r in TKP]

# MARK: - Konstanta FOL

C = {s[0]: s[3] for s in SUSPECTS}
C.update({w[0]: w[1] for w in WEAPONS})
C.update({'perpus': 'Perpustakaan', 'dapur': 'Dapur', 'kamar': 'KamarTidur', 'taman': 'Taman'})
DOMAIN = {
    'orang': [C[s] for s in S_IDS],
    'senjata': [C[w] for w in W_IDS],
    'ruang': [C[r] for r in TKP],
}
