"""
kontrak_agent.py
Agent — kontrak bersama antara engine (permainan_engine) dan para pemain: Detektif AI dan tim.

Engine hanya memanggil method yang didefinisikan di sini. Detektif AI atau tim baru cukup
mewarisi kelas yang sesuai dan mengganti method yang perlu; method yang tidak diganti
sudah punya perilaku netral (tidak mengamati apa pun, tidak bergerak, tidak menuduh).
Detektif AI yang bisa dipilih di UI dan replay didaftarkan di daftar_agent.py.
"""

# MARK: - Detektif AI

class DetektifAI:
    """Detektif AI. Urutan panggilan engine: mulai -> amati (berkas polisi) -> per aksi:
    tuduhan(), lalu aksi(); setiap bukti baru diteruskan lewat amati()."""
    nama = 'detektif'

    def mulai(self, case):
        self.case = case

    def amati(self, ids, ronde):
        """Terima bukti baru. Mengembalikan catatan per bukti untuk log permainan."""
        return []

    def dengar(self, jenis, target, topik):
        """Topik bukti yang terdengar saat lawan menggeledah atau menginterogasi di dekat AI."""

    def aksi(self, pos, searched, asked, punya_tp=False):
        """Aksi berikutnya sebagai (jenis, target), atau (None, {}) kalau AI menunggu."""
        return None, {}

    def tuduhan(self):
        """Jawaban (World) kalau AI siap menuduh, selain itu None."""
        return None

    def trace_teks(self):
        """Penjelasan penalaran untuk layar akhir UI. Kosong berarti UI menyusun trace dari event."""
        return []


# MARK: - Tim

class Tim:
    """Tim tiga detektif. giliran() memainkan satu ronde lewat game.tim_aksi dan game.tuduh."""
    nama = 'tim'

    def mulai(self, case):
        self.case = case

    def amati(self, ids):
        """Bukti yang ditemukan tim sendiri."""

    def dengar(self, jenis, target, topik):
        """Topik bukti yang terdengar dari Detektif AI."""

    def giliran(self, game):
        raise NotImplementedError

    def sidang(self):
        """Tuduhan terakhir setelah ronde 7, atau None kalau tim menyerahkan ke hakim."""
        return None
