"""
Analisis tambahan playtest untuk bagian hasil dan keterbatasan laporan. Dipanggil dari evaluasi.py.

- Game live      : setiap log hanya dihitung melawan AI yang benar-benar dilawan saat main.
- Terbukti/tebak : sisa jawaban yang mungkin dari bukti yang dipegang tim saat menuduh.
                   Sisa 1 = tuduhan terbukti, sisa 2 atau lebih = tebakan (v2 tidak pernah menebak).
- Efek belajar   : game 1-50 vs 51-100 per pemain (nomor game dari pembagian.json), plus durasi.

Game dan log tidak diubah: semua angka dihitung ulang dari replay.
"""
import json
import os
from collections import defaultdict

from agen_baseline import AIDiam
from kasus import ALL_WORLDS, World
from permainan import Permainan
from replay import TimRekaman

PATH_PEMBAGIAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pembagian.json')
BATAS_PARUH = 50
MENANG_PEMAIN = ('tim', 'ai-salah')
MENANG_AI = ('ai', 'tim-salah')


class TimRekamanPencatat(TimRekaman):
    """TimRekaman yang juga mencatat id bukti yang didapat tim dari geledah dan interogasi."""

    def __init__(self, log):
        super().__init__(log)
        self.bukti = []

    def _putar_aksi(self, game, d, aksi):
        ids = super()._putar_aksi(game, d, aksi)
        self.bukti.extend(ids or [])
        return ids


# ---------------------------------------------------------------- terbukti vs tebakan
def sisa_jawaban(log):
    """Jumlah jawaban (pelaku, senjata, TKP) yang masih mungkin dari bukti tim saat menuduh.
    Diputar melawan AI diam supaya tidak ada tuduhan AI yang menghentikan game lebih awal."""
    tim = TimRekamanPencatat(log)
    game = Permainan(log['seed'], AIDiam(), tim, teleport=True, menguping=True)
    game.jalan()
    berkas = [c['id'] for c in game.case['clues'] if c['kind'] == 'berkas']
    models = list(ALL_WORLDS)
    for cid in dict.fromkeys(berkas + tim.bukti):
        prop = game.case['by_id'][cid]['prop']
        models = [m for m in models if prop(m)]
    return len(models), game.case['sol']


def tuduhan_tim(logs):
    """Satu baris per log yang tim-nya menuduh: (pemain, seed, sisa jawaban, tuduhan benar?)."""
    baris = []
    for log in logs:
        t = log.get('tuduhan_tim')
        if not t:
            continue
        sisa, sol = sisa_jawaban(log)
        baris.append(dict(pemain=log['pemain'], seed=log['seed'], sisa=sisa, benar=World(*t['jawaban']) == sol))
    return baris


# ---------------------------------------------------------------- game live
def baris_live(baris_replay):
    """Baris evaluasi yang AI-nya sama dengan AI yang dilawan saat main."""
    return [b for b in baris_replay if b['ai'] == b['ai_live']]


def tanpa_tebakan(live, tuduhan):
    """Hasil live kalau tuduhan tim yang berupa tebakan dihitung seri (aturan yang dipakai v2)."""
    tebakan = {(t['pemain'], t['seed']) for t in tuduhan if t['sisa'] > 1}
    hasil = []
    for b in live:
        tipe = b['tipe']
        if tipe in ('tim', 'tim-salah') and (b['pemain'], b['seed']) in tebakan:
            tipe = 'vonis'
        hasil.append(dict(b, tipe=tipe))
    return hasil


# ---------------------------------------------------------------- efek belajar
def nomor_game():
    """(pemain, seed) -> nomor game di pembagian.json."""
    if not os.path.exists(PATH_PEMBAGIAN):
        return {}
    with open(PATH_PEMBAGIAN, encoding='utf-8') as f:
        pembagian = json.load(f)
    return {(p, e['seed']): e['no'] for p, daftar in pembagian.items() for e in daftar}


def efek_belajar(live, logs):
    """Per pemain dan paruh (game 1-50, 51-100): jumlah game, menang, dan rata-rata durasi."""
    nomor = nomor_game()
    durasi = {(log['pemain'], log['seed']): log.get('durasi_detik', 0) for log in logs}
    kelompok = defaultdict(list)
    for b in live:
        kunci = (b['pemain'], b['seed'])
        paruh = 1 if nomor.get(kunci, 0) <= BATAS_PARUH else 2
        kelompok[(b['pemain'], paruh)].append((b['tipe'] in MENANG_PEMAIN, durasi.get(kunci, 0)))
    return {k: dict(n=len(v), menang=sum(m for m, _ in v), durasi=sum(d for _, d in v) / len(v))
            for k, v in sorted(kelompok.items())}


# ---------------------------------------------------------------- keluaran
def teks_analisis(baris_replay, logs, ringkas_ai, persen):
    """Bagian markdown tambahan untuk hasil/evaluasi.md."""
    live = baris_live(baris_replay)
    tuduhan = tuduhan_tim(logs)
    bagian = _tabel_live(live, ringkas_ai)
    bagian += _tabel_tuduhan(tuduhan, persen)
    bagian += _tabel_tanpa_tebakan(tanpa_tebakan(live, tuduhan), persen)
    bagian += _tabel_belajar(efek_belajar(live, logs), persen)
    return '\n'.join(bagian)


def _tabel_live(live, ringkas_ai):
    per_ai = defaultdict(list)
    for b in live:
        per_ai[b['ai']].append(b)
    baris = ['\n## Game live (hanya AI yang dilawan saat main)\n',
             '| AI | Game | Pemain menang | AI menang | Seri |', '|---|---|---|---|---|']
    for nama, rows in per_ai.items():
        r = ringkas_ai(rows)
        baris.append(f'| {nama} | {r["n"]} | {r["pemain_menang"]} | {r["ai_menang"]} | {r["seri"]} |')
    return baris


def _tabel_tuduhan(tuduhan, persen):
    baris = ['\n## Tuduhan tim: terbukti vs menebak\n',
             'Sisa jawaban dihitung dari berkas polisi dan semua bukti yang didapat tim sampai menuduh.\n',
             '| Tuduhan tim | Jumlah | Benar | Salah |', '|---|---|---|---|']
    for judul, pilih in (('Terbukti (sisa 1)', lambda t: t['sisa'] == 1), ('Menebak (sisa 2+)', lambda t: t['sisa'] > 1)):
        rows = [t for t in tuduhan if pilih(t)]
        benar = sum(t['benar'] for t in rows)
        baris.append(f'| {judul} | {len(rows)} | {persen(benar, len(rows))} | {len(rows) - benar} |')
    return baris


def _tabel_tanpa_tebakan(hasil, persen):
    per_ai = defaultdict(list)
    for b in hasil:
        per_ai[b['ai']].append(b['tipe'])
    baris = ['\n## Game live kalau tebakan tim dihitung seri\n',
             '| AI | Game | Pemain menang | AI menang | Seri |', '|---|---|---|---|---|']
    for nama, tipe in per_ai.items():
        n = len(tipe)
        menang = sum(t in MENANG_PEMAIN for t in tipe)
        kalah = sum(t in MENANG_AI for t in tipe)
        baris.append(f'| {nama} | {n} | {persen(menang, n)} | {persen(kalah, n)} | {persen(tipe.count("vonis"), n)} |')
    return baris


def _tabel_belajar(belajar, persen):
    baris = ['\n## Efek belajar dan durasi (game live)\n',
             '| Pemain | Game | Jumlah | Pemain menang | Rata-rata durasi |', '|---|---|---|---|---|']
    for (pemain, paruh), r in belajar.items():
        rentang = f'1–{BATAS_PARUH}' if paruh == 1 else f'{BATAS_PARUH + 1}–100'
        menit, detik = divmod(int(r['durasi']), 60)
        baris.append(f'| {pemain} | {rentang} | {r["n"]} | {persen(r["menang"], r["n"])} | {menit} menit {detik} detik |')
    return baris
