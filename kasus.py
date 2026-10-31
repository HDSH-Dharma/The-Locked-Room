"""
Data dan generator kasus Rumah Terkunci.

Nomor kasus yang sama selalu menghasilkan kasus yang sama: RNG-nya mulberry32 dan urutan
pemanggilan acaknya tetap. Jangan menyisipkan, menghapus, atau menukar urutan pemanggilan
rnd() di PembuatKasus tanpa sengaja, karena semua kasus akan ikut berubah dan log lama tidak
bisa di-replay lagi.

Aturan proposal yang dipegang generator:
- Kesaksian tidak pernah menyebut pelaku asli. Kesaksian juga tidak menyebut tersangka lain:
  dengan aturan ini, "Aku yakin Y pelakunya" hanya bisa diucapkan pelaku (langsung membongkar
  pelakunya) dan "Y bukan pelakunya" hanya bisa diucapkan saksi jujur. Pelaku hanya bisa
  ditemukan dengan mencocokkan kesaksian dengan bukti lain.
- Ruang Tamu sudah diperiksa polisi (isinya berkas polisi), jadi tidak ada bukti fisik di sana.

Setiap bukti punya DUA representasi:
- `prop`  : fungsi atas dunia (pelaku, senjata, TKP), dipakai agen v1 (proposisional)
- `fol`   : daftar fakta FOL, dipakai agen v2 (FOL + resolusi). Aturan umumnya ada
            di agen_v2.ATURAN; bukti hanya menambahkan fakta.
"""
from collections import namedtuple
from fol import Atom, Not, Iff

World = namedtuple('World', 's w r')

SUSPECTS = [
    ('budi', 'Pak Budi', 'Tukang kebun', 'Budi'),
    ('sari', 'Bu Sari', 'Koki', 'Sari'),
    ('dimas', 'Dimas', 'Keponakan korban', 'Dimas'),
    ('nadia', 'Nadia', 'Sekretaris', 'Nadia'),
]
WEAPONS = [('pisau', 'Pisau'), ('racun', 'Racun'), ('tali', 'Tali'), ('vas', 'Vas')]
ROOMS = [
    ('gudang', 'Gudang', 0, 0), ('loteng', 'Loteng', 0, 1), ('kamar', 'Kamar Tidur', 0, 2),
    ('perpus', 'Perpustakaan', 1, 0), ('dapur', 'Dapur', 1, 1), ('kmandi', 'Kamar Mandi', 1, 2),
    ('rtamu', 'Ruang Tamu', 2, 0), ('rmakan', 'Ruang Makan', 2, 1), ('taman', 'Taman', 2, 2),
]
TKP = ['perpus', 'dapur', 'kamar', 'taman']
START = 'rtamu'           # Ruang Tamu: titik awal, sudah diperiksa polisi
MAX_ROUNDS = 7
WAKTU_KEMATIAN = '21.00–23.00'

S_IDS = [s[0] for s in SUSPECTS]
W_IDS = [w[0] for w in WEAPONS]
R_IDS = [r[0] for r in ROOMS]
_SN = {s[0]: s[1] for s in SUSPECTS}
_WN = dict(WEAPONS)
_RN = {r[0]: r[1] for r in ROOMS}
POS = {r[0]: (r[2], r[3]) for r in ROOMS}

# Konstanta FOL
C = {s[0]: s[3] for s in SUSPECTS}
C.update({w[0]: w[1] for w in WEAPONS})
C.update({'perpus': 'Perpustakaan', 'dapur': 'Dapur', 'kamar': 'KamarTidur', 'taman': 'Taman'})
DOMAIN = {
    'orang': [C[s] for s in S_IDS],
    'senjata': [C[w] for w in W_IDS],
    'ruang': [C[r] for r in TKP],
}


def sn(i):
    """Nama tersangka untuk ditampilkan."""
    return _SN[i]


def wn(i):
    """Nama senjata untuk ditampilkan."""
    return _WN[i]


def rn(i):
    """Nama ruangan untuk ditampilkan."""
    return _RN[i]


ALL_WORLDS = [World(s, w, r) for s in S_IDS for w in W_IDS for r in TKP]


# ---------- RNG mulberry32 (disalin persis dari versi JavaScript awal) ----------
MASK = 0xFFFFFFFF


def _imul(a, b):
    return (a * b) & MASK


def make_rng(seed):
    state = [seed & MASK]

    def rnd():
        a = (state[0] + 0x6D2B79F5) & MASK
        state[0] = a
        t = _imul(a ^ (a >> 15), 1 | a)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & MASK) ^ t
        return ((t ^ (t >> 14)) & MASK) / 4294967296
    return rnd


def pick(rnd, arr):
    return arr[int(rnd() * len(arr))]


def shuffle(rnd, arr):
    a = list(arr)
    for i in range(len(a) - 1, 0, -1):
        j = int(rnd() * (i + 1))
        a[i], a[j] = a[j], a[i]
    return a


def weighted_pick(rnd, opts):
    total = sum(o['weight'] for o in opts)
    x = rnd() * total
    for o in opts:
        x -= o['weight']
        if x <= 0:
            return o
    return opts[-1]


# ---------- parameter generator ----------
PELUANG_TANGKAP_PELAKU = 0.3        # polisi kebetulan menangkap pelaku asli
PELUANG_JASAD_DI_TKP = 0.3          # jasad tidak dipindahkan dari TKP
PELUANG_KESAKSIAN_DIRI = 0.25       # tersangka hanya berkata "Aku bukan pelakunya." (paling banyak satu)
MIN_MODEL_SETELAH_KESAKSIAN = 5     # kesaksian saja tidak boleh mempersempit jawaban terlalu jauh
BUKTI_PENENTU_MIN, BUKTI_PENENTU_MAX = 4, 8
MIN_JAWABAN_TANPA_KESAKSIAN = 2     # bukti fisik saja tidak cukup: kesaksian harus ikut dipakai
JUMLAH_PENGECOH = 2
MAKS_BUKTI_PER_RUANG = 2
BATAS_PERCOBAAN = 400
LANTAI_KAYU = ('perpus', 'kamar')
SENJATA_TANPA_DARAH = ('racun', 'tali')

_TANDA_SENJATA_UTUH = {
    'pisau': ('Semua pisau di rak dapur lengkap dan bersih.', 'dapur'),
    'racun': ('Botol racun tikus di gudang masih tersegel rapat.', 'gudang'),
    'tali': ('Satu-satunya gulungan tali di rumah masih tersegel di loteng.', 'loteng'),
    'vas': ('Semua vas di rumah utuh, tidak ada yang retak atau hilang.', 'rmakan'),
}
_TANDA_RUANGAN_KOSONG = {
    'kamar': 'Kamar tidur terkunci dari dalam dan kosong semalaman.',
    'perpus': 'Debu di lantai perpustakaan utuh, tidak ada yang masuk semalam.',
    'dapur': 'Rekaman CCTV dapur: tidak ada kejadian apa pun semalaman.',
    'taman': 'Tanah taman becek, tapi tidak ada satu pun jejak kaki.',
}
_TEKS_ALIBI = [
    lambda nama: f'Struk minimarket: {nama} berbelanja di luar rumah pukul {WAKTU_KEMATIAN}.',
    lambda nama: f'Satpam kompleks: {nama} mengobrol di pos jaga pukul {WAKTU_KEMATIAN}.',
    lambda nama: f'Tiket bioskop atas nama {nama}, pertunjukan pukul 20.45–23.10.',
]
_TEKS_PENGECOH = [
    ('Ada puntung rokok di dekat pagar.', 'PuntungRokok'),
    ('Jendela loteng terbuka sedikit.', 'JendelaLotengTerbuka'),
    ('Korban baru saja mengubah surat wasiatnya minggu lalu.', 'WasiatDiubah'),
    ('Ada dua gelas kopi setengah habis di meja.', 'DuaGelasKopi'),
    ('Lampu kamar mandi berkedip-kedip.', 'LampuBerkedip'),
    ('Anjing tetangga menggonggong sekitar pukul 22.00.', 'AnjingMenggonggong'),
]


# ---------- bentuk bukti ----------
def statement_options(found):
    """Pernyataan yang bisa diucapkan saksi. Saksi jujur memilih yang benar, pelaku yang salah.
    Tidak ada pernyataan yang menyebut tersangka lain (lihat docstring modul)."""
    out = []
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


# ---------- generator ----------
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
        models = _jawaban_konsisten(testimonies)
        if len(models) < MIN_MODEL_SETELAH_KESAKSIAN:
            return None
        chosen = self._pilih_bukti_penentu(self._kumpulkan_bukti_fisik(), models)
        if chosen is None:
            return None
        physical = chosen + self._bukti_pengecoh()
        self._letakkan_bukti(physical)
        return self._rakit(self._berkas_polisi(), testimonies, physical)

    # ---- jawaban, penangkapan, dan posisi tersangka ----
    def _pilih_jawaban(self):
        rnd = self.rnd
        self.sol = World(pick(rnd, S_IDS), pick(rnd, W_IDS), pick(rnd, TKP))
        self.innocents = [i for i in S_IDS if i != self.sol.s]
        self.arrested = self.sol.s if rnd() < PELUANG_TANGKAP_PELAKU else pick(rnd, self.innocents)
        self.found = self.sol.r if rnd() < PELUANG_JASAD_DI_TKP else pick(rnd, [t for t in TKP if t != self.sol.r])
        self.moved = self.found != self.sol.r

    def _tempatkan_tersangka(self):
        """Yang ditangkap menunggu di Ruang Tamu; tersangka lain tersebar di ruangan lain."""
        ruangan_lain = iter(shuffle(self.rnd, [r for r in R_IDS if r != START]))
        self.loc = {self.arrested: START}
        for x in S_IDS:
            if x != self.arrested:
                self.loc[x] = next(ruangan_lain)

    # ---- kesaksian ----
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

    # ---- bukti fisik (urutan dan isinya ikut menentukan kasus) ----
    def _kumpulkan_bukti_fisik(self):
        return (self._bukti_senjata() + self._bukti_ruangan_kosong() + self._bukti_jasad()
                + self._bukti_lantai() + self._bukti_alibi() + self._bukti_sepatu())

    def _bukti_senjata(self):
        sol, rnd = self.sol, self.rnd
        bukti = [_fisik(text, room, lambda m, w=w: m.w != w, [Atom('Utuh', C[w])])
                 for w in W_IDS if w != sol.w for text, room in [_TANDA_SENJATA_UTUH[w]]]
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
        return [_fisik(_TANDA_RUANGAN_KOSONG[t], t, lambda m, t=t: m.r != t, [Atom('Kosong', C[t])])
                for t in TKP if t not in (self.sol.r, self.found)]

    def _bukti_jasad(self):
        found, rnd = self.found, self.rnd
        if self.moved:
            bukti = [_fisik('Lebam mayat tidak sesuai dengan posisi jasad. Korban dipindahkan setelah meninggal.',
                            found, lambda m: m.r != found, [Atom('LebamTidakSesuai')])]
            pengalih = pick(rnd, [t for t in TKP if t not in (found, self.sol.r)])
            asal = shuffle(rnd, [self.sol.r, pengalih])
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
        bukti = [_fisik(pick(rnd, _TEKS_ALIBI)(sn(y)), None, lambda m, y=y: m.s != y, [Atom('AdaAlibi', C[y])])
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

    # ---- memilih bukti yang membuat jawaban unik ----
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
        return [_fisik(t, None, lambda m: True, [Atom(p)]) for t, p in shuffle(self.rnd, _TEKS_PENGECOH)[:JUMLAH_PENGECOH]]

    # ---- penempatan dan perakitan ----
    def _letakkan_bukti(self, physical):
        """Setiap bukti ke ruangan pilihannya kalau masih muat, selain itu ke ruangan acak.
        Ruang Tamu tidak dipakai karena sudah diperiksa polisi."""
        self.placeable = [r for r in R_IDS if r != START]
        isi = {r: 0 for r in R_IDS}
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
        clues = dossier + testimonies + physical
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


def generate_case(seed):
    for attempt in range(BATAS_PERCOBAAN):
        case = PembuatKasus(make_rng(seed * 7919 + attempt * 104729 + 13)).buat()
        if case:
            case['seed'] = seed
            return case
    raise RuntimeError(f'Kasus gagal dibuat untuk nomor {seed}')


# ---------- denah ----------
def neighbors(room):
    r, c = POS[room]
    return [x for x in R_IDS if abs(POS[x][0] - r) + abs(POS[x][1] - c) == 1]
