"""
Agen pembanding (baseline) dan tim simulasi.

- AIPolisi        : langsung menuduh orang yang ditangkap dan ruangan tempat jasad ditemukan,
                    tanpa penalaran.
- DetektifPenebak : penalaran v1, tapi berani menuduh begitu sisa kemungkinan <= 3
                    (menebak salah satunya). Lebih cepat, tapi bisa salah tangkap.
- AIDiam          : lawan kosong, untuk mengukur apakah tim bisa selesai dalam 7 ronde.
- TimBot          : pengganti tim manusia 3 orang. Tiga detektif berbagi catatan dan memakai
                    "bantuan logika" (model checking). Menuduh jika sisa kemungkinan <= ambang.
                    Tidak mengintip isi ruangan: semua ruangan yang belum digeledah (kecuali
                    Ruang Tamu, sudah diperiksa polisi) adalah target, sama seperti pemain manusia.
- TimLambat       : TimBot yang baru memahami arti bukti satu ronde kemudian (butuh waktu
                    diskusi). Perkiraan kasar untuk tim manusia tanpa bantuan logika.
"""
import random

from agen_v1 import AgenV1
from antarmuka import DetektifAI, PemeriksaModel, PengingatTopik, Tim, kunci_topik
from denah import jarak, langkah_pertama, nilai_target
from kasus import S_IDS, W_IDS, R_IDS, START, World

DETEKTIF = (1, 2, 3)


class AIPolisi(DetektifAI):
    """Baseline polisi: langsung menuduh orang yang ditangkap dan ruangan tempat jasad
    ditemukan, tanpa penalaran. Senjata dipilih acak, tapi selalu sama untuk kasus yang sama."""
    nama = 'polisi'

    def mulai(self, case):
        super().mulai(case)
        senjata = random.Random(case['seed']).choice(W_IDS)
        self.jawaban = World(case['arrested'], senjata, case['found'])
        self.log = []

    def tuduhan(self):
        return self.jawaban


class DetektifPenebak(AgenV1):
    nama = 'penebak (v1, menuduh saat sisa ≤ 3)'

    def __init__(self, ambang=3, seed=0):
        self.ambang, self.rng = ambang, random.Random(seed)

    def tuduhan(self):
        if len(self.models) <= self.ambang:
            return self.rng.choice(self.models)
        return None


class AIDiam(DetektifAI):
    nama = 'tanpa lawan'


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

    def _yakin(self):
        return self.models[0] if len(self.models) <= self.ambang else None

    def giliran(self, game):
        sudah_diambil = set()        # target yang sudah dituju detektif lain di ronde ini
        for d in DETEKTIF:
            if self._tuduh_kalau_yakin(game):
                return
            self._gerakkan_detektif(game, d, sudah_diambil)
        self._tuduh_kalau_yakin(game)

    def _tuduh_kalau_yakin(self, game):
        jawaban = self._yakin()
        if jawaban:
            game.tuduh('tim', jawaban)
        return bool(jawaban)

    def _gerakkan_detektif(self, game, d, sudah_diambil):
        """Detektif d menuju target terdekat yang belum diambil detektif lain. Kalau sudah
        di ruangan target, langsung geledah atau interogasi."""
        pos = game.tim_pos[d]
        punya_tp = game.tp_holder == ('tim', d)
        jarak_jalan, jarak_tp = jarak(pos, punya_tp)
        kandidat = self._kandidat_target(game)
        bebas = [k for k in kandidat if k[0] not in sudah_diambil] or kandidat
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

    def sidang(self):
        return self.models[0] if len(self.models) <= 2 else None


class TimLambat(TimBot):
    nama = 'tim lambat (logika sempurna, tapi paham bukti satu ronde kemudian)'

    def mulai(self, case):
        super().mulai(case)
        self.antre = []

    def amati(self, ids):
        self.antre.extend(ids)

    def _cerna(self):
        """Diskusi di awal ronde: bukti ronde lalu baru dipahami sekarang."""
        for cid in self.antre:
            self._saring(self.case['by_id'][cid])
        self.antre = []

    def giliran(self, game):
        self._cerna()
        super().giliran(game)

    def sidang(self):
        self._cerna()
        return super().sidang()
