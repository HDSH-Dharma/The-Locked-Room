"""
teks.py
Logic — teks tampilan untuk UI dan laporan: aksi, jawaban, bukti, kesimpulan, dan rencana.
Template teksnya ada di teks_model. Dipisah dari engine supaya aturan permainan tidak bergantung
pada cara menampilkannya.
"""
from logic.kasus.rumah import rn, sn, wn
from model.teks_model import FAKTA_GUGUR, FAKTA_PASTI, TEKS_AKSI

# MARK: - Indeks

NAMA_JAWABAN = {'s': sn, 'w': wn, 'r': rn}


# MARK: - Teks

def teks_aksi(act):
    jenis, target = act
    return TEKS_AKSI[jenis].format(sn(target) if jenis == 'interogasi' else rn(target))


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
    templat = FAKTA_PASTI if status == 'pasti' else FAKTA_GUGUR
    return templat[kategori].format(NAMA_JAWABAN[kategori](nilai))


def target_menguping(data):
    """Target aksi yang terdengar saat menguping: nama ruangan untuk geledah, nama tersangka untuk interogasi."""
    return rn(data['target']) if data['jenis'] == 'geledah' else sn(data['target'])


def teks_rencana(plan):
    """Rencana sebagai teks untuk trace, misalnya ['Pindah(Dapur)', 'Geledah(Dapur)']."""
    return [f'{a.capitalize()}({sn(b) if a == "interogasi" else rn(b)})' for a, b in plan]
