"""
Denah rumah (9, 12, atau 16 ruangan), teleport, dan topik untuk menguping.

- Denah 9 ruangan identik dengan versi web, jadi nomor kasus yang sama tetap menghasilkan
  kasus yang sama. Denah 12 dan 16 menambah kolom/baris baru; Ruang Tamu tetap start.
- Teleport: lompat serong 1 atau 2 kotak, 1 aksi, sekali pakai.
- Menguping hanya memberi TOPIK bukti (tersangka, senjata, ruangan, jasad), bukan isinya.
  Topik bukan fakta logika, jadi tidak masuk KB; agen memakainya untuk memilih tujuan.

pakai_denah() mengganti isi struktur denah di modul kasus secara in-place, sehingga semua
modul yang sudah mengimpor R_IDS, neighbors, dan rn ikut memakai denah baru.
"""
from collections import deque
import kasus

LAYOUTS = {
    '9': [
        ('gudang', 'Gudang', 0, 0), ('loteng', 'Loteng', 0, 1), ('kamar', 'Kamar Tidur', 0, 2),
        ('perpus', 'Perpustakaan', 1, 0), ('dapur', 'Dapur', 1, 1), ('kmandi', 'Kamar Mandi', 1, 2),
        ('rtamu', 'Ruang Tamu', 2, 0), ('rmakan', 'Ruang Makan', 2, 1), ('taman', 'Taman', 2, 2),
    ],
    '12': [
        ('gudang', 'Gudang', 0, 0), ('loteng', 'Loteng', 0, 1), ('kamar', 'Kamar Tidur', 0, 2), ('balkon', 'Balkon', 0, 3),
        ('perpus', 'Perpustakaan', 1, 0), ('dapur', 'Dapur', 1, 1), ('kmandi', 'Kamar Mandi', 1, 2), ('rkerja', 'Ruang Kerja', 1, 3),
        ('rtamu', 'Ruang Tamu', 2, 0), ('rmakan', 'Ruang Makan', 2, 1), ('taman', 'Taman', 2, 2), ('garasi', 'Garasi', 2, 3),
    ],
    '16': [
        ('gudang', 'Gudang', 0, 0), ('loteng', 'Loteng', 0, 1), ('kamar', 'Kamar Tidur', 0, 2), ('balkon', 'Balkon', 0, 3),
        ('perpus', 'Perpustakaan', 1, 0), ('dapur', 'Dapur', 1, 1), ('kmandi', 'Kamar Mandi', 1, 2), ('rkerja', 'Ruang Kerja', 1, 3),
        ('rmusik', 'Ruang Musik', 2, 0), ('rmakan', 'Ruang Makan', 2, 1), ('taman', 'Taman', 2, 2), ('garasi', 'Garasi', 2, 3),
        ('rtamu', 'Ruang Tamu', 3, 0), ('teras', 'Teras', 3, 1), ('kolam', 'Kolam Renang', 3, 2), ('gazebo', 'Gazebo', 3, 3),
    ],
}
_aktif = ['9']


def pakai_denah(nama):
    """Ganti denah aktif. Struktur di modul kasus diubah in-place."""
    if _aktif[0] == nama:
        return
    rooms = LAYOUTS[nama]
    kasus.ROOMS[:] = rooms
    kasus.R_IDS[:] = [r[0] for r in rooms]
    kasus._RN.clear()
    kasus._RN.update({r[0]: r[1] for r in rooms})
    kasus.POS.clear()
    kasus.POS.update({r[0]: (r[2], r[3]) for r in rooms})
    _aktif[0] = nama


def denah_aktif():
    return _aktif[0]


def serong(room):
    """Ruangan yang bisa dicapai teleport: serong 1 atau 2 kotak dalam satu garis lurus."""
    r, c = kasus.POS[room]
    out = []
    for k in (1, 2):
        for dr in (-k, k):
            for dc in (-k, k):
                for x in kasus.R_IDS:
                    if kasus.POS[x] == (r + dr, c + dc):
                        out.append(x)
    return out


# ---------- rute dengan teleport ----------
def _bfs(start, punya_tp):
    """BFS atas state (ruangan, masih punya teleport). Jalan biasa dicoba lebih dulu,
    jadi kalau panjangnya sama, rute tanpa teleport yang ditemukan duluan."""
    s0 = (start, punya_tp)
    parent = {s0: None}
    q = deque([s0])
    while q:
        cur = q.popleft()
        room, tp = cur
        nexts = [(('pindah', nb), (nb, tp)) for nb in kasus.neighbors(room)]
        if tp:
            nexts += [(('teleport', d), (d, False)) for d in serong(room)]
        for act, nxt in nexts:
            if nxt not in parent:
                parent[nxt] = (cur, act)
                q.append(nxt)
    return parent


def _dist(parent):
    depth = {}
    for s in parent:
        d, cur = 0, s
        while parent[cur]:
            cur = parent[cur][0]
            d += 1
        room = s[0]
        depth[room] = min(depth.get(room, 99), d)
    return depth


def jarak(pos, punya_tp=False):
    """(jarak tanpa teleport, jarak kalau teleport boleh dipakai) ke setiap ruangan."""
    d0 = _dist(_bfs(pos, False))
    d1 = _dist(_bfs(pos, True)) if punya_tp else d0
    return d0, d1


def langkah_pertama(pos, goal, pakai_tp):
    """Aksi pertama di rute terpendek ke goal. pakai_tp=False berarti jalan biasa saja."""
    parent = _bfs(pos, pakai_tp)
    ends = [s for s in parent if s[0] == goal]
    end = min(ends, key=lambda s: _depth(parent, s))
    acts, cur = [], end
    while parent[cur]:
        cur, act = parent[cur]
        acts.append(act)
    return acts[-1] if acts else None


def _depth(parent, s):
    d = 0
    while parent[s]:
        s = parent[s][0]
        d += 1
    return d


# ---------- topik untuk menguping ----------
TOPIK_PREDIKAT = {
    'tersangka': {'Pelaku', 'AdaAlibi', 'Kuat', 'PegangKunci', 'Ukuran43', 'JejakSepatu43',
                  'PuntungRokok', 'WasiatDiubah', 'DuaGelasKopi'},
    'senjata': {'Senjata', 'Utuh', 'LukaBerdarah'},
    'ruangan': {'TKP', 'Kosong', 'SerpihanKayu', 'NodaBasah', 'JendelaLotengTerbuka', 'LampuBerkedip'},
    'jasad': {'Dipindahkan', 'LebamTidakSesuai', 'LebamSesuai', 'AdaSeretan', 'AnjingMenggonggong'},
}
_PRED_KE_TOPIK = {p: t for t, ps in TOPIK_PREDIKAT.items() for p in ps}


def _atom_pertama(f):
    if f[0] == 'atom':
        return f[1]
    if f[0] == 'not':
        return _atom_pertama(f[1])
    if f[0] == 'iff':          # kesaksian: Jujur(x) ↔ pernyataan → topik dari pernyataan
        return _atom_pertama(f[2])
    for sub in f[1] if f[0] in ('and', 'or') else ():
        return _atom_pertama(sub)
    return None


def topik(clue):
    if clue['kind'] == 'berkas':
        return 'berkas'
    return _PRED_KE_TOPIK.get(_atom_pertama(clue['fol'][0]), 'tersangka')


def lengkapi(case):
    """Tambahkan letak teleport dan topik tiap bukti. Memakai aliran acak terpisah,
    jadi isi kasus (pelaku, bukti, letak bukti) tidak berubah."""
    rnd = kasus.make_rng(case['seed'] * 2654435761 + 97)
    cands = [r for r in kasus.R_IDS if r != kasus.START and case['room_clues'][r]]
    case['teleport'] = kasus.pick(rnd, cands)
    for c in case['clues']:
        c['topik'] = topik(c)
    return case


def topik_terbuka(t, terbuka):
    """Apakah bukti bertopik t masih bisa berguna, diberi kategori jawaban yang belum pasti."""
    if t == 'jasad':
        return terbuka['ruangan'] or terbuka['tersangka']
    return terbuka.get(t, False)


def nilai_target(topik_dict, key, bawaan, terbuka):
    """Nilai sebuah target (ruangan atau tersangka). Kalau topiknya pernah terdengar,
    hanya bukti bertopik terbuka yang dihitung."""
    if key not in topik_dict:
        return bawaan
    n = sum(1 for t in topik_dict[key] if topik_terbuka(t, terbuka))
    return n * (1.2 if key[0] == 's' else 1)
