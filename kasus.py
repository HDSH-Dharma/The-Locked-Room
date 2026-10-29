"""
Data dan generator kasus Rumah Terkunci.

RNG-nya mulberry32 dengan urutan pemanggilan acak yang sama dengan versi web, jadi nomor
kasus yang sama selalu menghasilkan kasus yang sama. Sejak aturan proposal (kesaksian tidak
pernah menyebut pelaku asli), sebagian kasus berbeda dari versi web.

Aturan proposal yang dipegang generator:
- Kesaksian tidak pernah menyebut pelaku asli. Saksi jujur tidak pernah berkata "Aku yakin
  <pelaku> pelakunya"; pelaku boleh berbohong dengan menuduh orang lain.
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


def sn(i): return _SN[i]
def wn(i): return _WN[i]
def rn(i): return _RN[i]


ALL_WORLDS = [World(s, w, r) for s in S_IDS for w in W_IDS for r in TKP]


# ---------- RNG mulberry32 (sama persis dengan versi JavaScript) ----------
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


# ---------- kesaksian ----------
def statement_options(x, found):
    out = []
    f_low = rn(found).lower()
    out.append(dict(weight=1, text='Jasadnya pasti dipindahkan dari tempat lain.', f=lambda m: m.r != found,
                    fol=Atom('Dipindahkan')))
    out.append(dict(weight=1, text=f'Korban dibunuh di {f_low}, tempat jasadnya ditemukan.', f=lambda m: m.r == found,
                    fol=Atom('TKP', C[found])))
    for y in S_IDS:
        if y == x:
            continue
        out.append(dict(weight=2, text=f'{sn(y)} bukan pelakunya.', f=lambda m, y=y: m.s != y, fol=Not(Atom('Pelaku', C[y]))))
        out.append(dict(weight=2, text=f'Aku yakin {sn(y)} pelakunya.', f=lambda m, y=y: m.s == y, fol=Atom('Pelaku', C[y]),
                        menyebut=y))
    for w in W_IDS:
        low = wn(w).lower()
        out.append(dict(weight=1, text=f'Senjatanya bukan {low}.', f=lambda m, w=w: m.w != w, fol=Not(Atom('Senjata', C[w]))))
        out.append(dict(weight=1, text=f'Korban dibunuh dengan {low}.', f=lambda m, w=w: m.w == w, fol=Atom('Senjata', C[w])))
    for t in TKP:
        low = rn(t).lower()
        out.append(dict(weight=1, text=f'Kejadiannya bukan di {low}.', f=lambda m, t=t: m.r != t, fol=Not(Atom('TKP', C[t]))))
        out.append(dict(weight=1, text=f'Kejadiannya pasti di {low}.', f=lambda m, t=t: m.r == t, fol=Atom('TKP', C[t])))
    return out


def make_testimony(x, st, room):
    sf = st['f']
    return dict(
        kind='kesaksian', speaker=x, room=room, statement=st['text'], text=f'"{st["text"]}"',
        # v1: x tidak bersalah -> pernyataan benar, x pelaku -> pernyataan salah
        prop=lambda m: sf(m) == (m.s != x),
        # v2: hanya fakta "Jujur(x) ↔ pernyataan"; aturan ∀x Jujur(x) ↔ ¬Pelaku(x) ada di KB umum
        fol=[Iff(Atom('Jujur', C[x]), st['fol'])],
    )


def phys(text, pref, f, fol):
    return dict(kind='fisik', text=text, pref=pref, prop=f, fol=fol)


def only(pred, chosen, universe):
    """Fakta 'hanya A dan B yang ...': positif untuk yang disebut, negatif untuk sisanya."""
    return [Atom(pred, C[u]) if u in chosen else Not(Atom(pred, C[u])) for u in universe]


def _try_build(rnd):
    sol = World(pick(rnd, S_IDS), pick(rnd, W_IDS), pick(rnd, TKP))
    innocents = [i for i in S_IDS if i != sol.s]
    arrested = sol.s if rnd() < 0.3 else pick(rnd, innocents)
    found = sol.r if rnd() < 0.3 else pick(rnd, [t for t in TKP if t != sol.r])
    moved = found != sol.r
    f_name = rn(found)
    f_low = f_name.lower()

    other_rooms = shuffle(rnd, [r for r in R_IDS if r != START])
    loc = {arrested: START}
    k = 0
    for x in S_IDS:
        if x != arrested:
            loc[x] = other_rooms[k]
            k += 1

    testimonies = []
    self_used = False
    for x in S_IDS:
        honest = x != sol.s
        if not self_used and rnd() < 0.25:
            st = dict(text='Aku bukan pelakunya.', f=lambda m, x=x: m.s != x, fol=Not(Atom('Pelaku', C[x])))
            self_used = True
        else:
            # Kesaksian tidak pernah menyebut pelaku asli (proposal).
            st = weighted_pick(rnd, [o for o in statement_options(x, found)
                                     if o['f'](sol) == honest and o.get('menyebut') != sol.s])
        testimonies.append(make_testimony(x, st, loc[x]))
    models = [m for m in ALL_WORLDS if all(t['prop'](m) for t in testimonies)]
    if len(models) <= 4:
        return None

    pool = []
    weapon_flavor = {
        'pisau': ('Semua pisau di rak dapur lengkap dan bersih.', 'dapur'),
        'racun': ('Botol racun tikus di gudang masih tersegel rapat.', 'gudang'),
        'tali': ('Satu-satunya gulungan tali di rumah masih tersegel di loteng.', 'loteng'),
        'vas': ('Semua vas di rumah utuh, tidak ada yang retak atau hilang.', 'rmakan'),
    }
    for w in W_IDS:
        if w != sol.w:
            text, room = weapon_flavor[w]
            pool.append(phys(text, room, lambda m, w=w: m.w != w, [Atom('Utuh', C[w])]))
    if sol.w in ('racun', 'tali'):
        pool.append(phys('Laporan forensik: tidak ada luka berdarah di tubuh korban.', 'kmandi',
                         lambda m: m.w in ('racun', 'tali'), [Not(Atom('LukaBerdarah'))]))
    else:
        pool.append(phys('Laporan forensik: ada luka berdarah di tubuh korban.', 'kmandi',
                         lambda m: m.w in ('pisau', 'vas'), [Atom('LukaBerdarah')]))
    key_pair = shuffle(rnd, [sol.s, pick(rnd, innocents)]) if sol.w == 'racun' else shuffle(rnd, S_IDS)[:2]
    pool.append(phys(f'Kunci lemari racun hanya dipegang {sn(key_pair[0])} dan {sn(key_pair[1])}.', 'gudang',
                     lambda m, kp=tuple(key_pair): m.w != 'racun' or m.s in kp, only('PegangKunci', key_pair, S_IDS)))

    room_flavor = {
        'kamar': 'Kamar tidur terkunci dari dalam dan kosong semalaman.',
        'perpus': 'Debu di lantai perpustakaan utuh, tidak ada yang masuk semalam.',
        'dapur': 'Rekaman CCTV dapur: tidak ada kejadian apa pun semalaman.',
        'taman': 'Tanah taman becek, tapi tidak ada satu pun jejak kaki.',
    }
    for t in TKP:
        if t != sol.r and t != found:
            pool.append(phys(room_flavor[t], t, lambda m, t=t: m.r != t, [Atom('Kosong', C[t])]))
    if moved:
        pool.append(phys('Lebam mayat tidak sesuai dengan posisi jasad. Korban dipindahkan setelah meninggal.', found,
                         lambda m: m.r != found, [Atom('LebamTidakSesuai')]))
        decoy = pick(rnd, [t for t in TKP if t != found and t != sol.r])
        trail = shuffle(rnd, [sol.r, decoy])
        pool.append(phys(f'Ada bekas seretan menuju {f_low} dari arah {rn(trail[0]).lower()} atau {rn(trail[1]).lower()}.', found,
                         lambda m, tr=tuple(trail): m.r in tr, [Atom('AdaSeretan')] + only('AsalSeretan', trail, TKP)))
    else:
        pool.append(phys('Lebam mayat sesuai dengan posisi jasad. Korban meninggal di tempat ia ditemukan.', found,
                         lambda m: m.r == found, [Atom('LebamSesuai')]))
    strong = shuffle(rnd, [sol.s, pick(rnd, innocents)]) if moved else shuffle(rnd, S_IDS)[:2]
    pool.append(phys(f'Korban bertubuh besar. Hanya {sn(strong[0])} dan {sn(strong[1])} yang cukup kuat untuk memindahkan jasadnya.', None,
                     lambda m, st=tuple(strong): m.r == found or m.s in st, only('Kuat', strong, S_IDS)))
    wood = ('perpus', 'kamar')
    if sol.r in wood:
        pool.append(phys('Serpihan kayu menempel di baju korban. Hanya perpustakaan dan kamar tidur yang berlantai kayu.', 'kmandi',
                         lambda m: m.r in wood, [Atom('SerpihanKayu')]))
    else:
        pool.append(phys('Ada noda tanah dan air di baju korban. Hanya dapur dan taman yang lantainya basah malam itu.', 'kmandi',
                         lambda m: m.r not in wood, [Atom('NodaBasah')]))

    alibi_texts = [
        lambda x: f'Struk minimarket: {x} berbelanja di luar rumah pukul 21.00–23.00.',
        lambda x: f'Satpam kompleks: {x} mengobrol di pos jaga pukul 21.00–23.00.',
        lambda x: f'Tiket bioskop atas nama {x}, pertunjukan pukul 20.45–23.10.',
    ]
    for y in innocents:
        pool.append(phys(pick(rnd, alibi_texts)(sn(y)), None, lambda m, y=y: m.s != y, [Atom('AdaAlibi', C[y])]))
    a, b = shuffle(rnd, innocents)[:2]
    pool.append(phys(f'Foto di ponsel yang tertinggal: {sn(a)} dan {sn(b)} bermain catur bersama pukul 21.00–23.00.', 'rmakan',
                     lambda m, a=a, b=b: m.s != a and m.s != b, [Atom('AdaAlibi', C[a]), Atom('AdaAlibi', C[b])]))
    fp = shuffle(rnd, [sol.s, pick(rnd, innocents)])
    pool.append(phys(f'Jejak sepatu ukuran 43 di dekat TKP. Hanya {sn(fp[0])} dan {sn(fp[1])} yang memakai ukuran itu.', None,
                     lambda m, fp=tuple(fp): m.s in fp, [Atom('JejakSepatu43')] + only('Ukuran43', fp, S_IDS)))

    order = shuffle(rnd, pool)
    chosen = []
    for c in order:
        if len(models) == 1:
            break
        nxt = [m for m in models if c['prop'](m)]
        if len(nxt) < len(models):
            chosen.append(c)
            models = nxt
    if len(models) != 1:
        return None
    spare = next((c for c in order if not any(c is x for x in chosen)), None)
    if spare is not None:
        chosen.append(spare)
    if len(chosen) < 4 or len(chosen) > 8:
        return None
    if len([m for m in ALL_WORLDS if all(c['prop'](m) for c in chosen)]) < 2:
        return None

    herring_texts = [
        ('Ada puntung rokok di dekat pagar.', 'PuntungRokok'),
        ('Jendela loteng terbuka sedikit.', 'JendelaLotengTerbuka'),
        ('Korban baru saja mengubah surat wasiatnya minggu lalu.', 'WasiatDiubah'),
        ('Ada dua gelas kopi setengah habis di meja.', 'DuaGelasKopi'),
        ('Lampu kamar mandi berkedip-kedip.', 'LampuBerkedip'),
        ('Anjing tetangga menggonggong sekitar pukul 22.00.', 'AnjingMenggonggong'),
    ]
    herrings = [phys(t, None, lambda m: True, [Atom(p)]) for t, p in shuffle(rnd, herring_texts)[:2]]

    cap = {r: 0 for r in R_IDS}
    placeable = [r for r in R_IDS if r != START]    # Ruang Tamu sudah diperiksa polisi
    for c in shuffle(rnd, chosen + herrings):
        room = c['pref'] if c['pref'] and cap[c['pref']] < 2 else None
        if not room:
            room = shuffle(rnd, [r for r in placeable if cap[r] < 2])[0]
        c['room'] = room
        cap[room] += 1

    A = C[arrested]
    dossier_texts = [
        (f'{sn(arrested)} punya utang kepada korban.', Atom('PunyaUtang', A)),
        (f'{sn(arrested)} terlihat mondar-mandir di dekat rumah sore itu.', Atom('MondarMandir', A)),
        (f'{sn(arrested)} pernah bertengkar dengan korban minggu lalu.', Atom('PernahBertengkar', A)),
        (f'Sidik jari {sn(arrested)} ada di gagang pintu depan. Ia memang sering keluar-masuk rumah.', Atom('SidikJariDiPintu', A)),
    ]
    dossier_items = [(f'Polisi menyimpulkan TKP-nya {f_low} karena jasad ditemukan di sana.', Atom('DugaanPolisiTKP', C[found]))] \
        + shuffle(rnd, dossier_texts)[:2]
    dossier = [dict(kind='berkas', text=t, room=START, prop=lambda m: True, fol=[f]) for t, f in dossier_items]

    physical = sorted(chosen + herrings, key=lambda c: placeable.index(c['room']))
    clues = dossier + testimonies + physical
    for i, c in enumerate(clues):
        c['id'] = f'k{i + 1}'
        c['relevant'] = any(not c['prop'](m) for m in ALL_WORLDS)
        c.pop('pref', None)
    room_clues = {r: [] for r in R_IDS}
    for c in clues:
        if c['kind'] == 'fisik':
            room_clues[c['room']].append(c['id'])
    testimony_of = {c['speaker']: c['id'] for c in clues if c['kind'] == 'kesaksian'}
    return dict(sol=sol, arrested=arrested, found=found, moved=moved, loc=loc, clues=clues,
                by_id={c['id']: c for c in clues}, room_clues=room_clues, testimony_of=testimony_of)


def generate_case(seed):
    for attempt in range(400):
        c = _try_build(make_rng(seed * 7919 + attempt * 104729 + 13))
        if c:
            c['seed'] = seed
            return c
    raise RuntimeError(f'Kasus gagal dibuat untuk nomor {seed}')


# ---------- denah ----------
def neighbors(room):
    r, c = POS[room]
    return [x for x in R_IDS if abs(POS[x][0] - r) + abs(POS[x][1] - c) == 1]
