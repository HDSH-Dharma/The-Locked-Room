"""
layar_sidebar.py
Logic — logika sidebar "Game baru": kunci pengaturan, jatah game test mode, dan nomor kasus latihan.
"""
from logic.agen.daftar import LAWAN_AI
from logic.evaluasi.pembagian import jatah_berikutnya, muat_pembagian
from model.pembagian_model import PEMAIN
from model.ui_model import JUMLAH_LATIHAN, KASUS_PLAYTEST


class LayarSidebar:
    """Pilihan game baru. permainan = LayarPermainan game yang sedang berjalan, atau None."""

    def __init__(self, permainan):
        self.permainan = permainan
        self.pembagian = muat_pembagian()

    # MARK: - Pengaturan

    def pemain(self):
        return PEMAIN

    def daftar_lawan(self):
        return list(LAWAN_AI)

    def terkunci(self):
        """Pengaturan tidak bisa diubah selama game berjalan."""
        return self.permainan is not None and not self.permainan.game.hasil

    def ada_game(self):
        return self.permainan is not None

    def pakai_pembagian(self, mode):
        """Test mode memakai pembagian.json kalau ada: kasus dan lawan tidak dipilih sendiri."""
        return mode == 'Test mode' and bool(self.pembagian)

    def latihan(self, mode):
        return mode == 'Normal'

    def batas_latihan(self):
        return JUMLAH_LATIHAN

    def batas_kasus(self):
        return KASUS_PLAYTEST

    # MARK: - Pilihan game

    def jatah(self, pemain):
        """(keterangan, pilihan) dari pembagian.json. pilihan = (seed, lawan, uji) atau None."""
        jatah = jatah_berikutnya(self.pembagian, pemain) if pemain else None
        if jatah:
            return f'Game ke-{jatah["no"]} · Kasus {jatah["seed"]} · lawan dirahasiakan', (jatah['seed'], jatah['lawan'], True)
        if pemain:
            return 'Semua game jatahmu sudah selesai.', None
        return None, None

    def pilihan_manual(self, pemain, mode, nomor, ai_live):
        """Mode normal (latihan, kasus 301–350 supaya kasus playtest tidak bocor), atau test mode
        tanpa pembagian.json. Mengembalikan (seed, lawan, uji) atau None kalau inisial belum dipilih."""
        seed = KASUS_PLAYTEST + nomor if mode == 'Normal' else nomor
        return (int(seed), ai_live, mode == 'Test mode') if pemain else None

    def keterangan_bawah(self, pemain):
        if self.terkunci():
            return 'Game sedang berjalan. Pengaturan terkunci sampai game selesai. Refresh halaman untuk membatalkan.'
        if not pemain:
            return 'Pilih inisial untuk mulai.'
        return None
