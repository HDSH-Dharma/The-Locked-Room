"""
kasus.py
Logic — generator kasus: jawaban, kesaksian, bukti fisik, berkas polisi, teleport, dan topik.

Nomor kasus yang sama selalu menghasilkan kasus yang sama: RNG-nya mulberry32 (acak) dan
urutan pemanggilan acaknya tetap. Jangan menyisipkan, menghapus, atau menukar urutan pemanggilan
rnd() di PembuatKasus tanpa sengaja, karena semua kasus akan ikut berubah dan log lama tidak
bisa di-replay lagi.

Aturan proposal yang dipegang generator:
- Kesaksian tidak pernah menyebut pelaku asli. Kesaksian juga tidak menyebut tersangka lain:
  dengan aturan ini, "Aku yakin Y pelakunya" hanya bisa diucapkan pelaku (langsung membongkar
  pelakunya) dan "Y bukan pelakunya" hanya bisa diucapkan saksi jujur. Pelaku hanya bisa
  ditemukan dengan mencocokkan kesaksian dengan bukti lain.
- Ruang Tamu sudah diperiksa polisi (isinya berkas polisi), jadi tidak ada bukti fisik di sana.

Setiap bukti punya DUA representasi:
- `prop` : fungsi atas dunia (pelaku, senjata, TKP), dipakai agen v1 (proposisional)
- `fol`  : daftar fakta FOL, dipakai agen v2 (FOL + resolusi). Aturan umumnya ada di
           aturan_model.ATURAN; bukti hanya menambahkan fakta.
"""
from logic.kasus.acak import make_rng, pick, shuffle, weighted_pick
from logic.kasus.denah import letakkan_teleport
from logic.kasus.rumah import rn, sn, wn
from logic.kasus.topik import topik
from model.bukti_model import (
    BATAS_PERCOBAAN,
    BUKTI_PENENTU_MAX,
    BUKTI_PENENTU_MIN,
    JUMLAH_PENGECOH,
    LANTAI_KAYU,
    MAKS_BUKTI_PER_RUANG,
    MIN_JAWABAN_TANPA_KESAKSIAN,
    MIN_MODEL_SETELAH_KESAKSIAN,
    PELUANG_JASAD_DI_TKP,
    PELUANG_KESAKSIAN_DIRI,
    PELUANG_TANGKAP_PELAKU,
    SENJATA_TANPA_DARAH,
    TANDA_RUANGAN_KOSONG,
    TANDA_SENJATA_UTUH,
    TEKS_ALIBI,
    TEKS_PENGECOH,
)
from model.fol_model import Atom, Iff, Not
from model.rumah_model import ALL_WORLDS, R_IDS, S_IDS, START, TKP, W_IDS, WAKTU_KEMATIAN, C, World

# MARK: - API

def generate_case(seed):
    for attempt in range(BATAS_PERCOBAAN):
        case = PembuatKasus(make_rng(seed * 7919 + attempt * 104729 + 13)).buat()
        if case:
            case['seed'] = seed
            return case
    raise RuntimeError(f'Kasus gagal dibuat untuk nomor {seed}')


def lengkapi(case):
    """Tambahkan letak teleport dan topik tiap bukti ke kasus. Memakai aliran acak terpisah,
    jadi isi kasus (pelaku, bukti, letak bukti) tidak berubah."""
    letakkan_teleport(case)
    for c in case['clues']:
        c['topik'] = topik(c)
    return case


def statement_options(found):
    """Pernyataan yang bisa diucapkan saksi. Saksi jujur memilih yang benar, pelaku yang salah.
    Tidak ada pernyataan yang menyebut tersangka lain (lihat docstring modul)."""
    out   = []
    f_low = rn(found).lower()
    out.append(dict(weight=1, text='Jasadnya pasti dipindahkan dari tempat lain.', f=lambda m: m.r != found,
                    fol=Atom('Dipindahkan')))
    out.append(dict(weight=1, text=f'Korban dibunuh di {f_low}, tempat jasadnya ditemukan.', f=lambda m: m.r == found,
                    fol=Atom('TKP', C[found])))
    for w in W_IDS:
        low = wn(w).lower()
        out.append(dict(weight=1, text=f'Senjatanya bukan {low}.', f=lambda m, w=w: m.w != w, fol=Not(Atom('Senjata', C[w]))))
        out.append(dict(weight=1, text=f'Korban dibunuh dengan {low}.', f=lambda m, w=w: m.w == w, fol=Atom('Senjata', C[w])))
    for t in TKP:
        low = rn(t).lower()
        out.append(dict(weight=1, text=f'Kejadiannya bukan di {low}.', f=lambda m, t=t: m.r != t, fol=Not(Atom('TKP', C[t]))))
        out.append(dict(weight=1, text=f'Kejadiannya pasti di {low}.', f=lambda m, t=t: m.r == t, fol=Atom('TKP', C[t])))
    return out


# MARK: - Generator

class PembuatKasus:
    """Satu percobaan membuat kasus dari satu aliran angka acak. buat() mengembalikan None kalau
    hasilnya tidak memenuhi syarat; generate_case lalu mencoba aliran berikutnya.
    Urutan pemanggilan rnd() di kelas ini menentukan isi kasus (lihat docstring modul)."""

    def __init__(self, rnd):
        self.rnd = rnd

    def buat(self):
        self._pilih_jawaban()
        self._tempatkan_tersangka()
        testimonies = self._buat_kesaksian()
        models      = _jawaban_konsisten(testimonies)
        if len(models) < MIN_MODEL_SETELAH_KESAKSIAN:
            return None
        chosen = self._pilih_bukti_penentu(self._kumpulkan_bukti_fisik(), models)
        if chosen is None:
            return None
        physical = chosen + self._bukti_pengecoh()
        self._letakkan_bukti(physical)
        return self._rakit(self._berkas_polisi(), testimonies, physical)

    # MARK: - Private · Jawaban, penangkapan, dan posisi tersangka

    def _pilih_jawaban(self):
        rnd            = self.rnd
        self.sol       = World(pick(rnd, S_IDS), pick(rnd, W_IDS), pick(rnd, TKP))
        self.innocents = [i for i in S_IDS if i != self.sol.s]
        self.arrested  = self.sol.s if rnd() < PELUANG_TANGKAP_PELAKU else pick(rnd, self.innocents)
        self.found     = self.sol.r if rnd() < PELUANG_JASAD_DI_TKP else pick(rnd, [t for t in TKP if t != self.sol.r])
        self.moved     = self.found != self.sol.r

    def _tempatkan_tersangka(self):
        """Yang ditangkap menunggu di Ruang Tamu; tersangka lain tersebar di ruangan lain."""
        ruangan_lain = iter(shuffle(self.rnd, [r for r in R_IDS if r != START]))
        self.loc     = {self.arrested: START}
        for x in S_IDS:
            if x != self.arrested:
                self.loc[x] = next(ruangan_lain)

    # MARK: - Private · Kesaksian

    def _buat_kesaksian(self):
        testimonies, sudah_diri = [], False
        for x in S_IDS:
            if not sudah_diri and self.rnd() < PELUANG_KESAKSIAN_DIRI:
                pernyataan, sudah_diri = _pernyataan_diri(x), True
            else:
                pernyataan = self._pernyataan_acak(x)
            testimonies.append(_kesaksian(x, pernyataan, self.loc[x]))
        return testimonies

    def _pernyataan_acak(self, x):
        jujur = x != self.sol.s
        return weighted_pick(self.rnd, [o for o in statement_options(self.found) if o['f'](self.sol) == jujur])

    # MARK: - Private · Bukti fisik (urutan dan isinya ikut menentukan kasus)

    def _kumpulkan_bukti_fisik(self):
        return (self._bukti_senjata() + self._bukti_ruangan_kosong() + self._bukti_jasad()
                + self._bukti_lantai() + self._bukti_alibi() + self._bukti_sepatu())

    def _bukti_senjata(self):
        sol, rnd = self.sol, self.rnd
        bukti = [_fisik(text, room, lambda m, w=w: m.w != w, [Atom('Utuh', C[w])])
                 for w in W_IDS if w != sol.w for text, room in [TANDA_SENJATA_UTUH[w]]]
        if sol.w in SENJATA_TANPA_DARAH:
            bukti.append(_fisik('Laporan forensik: tidak ada luka berdarah di tubuh korban.', 'kmandi',
                                lambda m: m.w in SENJATA_TANPA_DARAH, [Not(Atom('LukaBerdarah'))]))
        else:
            bukti.append(_fisik('Laporan forensik: ada luka berdarah di tubuh korban.', 'kmandi',
                                lambda m: m.w not in SENJATA_TANPA_DARAH, [Atom('LukaBerdarah')]))
        pemegang = shuffle(rnd, [sol.s, pick(rnd, self.innocents)]) if sol.w == 'racun' else shuffle(rnd, S_IDS)[:2]
        bukti.append(_fisik(f'Kunci lemari racun hanya dipegang {sn(pemegang[0])} dan {sn(pemegang[1])}.', 'gudang',
                            lambda m, kp=tuple(pemegang): m.w != 'racun' or m.s in kp,
                            _hanya('PegangKunci', pemegang, S_IDS)))
        return bukti

    def _bukti_ruangan_kosong(self):
        return [_fisik(TANDA_RUANGAN_KOSONG[t], t, lambda m, t=t: m.r != t, [Atom('Kosong', C[t])])
                for t in TKP if t not in (self.sol.r, self.found)]

    def _bukti_jasad(self):
        found, rnd = self.found, self.rnd
        if self.moved:
            bukti = [_fisik('Lebam mayat tidak sesuai dengan posisi jasad. Korban dipindahkan setelah meninggal.',
                            found, lambda m: m.r != found, [Atom('LebamTidakSesuai')])]
            pengalih = pick(rnd, [t for t in TKP if t not in (found, self.sol.r)])
            asal     = shuffle(rnd, [self.sol.r, pengalih])
            bukti.append(_fisik(f'Ada bekas seretan menuju {rn(found).lower()} dari arah {rn(asal[0]).lower()} '
                                f'atau {rn(asal[1]).lower()}.', found,
                                lambda m, tr=tuple(asal): m.r in tr, [Atom('AdaSeretan')] + _hanya('AsalSeretan', asal, TKP)))
        else:
            bukti = [_fisik('Lebam mayat sesuai dengan posisi jasad. Korban meninggal di tempat ia ditemukan.',
                            found, lambda m: m.r == found, [Atom('LebamSesuai')])]
        kuat = shuffle(rnd, [self.sol.s, pick(rnd, self.innocents)]) if self.moved else shuffle(rnd, S_IDS)[:2]
        bukti.append(_fisik(f'Korban bertubuh besar. Hanya {sn(kuat[0])} dan {sn(kuat[1])} yang cukup kuat untuk '
                            'memindahkan jasadnya.', None,
                            lambda m, st=tuple(kuat): m.r == found or m.s in st, _hanya('Kuat', kuat, S_IDS)))
        return bukti

    def _bukti_lantai(self):
        if self.sol.r in LANTAI_KAYU:
            return [_fisik('Serpihan kayu menempel di baju korban. Hanya perpustakaan dan kamar tidur yang berlantai '
                           'kayu.', 'kmandi', lambda m: m.r in LANTAI_KAYU, [Atom('SerpihanKayu')])]
        return [_fisik('Ada noda tanah dan air di baju korban. Hanya dapur dan taman yang lantainya basah malam itu.',
                       'kmandi', lambda m: m.r not in LANTAI_KAYU, [Atom('NodaBasah')])]

    def _bukti_alibi(self):
        rnd = self.rnd
        bukti = [_fisik(pick(rnd, TEKS_ALIBI).format(nama=sn(y)), None, lambda m, y=y: m.s != y, [Atom('AdaAlibi', C[y])])
                 for y in self.innocents]
        a, b = shuffle(rnd, self.innocents)[:2]
        bukti.append(_fisik(f'Foto di ponsel yang tertinggal: {sn(a)} dan {sn(b)} bermain catur bersama pukul '
                            f'{WAKTU_KEMATIAN}.', 'rmakan',
                            lambda m, a=a, b=b: m.s not in (a, b), [Atom('AdaAlibi', C[a]), Atom('AdaAlibi', C[b])]))
        return bukti

    def _bukti_sepatu(self):
        pemakai = shuffle(self.rnd, [self.sol.s, pick(self.rnd, self.innocents)])
        return [_fisik(f'Jejak sepatu ukuran 43 di dekat TKP. Hanya {sn(pemakai[0])} dan {sn(pemakai[1])} yang '
                       'memakai ukuran itu.', None,
                       lambda m, fp=tuple(pemakai): m.s in fp, [Atom('JejakSepatu43')] + _hanya('Ukuran43', pemakai, S_IDS))]

    # MARK: - Private · Bukti yang membuat jawaban unik

    def _pilih_bukti_penentu(self, pool, models):
        """Bukti diambil dalam urutan acak selama masih mempersempit jawaban, sampai jawaban
        tinggal satu, ditambah satu bukti cadangan. None kalau syarat kasus tidak terpenuhi."""
        order = shuffle(self.rnd, pool)
        chosen, models = _ambil_selama_mempersempit(order, models)
        if len(models) != 1:
            return None
        chosen += [c for c in order if not any(c is x for x in chosen)][:1]
        if not BUKTI_PENENTU_MIN <= len(chosen) <= BUKTI_PENENTU_MAX:
            return None
        if len(_jawaban_konsisten(chosen)) < MIN_JAWABAN_TANPA_KESAKSIAN:
            return None
        return chosen

    def _bukti_pengecoh(self):
        return [_fisik(t, None, lambda m: True, [Atom(p)]) for t, p in shuffle(self.rnd, TEKS_PENGECOH)[:JUMLAH_PENGECOH]]

    # MARK: - Private · Penempatan dan perakitan

    def _letakkan_bukti(self, physical):
        """Setiap bukti ke ruangan pilihannya kalau masih muat, selain itu ke ruangan acak.
        Ruang Tamu tidak dipakai karena sudah diperiksa polisi."""
        self.placeable = [r for r in R_IDS if r != START]
        isi            = {r: 0 for r in R_IDS}
        for c in shuffle(self.rnd, physical):
            room = c['pref'] if c['pref'] and isi[c['pref']] < MAKS_BUKTI_PER_RUANG else None
            if not room:
                room = shuffle(self.rnd, [r for r in self.placeable if isi[r] < MAKS_BUKTI_PER_RUANG])[0]
            c['room'] = room
            isi[room] += 1

    def _berkas_polisi(self):
        nama, konstanta = sn(self.arrested), C[self.arrested]
        motif = [
            (f'{nama} punya utang kepada korban.', Atom('PunyaUtang', konstanta)),
            (f'{nama} terlihat mondar-mandir di dekat rumah sore itu.', Atom('MondarMandir', konstanta)),
            (f'{nama} pernah bertengkar dengan korban minggu lalu.', Atom('PernahBertengkar', konstanta)),
            (f'Sidik jari {nama} ada di gagang pintu depan. Ia memang sering keluar-masuk rumah.',
             Atom('SidikJariDiPintu', konstanta)),
        ]
        dugaan_tkp = (f'Polisi menyimpulkan TKP-nya {rn(self.found).lower()} karena jasad ditemukan di sana.',
                      Atom('DugaanPolisiTKP', C[self.found]))
        items = [dugaan_tkp] + shuffle(self.rnd, motif)[:2]
        return [dict(kind='berkas', text=t, room=START, prop=lambda m: True, fol=[f]) for t, f in items]

    def _rakit(self, dossier, testimonies, physical):
        physical = sorted(physical, key=lambda c: self.placeable.index(c['room']))
        clues    = dossier + testimonies + physical
        for i, c in enumerate(clues):
            c['id'] = f'k{i + 1}'
            c['relevant'] = any(not c['prop'](m) for m in ALL_WORLDS)
            c.pop('pref', None)
        room_clues = {r: [] for r in R_IDS}
        for c in physical:
            room_clues[c['room']].append(c['id'])
        testimony_of = {c['speaker']: c['id'] for c in testimonies}
        return dict(sol=self.sol, arrested=self.arrested, found=self.found, moved=self.moved, loc=self.loc,
                    clues=clues, by_id={c['id']: c for c in clues}, room_clues=room_clues, testimony_of=testimony_of)


# MARK: - Private Helpers

def _pernyataan_diri(x):
    return dict(text='Aku bukan pelakunya.', f=lambda m: m.s != x, fol=Not(Atom('Pelaku', C[x])))


def _kesaksian(x, pernyataan, room):
    benar_di = pernyataan['f']
    return dict(
        kind='kesaksian', speaker=x, room=room, statement=pernyataan['text'], text=f'"{pernyataan["text"]}"',
        # v1: x tidak bersalah -> pernyataan benar, x pelaku -> pernyataan salah
        prop=lambda m: benar_di(m) == (m.s != x),
        # v2: hanya fakta "Jujur(x) ↔ pernyataan"; aturan ∀x Jujur(x) ↔ ¬Pelaku(x) ada di KB umum
        fol=[Iff(Atom('Jujur', C[x]), pernyataan['fol'])],
    )


def _fisik(text, pref, f, fol):
    """Bukti fisik. pref = ruangan yang paling cocok untuk meletakkannya (None = bebas)."""
    return dict(kind='fisik', text=text, pref=pref, prop=f, fol=fol)


def _hanya(pred, chosen, universe):
    """Fakta 'hanya A dan B yang ...': positif untuk yang disebut, negatif untuk sisanya."""
    return [Atom(pred, C[u]) if u in chosen else Not(Atom(pred, C[u])) for u in universe]


def _jawaban_konsisten(clues, models=ALL_WORLDS):
    return [m for m in models if all(c['prop'](m) for c in clues)]


def _ambil_selama_mempersempit(order, models):
    chosen = []
    for c in order:
        if len(models) == 1:
            break
        tersisa = [m for m in models if c['prop'](m)]
        if len(tersisa) < len(models):
            chosen.append(c)
            models = tersisa
    return chosen, models
