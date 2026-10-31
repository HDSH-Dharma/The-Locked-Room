"""
planning_model.py
Model — state perencanaan gerak AI dan teks problem formulation. Data saja.
"""
from collections import namedtuple

from model.rumah_model import START

# MARK: - State

State            = namedtuple('State', 'ruang digeledah ditanya teleport')
DIPERIKSA_POLISI = START  # Ruang Tamu sudah diperiksa polisi, tidak bisa digeledah

# MARK: - Teks problem formulation (lampiran laporan)

TEKS_FORMULASI = '\n'.join([
    'State      : (ruangan AI, ruangan sudah digeledah, tersangka sudah ditanya, memegang teleport)',
    'ACTIONS(s) : Pindah(r)      r bersebelahan dengan ruangan AI',
    '             Teleport(r)    r serong 1-2 kotak, hanya kalau memegang teleport',
    '             Geledah(r)     r = ruangan AI, belum digeledah, bukan Ruang Tamu (sudah diperiksa polisi)',
    '             Interogasi(x)  x di ruangan AI dan belum ditanya',
    '             Tuduh(x,w,r)   hanya kalau KB berisi Terbukti(x, w, r)',
    'RESULT     : Pindah/Teleport mengganti ruangan AI (Teleport juga melepas teleport);',
    '             Geledah/Interogasi menambah ruangan/tersangka ke himpunan yang sudah diperiksa',
    'Goal test  : satu informasi baru didapat dari target yang topiknya belum terbukti',
    'Biaya      : 1 per aksi',
    'Heuristik  : h = d + 1, atau max(0, d - 3) + 1 saat memegang teleport (d = jarak Manhattan)',
])
