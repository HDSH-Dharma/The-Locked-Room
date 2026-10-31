"""
tim_bot_agent.py
Agent — tim bot pengganti tim manusia 3 orang, untuk simulasi.

- TimBot    : tiga detektif berbagi catatan dan memakai "bantuan logika" (model checking).
              Menuduh jika sisa kemungkinan <= ambang. Tidak mengintip isi ruangan: semua ruangan
              yang belum digeledah (kecuali Ruang Tamu, sudah diperiksa polisi) adalah target,
              sama seperti pemain manusia.
- TimLambat : TimBot yang baru memahami arti bukti satu ronde kemudian (butuh waktu diskusi).
              Perkiraan kasar untuk tim manusia tanpa bantuan logika.
"""
from agents.kontrak_agent import Tim
from agents.mixin_agent import PemeriksaModel, PengingatTopik
from models.permainan_model import DETEKTIF
from models.rumah_model import R_IDS, S_IDS, START
from services.denah_service import jarak, langkah_pertama
from services.topik_service import kunci_topik, nilai_target

# MARK: - Tim bot

class TimBot(PengingatTopik, PemeriksaModel, Tim):
    nama = 'tim bot (3 detektif, model checking)'

    def __init__(self, ambang=1):
        self.ambang = ambang

    def mulai(self, case):
        super().mulai(case)
        self._mulai_model()
        self._lupakan_topik()

    def amati(self, ids):
        for cid in ids:
            self._saring(self.case['by_id'][cid])

    def giliran(self, game):
        sudah_diambil = set()        # target yang sudah dituju detektif lain di ronde ini
        for d in DETEKTIF:
            if self._tuduh_kalau_yakin(game):
                return
            self._gerakkan_detektif(game, d, sudah_diambil)
        self._tuduh_kalau_yakin(game)

    def sidang(self):
        return self.models[0] if len(self.models) <= 2 else None

    # MARK: - Private Helpers

    def _yakin(self):
        return self.models[0] if len(self.models) <= self.ambang else None

    def _tuduh_kalau_yakin(self, game):
        jawaban = self._yakin()
        if jawaban:
            game.tuduh('tim', jawaban)
        return bool(jawaban)

    def _gerakkan_detektif(self, game, d, sudah_diambil):
        """Detektif d menuju target terdekat yang belum diambil detektif lain. Kalau sudah
        di ruangan target, langsung geledah atau interogasi."""
        pos      = game.tim_pos[d]
        punya_tp = game.tp_holder == ('tim', d)
        jarak_jalan, jarak_tp = jarak(pos, punya_tp)
        kandidat = self._kandidat_target(game)
        bebas    = [k for k in kandidat if k[0] not in sudah_diambil] or kandidat
        if not bebas:
            return
        aksi, ruang = min(bebas, key=lambda k: jarak_tp[k[1]])
        sudah_diambil.add(aksi)
        if ruang == pos:
            self.amati(game.tim_aksi(d, aksi))
        else:
            game.tim_aksi(d, langkah_pertama(pos, ruang, jarak_tp[ruang] < jarak_jalan[ruang]))

    def _kandidat_target(self, game):
        """(aksi, ruangan tujuan) untuk setiap ruangan dan tersangka yang masih layak dituju."""
        terbuka = self.terbuka()
        kandidat = [(('geledah', r), r) for r in R_IDS
                    if r != START and r not in game.tim_searched
                    and nilai_target(self.topik, kunci_topik('geledah', r), 1, terbuka)]
        kandidat += [(('interogasi', x), self.case['loc'][x]) for x in S_IDS
                     if x not in game.tim_asked
                     and nilai_target(self.topik, kunci_topik('interogasi', x), 1, terbuka)]
        return kandidat


# MARK: - Tim lambat

class TimLambat(TimBot):
    nama = 'tim lambat (logika sempurna, tapi paham bukti satu ronde kemudian)'

    def mulai(self, case):
        super().mulai(case)
        self.antre = []

    def amati(self, ids):
        self.antre.extend(ids)

    def giliran(self, game):
        self._cerna()
        super().giliran(game)

    def sidang(self):
        self._cerna()
        return super().sidang()

    # MARK: - Private Helpers

    def _cerna(self):
        """Diskusi di awal ronde: bukti ronde lalu baru dipahami sekarang."""
        for cid in self.antre:
            self._saring(self.case['by_id'][cid])
        self.antre = []
