"""
Teks untuk ditampilkan ke pemain dan di laporan (UI, transkrip, trace). Dipisah dari engine
supaya aturan permainan tidak bergantung pada cara menampilkannya.
"""
from kasus import sn, wn, rn

NAMA_JAWABAN = {'s': sn, 'w': wn, 'r': rn}
_TEKS_AKSI = {'pindah': 'pindah ke {}', 'teleport': 'teleport ke {}', 'geledah': 'menggeledah {}',
              'interogasi': 'menginterogasi {}'}
_FAKTA_PASTI = {'s': 'Pelaku pasti {}', 'w': 'Senjata pasti {}', 'r': 'TKP pasti {}'}
_FAKTA_GUGUR = {'s': '{} bukan pelaku', 'w': 'Senjata bukan {}', 'r': 'TKP bukan {}'}


def teks_aksi(act):
    jenis, target = act
    return _TEKS_AKSI[jenis].format(sn(target) if jenis == 'interogasi' else rn(target))


def teks_jawaban(m):
    return f'{sn(m.s)} · {wn(m.w)} · {rn(m.r)}'


def teks_bukti(case, cid):
    """Bukti beserta asalnya: siapa yang bersaksi, berkas polisi, atau ruangan tempat ditemukan."""
    c = case['by_id'][cid]
    if c['kind'] == 'kesaksian':
        return f'{sn(c["speaker"])}: {c["text"]}'
    if c['kind'] == 'berkas':
        return f'Berkas polisi: {c["text"]}'
    return f'{c["text"]} ({rn(c["room"])})'


def fakta(kategori, nilai, status):
    """Kesimpulan baru dari ASK, misalnya 'Pelaku pasti Dimas' atau 'TKP bukan Dapur'."""
    templat = _FAKTA_PASTI if status == 'pasti' else _FAKTA_GUGUR
    return templat[kategori].format(NAMA_JAWABAN[kategori](nilai))


def target_menguping(data):
    """Target aksi yang terdengar saat menguping: nama ruangan untuk geledah, nama tersangka untuk interogasi."""
    return rn(data['target']) if data['jenis'] == 'geledah' else sn(data['target'])
