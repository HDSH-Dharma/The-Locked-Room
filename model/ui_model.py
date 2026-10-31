"""
ui_model.py
Model — konstanta dan teks tetap untuk UI Streamlit. Data saja.
"""
from model.rumah_model import MAX_ROUNDS, WAKTU_KEMATIAN

# MARK: - Kasus dan tampilan

KASUS_PLAYTEST = 300  # kasus 1–300 untuk playtest; latihan ke-n memakai kasus 300 + n
JUMLAH_LATIHAN = 50
JEDA_ANIMASI   = 0.9
WARNA_D        = {1: '#2f6fd6', 2: '#1f9d55', 3: '#d9822b'}
WARNA_AI       = '#c0392b'

# MARK: - Teks hasil

HASIL_TEKS = {
    'tim': ('success', 'Tim menang! Tuduhan kalian benar.'),
    'tim-salah': ('error', 'Tuduhan tim salah. Tim kalah.'),
    'ai': ('error', 'Detektif AI menuduh lebih dulu dan benar. AI menang.'),
    'ai-salah': ('success', 'Detektif AI salah tuduh. Tim menang.'),
    'vonis': ('warning', 'Tim tidak menuduh. Hakim memvonis orang yang ditangkap polisi. Hasil seri.'),
}
TUDUHAN_TIM_TEKS = {
    'tim': 'Tuduhan kalian benar.',
    'tim-salah': 'Tuduhan kalian salah.',
    'vonis': 'Kalian tidak menuduh sampai sidang.',
}

# MARK: - Cerita dan cara main

CERITA = (f'**Tuan Hartono ditemukan tewas di rumahnya**, dengan perkiraan waktu kematian pukul {WAKTU_KEMATIAN}. '
          'Polisi langsung menganggap ruangan tempat jasad ditemukan sebagai TKP dan menangkap seorang tersangka, '
          f'padahal berkasnya hanya berisi motif dan gosip. Sidang dimulai setelah ronde {MAX_ROUNDS}. '
          'Temukan pelaku, senjata, dan TKP yang sebenarnya sebelum Detektif AI.')
CARA_MAIN = ('**Cara main**\n'
             '1. Tiap ronde, Detektif 1, 2, 3 masing-masing 1 aksi.\n'
             '2. Setelah aksi ketiga, Detektif AI jalan 2–3 aksi.\n'
             '3. Semua ruangan yang belum digeledah boleh digeledah, kecuali Ruang Tamu (sudah diperiksa polisi). '
             'Isinya baru ketahuan setelah digeledah, dan ruangan bisa saja kosong.\n'
             '4. Pelaku selalu bohong; yang tidak bersalah selalu jujur.\n'
             '5. Jasad bisa sudah dipindahkan dari TKP.\n'
             '6. Menuduh boleh kapan saja di giliran tim, tapi hanya sekali.\n'
             f'7. Setelah ronde {MAX_ROUNDS}: sidang. Kalau tim tidak menuduh, hasilnya seri.')
