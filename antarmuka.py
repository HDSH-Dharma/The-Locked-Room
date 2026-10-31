"""
Kontrak bersama antara engine (permainan.py) dan para pemain: Detektif AI dan tim.

Engine hanya memanggil method yang didefinisikan di sini. Detektif AI atau tim baru cukup
mewarisi kelas yang sesuai dan mengganti method yang perlu; method yang tidak diganti
sudah punya perilaku netral (tidak mengamati apa pun, tidak bergerak, tidak menuduh).
Detektif AI yang bisa dipilih di UI dan replay didaftarkan di daftar_ai.py.

Dua mixin dipakai bersama oleh v1, v2 dan tim bot:
- PengingatTopik : mencatat topik bukti yang terdengar saat menguping lawan.
- PemeriksaModel : menyaring 64 kemungkinan jawaban (model checking proposisional).
"""
from kasus import ALL_WORLDS


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


def kunci_topik(jenis, target):
    """Kunci catatan menguping: ('r', ruangan) untuk geledah, ('s', tersangka) untuk interogasi."""
    return ('r' if jenis == 'geledah' else 's', target)


class PengingatTopik:
    """Mixin: menyimpan topik hasil menguping. Topik bukan fakta logika, jadi tidak masuk KB."""

    def _lupakan_topik(self):
        self.topik = {}

    def dengar(self, jenis, target, topik):
        self.topik[kunci_topik(jenis, target)] = list(topik)


def kemungkinan(models):
    """Nilai yang masih mungkin untuk pelaku, senjata, dan TKP."""
    return ({m.s for m in models}, {m.w for m in models}, {m.r for m in models})


class PemeriksaModel:
    """Mixin model checking: setiap bukti membuang model (pelaku, senjata, TKP) yang bertentangan."""

    def _mulai_model(self):
        self.models = list(ALL_WORLDS)

    def _saring(self, clue):
        self.models = [m for m in self.models if clue['prop'](m)]

    def terbuka(self):
        """Kategori jawaban yang belum pasti."""
        pelaku, senjata, tkp = kemungkinan(self.models)
        return dict(tersangka=len(pelaku) > 1, senjata=len(senjata) > 1, ruangan=len(tkp) > 1)
