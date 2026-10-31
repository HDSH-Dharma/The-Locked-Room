"""
denah.py
Logic — ganti denah, jarak antar-ruangan (dengan atau tanpa teleport), dan letak teleport.

- Teleport: lompat serong 1 atau 2 kotak, 1 aksi, sekali pakai.
- pakai_denah() mengganti isi struktur denah di rumah_model secara in-place, sehingga semua modul
  yang sudah mengimpor R_IDS, POS, dan NAMA_RUANGAN ikut memakai denah baru.
"""
from collections import deque

from logic.kasus.acak import make_rng, pick
from logic.kasus.rumah import neighbors
from model.denah_model import LAYOUTS
from model.rumah_model import NAMA_RUANGAN, POS, R_IDS, ROOMS, START

# MARK: - State

_aktif = ['9']


# MARK: - Denah

def pakai_denah(nama):
    """Ganti denah aktif. Struktur di rumah_model diubah in-place."""
    if _aktif[0] == nama:
        return
    rooms = LAYOUTS[nama]
    ROOMS[:] = rooms
    R_IDS[:] = [r[0] for r in rooms]
    NAMA_RUANGAN.clear()
    NAMA_RUANGAN.update({r[0]: r[1] for r in rooms})
    POS.clear()
    POS.update({r[0]: (r[2], r[3]) for r in rooms})
    _aktif[0] = nama


def serong(room):
    """Ruangan yang bisa dicapai teleport: serong 1 atau 2 kotak dalam satu garis lurus."""
    r, c = POS[room]
    out = []
    for k in (1, 2):
        for dr in (-k, k):
            for dc in (-k, k):
                for x in R_IDS:
                    if POS[x] == (r + dr, c + dc):
                        out.append(x)
    return out


# MARK: - Jarak dan rute

def jarak(pos, punya_tp=False):
    """(jarak tanpa teleport, jarak kalau teleport boleh dipakai) ke setiap ruangan."""
    tanpa_tp  = _jarak_per_ruang(_bfs(pos, False))
    dengan_tp = _jarak_per_ruang(_bfs(pos, True)) if punya_tp else tanpa_tp
    return tanpa_tp, dengan_tp


def langkah_pertama(pos, goal, pakai_tp):
    """Aksi pertama di rute terpendek ke goal. pakai_tp=False berarti jalan biasa saja."""
    parent = _bfs(pos, pakai_tp)
    ends   = [s for s in parent if s[0] == goal]
    end    = min(ends, key=lambda s: _depth(parent, s))
    acts, cur = [], end
    while parent[cur]:
        cur, act = parent[cur]
        acts.append(act)
    return acts[-1] if acts else None


# MARK: - Teleport

def letakkan_teleport(case):
    """Teleport disembunyikan di salah satu ruangan berisi bukti (bukan Ruang Tamu). Memakai
    aliran acak terpisah, jadi isi kasus (pelaku, bukti, letak bukti) tidak berubah."""
    rnd      = make_rng(case['seed'] * 2654435761 + 97)
    kandidat = [r for r in R_IDS if r != START and case['room_clues'][r]]
    case['teleport'] = pick(rnd, kandidat)


# MARK: - Private Helpers

def _bfs(start, punya_tp):
    """BFS atas state (ruangan, masih punya teleport). Jalan biasa dicoba lebih dulu,
    jadi kalau panjangnya sama, rute tanpa teleport yang ditemukan duluan."""
    s0       = (start, punya_tp)
    parent   = {s0: None}
    frontier = deque([s0])
    while frontier:
        cur = frontier.popleft()
        room, tp = cur
        berikut = [(('pindah', nb), (nb, tp)) for nb in neighbors(room)]
        if tp:
            berikut += [(('teleport', tujuan), (tujuan, False)) for tujuan in serong(room)]
        for act, nxt in berikut:
            if nxt not in parent:
                parent[nxt] = (cur, act)
                frontier.append(nxt)
    return parent


def _jarak_per_ruang(parent):
    """Jarak terpendek ke setiap ruangan dari pohon BFS (state = (ruangan, punya teleport))."""
    hasil = {}
    for s in parent:
        hasil[s[0]] = min(hasil.get(s[0], 99), _depth(parent, s))
    return hasil


def _depth(parent, s):
    d = 0
    while parent[s]:
        s = parent[s][0]
        d += 1
    return d
