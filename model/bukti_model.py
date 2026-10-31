"""
bukti_model.py
Model — angka aturan generator kasus dan teks bukti. Data saja, tanpa logika.
"""
from model.rumah_model import WAKTU_KEMATIAN

# MARK: - Peluang dan batas generator

PELUANG_TANGKAP_PELAKU      = 0.3   # polisi kebetulan menangkap pelaku asli
PELUANG_JASAD_DI_TKP        = 0.3   # jasad tidak dipindahkan dari TKP
PELUANG_KESAKSIAN_DIRI      = 0.25  # tersangka hanya berkata "Aku bukan pelakunya." (paling banyak satu)
MIN_MODEL_SETELAH_KESAKSIAN = 5     # kesaksian saja tidak boleh mempersempit jawaban terlalu jauh
BUKTI_PENENTU_MIN, BUKTI_PENENTU_MAX = 4, 8
MIN_JAWABAN_TANPA_KESAKSIAN = 2  # bukti fisik saja tidak cukup: kesaksian harus ikut dipakai
JUMLAH_PENGECOH             = 2
MAKS_BUKTI_PER_RUANG        = 2
BATAS_PERCOBAAN             = 400
LANTAI_KAYU                 = ('perpus', 'kamar')
SENJATA_TANPA_DARAH         = ('racun', 'tali')

# MARK: - Teks bukti

TANDA_SENJATA_UTUH = {
    'pisau': ('Semua pisau di rak dapur lengkap dan bersih.', 'dapur'),
    'racun': ('Botol racun tikus di gudang masih tersegel rapat.', 'gudang'),
    'tali': ('Satu-satunya gulungan tali di rumah masih tersegel di loteng.', 'loteng'),
    'vas': ('Semua vas di rumah utuh, tidak ada yang retak atau hilang.', 'rmakan'),
}
TANDA_RUANGAN_KOSONG = {
    'kamar': 'Kamar tidur terkunci dari dalam dan kosong semalaman.',
    'perpus': 'Debu di lantai perpustakaan utuh, tidak ada yang masuk semalam.',
    'dapur': 'Rekaman CCTV dapur: tidak ada kejadian apa pun semalaman.',
    'taman': 'Tanah taman becek, tapi tidak ada satu pun jejak kaki.',
}
TEKS_ALIBI = [                              # {nama} diisi nama tersangka yang punya alibi
    f'Struk minimarket: {{nama}} berbelanja di luar rumah pukul {WAKTU_KEMATIAN}.',
    f'Satpam kompleks: {{nama}} mengobrol di pos jaga pukul {WAKTU_KEMATIAN}.',
    'Tiket bioskop atas nama {nama}, pertunjukan pukul 20.45–23.10.',
]
TEKS_PENGECOH = [
    ('Ada puntung rokok di dekat pagar.', 'PuntungRokok'),
    ('Jendela loteng terbuka sedikit.', 'JendelaLotengTerbuka'),
    ('Korban baru saja mengubah surat wasiatnya minggu lalu.', 'WasiatDiubah'),
    ('Ada dua gelas kopi setengah habis di meja.', 'DuaGelasKopi'),
    ('Lampu kamar mandi berkedip-kedip.', 'LampuBerkedip'),
    ('Anjing tetangga menggonggong sekitar pukul 22.00.', 'AnjingMenggonggong'),
]
