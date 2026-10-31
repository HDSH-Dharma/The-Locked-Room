"""
aturan_model.py
Model — basis pengetahuan umum Detektif AI v2: 18 aturan FOL berkuantor dan pengetahuan latar.
Data saja; instansiasi dan resolusinya ada di kb_service dan resolusi_service.

Aturan umum ditulis SEKALI dengan kuantor; setiap bukti hanya menambah fakta, misalnya
AdaAlibi(Budi) atau Kuat(Dimas).
"""
from models.fol_model import Atom, Not, And, Imp, Iff, ForAll, Exists, Neq

# MARK: - Variabel

x, y, w, r = '?x', '?y', '?w', '?r'


# MARK: - Singkatan supaya aturan terbaca seperti notasi logika di slide

def P(a):
    return Atom('Pelaku', a)


def S(a):
    return Atom('Senjata', a)


def T(a):
    return Atom('TKP', a)


# MARK: - Aturan umum (berkuantor)

ATURAN = [
    ('R1', 'Pasti ada tepat satu pelaku',
     And(Exists(x, 'orang', P(x)), ForAll(x, 'orang', ForAll(y, 'orang', Imp(Neq(x, y), Not(And(P(x), P(y)))))))),
    ('R2', 'Pasti ada tepat satu senjata',
     And(Exists(w, 'senjata', S(w)), ForAll(w, 'senjata', ForAll(y, 'senjata', Imp(Neq(w, y), Not(And(S(w), S(y)))))))),
    ('R3', 'Pasti ada tepat satu TKP',
     And(Exists(r, 'ruang', T(r)), ForAll(r, 'ruang', ForAll(y, 'ruang', Imp(Neq(r, y), Not(And(T(r), T(y)))))))),
    ('R4', 'Saksi pembohong: jujur jika dan hanya jika bukan pelaku',
     ForAll(x, 'orang', Iff(Atom('Jujur', x), Not(P(x))))),
    ('R5', 'Punya alibi berarti bukan pelaku',
     ForAll(x, 'orang', Imp(Atom('AdaAlibi', x), Not(P(x))))),
    ('R6', 'Benda yang utuh bukan senjata',
     ForAll(w, 'senjata', Imp(Atom('Utuh', w), Not(S(w))))),
    ('R7', 'Ruangan yang kosong semalaman bukan TKP',
     ForAll(r, 'ruang', Imp(Atom('Kosong', r), Not(T(r))))),
    ('R8', 'Luka berdarah jika dan hanya jika senjatanya senjata berdarah',
     Iff(Atom('LukaBerdarah'), Exists(w, 'senjata', And(S(w), Atom('Berdarah', w))))),
    ('R9', 'Serpihan kayu berarti TKP berlantai kayu',
     Imp(Atom('SerpihanKayu'), Exists(r, 'ruang', And(T(r), Atom('LantaiKayu', r))))),
    ('R10', 'Noda tanah dan air berarti TKP berlantai basah',
     Imp(Atom('NodaBasah'), Exists(r, 'ruang', And(T(r), Atom('LantaiBasah', r))))),
    ('R11', 'Jasad dipindahkan jika dan hanya jika tempat ditemukan bukan TKP',
     ForAll(r, 'ruang', Imp(Atom('DitemukanDi', r), Iff(Atom('Dipindahkan'), Not(T(r)))))),
    ('R12', 'Lebam tidak sesuai posisi berarti jasad dipindahkan',
     Imp(Atom('LebamTidakSesuai'), Atom('Dipindahkan'))),
    ('R13', 'Lebam sesuai posisi berarti jasad tidak dipindahkan',
     Imp(Atom('LebamSesuai'), Not(Atom('Dipindahkan')))),
    ('R14', 'Bekas seretan berarti jasad dipindahkan',
     Imp(Atom('AdaSeretan'), Atom('Dipindahkan'))),
    ('R15', 'Seretan berasal dari TKP',
     ForAll(r, 'ruang', Imp(And(T(r), Atom('AdaSeretan')), Atom('AsalSeretan', r)))),
    ('R16', 'Kalau jasad dipindahkan, pelakunya orang yang kuat',
     ForAll(x, 'orang', Imp(And(P(x), Atom('Dipindahkan')), Atom('Kuat', x)))),
    ('R17', 'Kalau senjatanya racun, pelakunya memegang kunci lemari',
     ForAll(x, 'orang', Imp(And(P(x), S('Racun')), Atom('PegangKunci', x)))),
    ('R18', 'Jejak sepatu 43 di TKP berarti pelaku bersepatu 43',
     Imp(Atom('JejakSepatu43'), ForAll(x, 'orang', Imp(P(x), Atom('Ukuran43', x))))),
]

# MARK: - Pengetahuan latar (tetap, bukan bukti)

LATAR = [Atom('Berdarah', 'Pisau'), Atom('Berdarah', 'Vas'), Not(Atom('Berdarah', 'Racun')), Not(Atom('Berdarah', 'Tali')),
         Atom('LantaiKayu', 'Perpustakaan'), Atom('LantaiKayu', 'KamarTidur'),
         Not(Atom('LantaiKayu', 'Dapur')), Not(Atom('LantaiKayu', 'Taman')),
         Atom('LantaiBasah', 'Dapur'), Atom('LantaiBasah', 'Taman'),
         Not(Atom('LantaiBasah', 'Perpustakaan')), Not(Atom('LantaiBasah', 'KamarTidur'))]

# MARK: - Label query

QUERY_LABEL = {'s': 'Pelaku', 'w': 'Senjata', 'r': 'TKP'}
