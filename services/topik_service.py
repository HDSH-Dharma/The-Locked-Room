"""
topik_service.py
Service — topik bukti untuk fitur menguping.

Menguping hanya memberi TOPIK bukti (tersangka, senjata, ruangan, jasad), bukan isinya. Topik bukan
fakta logika, jadi tidak masuk KB; agen memakainya untuk memilih tujuan.
"""
from models.topik_model import TOPIK_PREDIKAT

# MARK: - Indeks

_PRED_KE_TOPIK = {p: t for t, ps in TOPIK_PREDIKAT.items() for p in ps}


# MARK: - Topik

def kunci_topik(jenis, target):
    """Kunci catatan menguping: ('r', ruangan) untuk geledah, ('s', tersangka) untuk interogasi."""
    return ('r' if jenis == 'geledah' else 's', target)


def topik(clue):
    if clue['kind'] == 'berkas':
        return 'berkas'
    return _PRED_KE_TOPIK.get(_atom_pertama(clue['fol'][0]), 'tersangka')


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


# MARK: - Private Helpers

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
