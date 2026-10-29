"""
Agen pembanding (baseline) dan tim simulasi.

- PolisiGegabah   : menuduh orang yang ditangkap dan menganggap tempat jasad ditemukan
                    sebagai TKP. Tidak memakai penalaran sama sekali.
- DetektifPenebak : penalaran v1, tapi berani menuduh begitu sisa kemungkinan <= 3
                    (menebak salah satunya). Lebih cepat, tapi bisa salah tangkap.
- TimBot          : pengganti tim manusia 3 orang. Tiga detektif berbagi catatan dan memakai
                    "bantuan logika" (model checking). Menuduh jika sisa kemungkinan <= ambang.
                    Tidak mengintip isi ruangan: semua ruangan yang belum digeledah (kecuali
                    Ruang Tamu, sudah diperiksa polisi) adalah target, sama seperti pemain manusia.
- TimLambat       : TimBot yang baru memahami arti bukti satu ronde kemudian (butuh waktu
                    diskusi). Perkiraan kasar untuk tim manusia tanpa bantuan logika.
- AIDiam          : lawan kosong, untuk mengukur apakah tim bisa selesai dalam 7 ronde.
"""
import random
from kasus import ALL_WORLDS, S_IDS, R_IDS, START
from agen_v1 import AgenV1, possible
from denah import jarak, langkah_pertama, nilai_target


def polisi_gegabah(case):
    tebakan_pelaku = case['arrested']
    tebakan_tkp = case['found']
    return dict(pelaku_benar=tebakan_pelaku == case['sol'].s, tkp_benar=tebakan_tkp == case['sol'].r,
                salah_tangkap=tebakan_pelaku != case['sol'].s)


class DetektifPenebak(AgenV1):
    nama = 'penebak (v1, menuduh saat sisa ≤ 3)'

    def __init__(self, ambang=3, seed=0):
        self.ambang, self.rng = ambang, random.Random(seed)

    def tuduhan(self):
        if len(self.models) <= self.ambang:
            return self.rng.choice(self.models)
        return None


class TimBot:
    nama = 'tim bot (3 detektif, model checking)'

    def __init__(self, ambang=1):
        self.ambang = ambang

    def mulai(self, case):
        self.case = case
        self.models = list(ALL_WORLDS)
        self.topik = {}

    def amati(self, ids):
        for cid in ids:
            clue = self.case['by_id'][cid]
            self.models = [m for m in self.models if clue['prop'](m)]

    def dengar(self, jenis, target, topik):
        self.topik[('r' if jenis == 'geledah' else 's', target)] = list(topik)

    def terbuka(self):
        ps, pw, pr = possible(self.models)
        return dict(tersangka=len(ps) > 1, senjata=len(pw) > 1, ruangan=len(pr) > 1)

    def _yakin(self):
        return self.models[0] if len(self.models) <= self.ambang else None

    def giliran(self, game):
        claimed = set()
        for d in (1, 2, 3):
            g = self._yakin()
            if g:
                game.tuduh('tim', g)
                return
            pos = game.tim_pos[d]
            punya_tp = game.tp_holder == ('tim', d)
            d0, d1 = jarak(pos, punya_tp)
            terbuka = self.terbuka()
            cands = []
            for r in R_IDS:
                if r != START and r not in game.tim_searched \
                        and nilai_target(self.topik, ('r', r), 1, terbuka):
                    cands.append((('geledah', r), r))
            for s in S_IDS:
                if s not in game.tim_asked and nilai_target(self.topik, ('s', s), 1, terbuka):
                    cands.append((('interogasi', s), self.case['loc'][s]))
            free = [c for c in cands if c[0] not in claimed] or cands
            if not free:
                continue
            free.sort(key=lambda c: d1[c[1]])
            act, room = free[0]
            claimed.add(act)
            if room == pos:
                self.amati(game.tim_aksi(d, act))
            else:
                game.tim_aksi(d, langkah_pertama(pos, room, d1[room] < d0[room]))
        g = self._yakin()
        if g:
            game.tuduh('tim', g)

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
        for cid in self.antre:
            clue = self.case['by_id'][cid]
            self.models = [m for m in self.models if clue['prop'](m)]
        self.antre = []

    def giliran(self, game):
        self._cerna()            # diskusi di awal ronde: bukti ronde lalu baru dipahami
        super().giliran(game)

    def sidang(self):
        self._cerna()
        return super().sidang()


class AIDiam:
    nama = 'tanpa lawan'

    def mulai(self, case):
        pass

    def amati(self, ids, ronde):
        return []

    def dengar(self, *a):
        pass

    def tuduhan(self):
        return None

    def aksi(self, *a, **k):
        return None, {}
