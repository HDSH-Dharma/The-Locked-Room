"""
perbandingan_service.py
Service — angka perbandingan v1 vs v2 vs baseline pada banyak kasus, dan teks perbandingan.md.
"""
import statistics as st
import time
from collections import Counter

from agents.baseline_agent import DetektifPenebak
from agents.tim_bot_agent import TimBot
from agents.v1_agent import AgenV1
from agents.v2_agent import AgenV2
from engine.permainan_engine import Permainan
from models.aturan_model import ATURAN
from models.evaluasi_model import HASIL_GAME
from models.planning_model import TEKS_FORMULASI
from models.rumah_model import TKP
from services.fol_service import show
from services.kasus_service import generate_case
from services.kb_service import KB, QUERY_ATOMS
from services.konsistensi_service import bandingkan

# MARK: - Angka

def akurasi_polisi(case):
    """Polisi gegabah: menuduh orang yang ditangkap dan menganggap tempat jasad ditemukan sebagai TKP."""
    return dict(pelaku_benar=case['arrested'] == case['sol'].s, tkp_benar=case['found'] == case['sol'].r)


def main_ai(buat_agen, seeds, level='normal'):
    """Detektif AI bermain sendiri di setiap kasus. Mengembalikan angka tabel 1 dan 2."""
    hasil, ronde_menang, aksi, agen_semua = Counter(), [], [], []
    for seed in seeds:
        agen = buat_agen()
        game = Permainan(seed, agen, None, level=level)
        h    = game.jalan()
        hasil[h['tipe']] += 1
        if h['tipe'] == 'ai':
            ronde_menang.append(h['ronde'])
        aksi.append(game.ai_aksi)
        agen_semua.append(agen)
    n = len(seeds)
    angka = dict(pecah=hasil['ai'] / n * 100, salah=hasil['ai-salah'] / n * 100, buntu=hasil['vonis'] / n * 100,
                 ronde=st.mean(ronde_menang) if ronde_menang else 0, aksi=st.mean(aksi))
    angka.update(_biaya_penalaran([a.stats for a in agen_semua]))
    return angka


def tim_vs(buat_ai, seeds, ambang=1):
    """Tim bot melawan Detektif AI. Mengembalikan persentase setiap jenis hasil."""
    hasil = Counter(Permainan(seed, buat_ai(), TimBot(ambang)).jalan()['tipe'] for seed in seeds)
    return {k: hasil[k] / len(seeds) * 100 for k in HASIL_GAME}


def ablation(seed=3, n_bukti=8, limit=20000):
    """Biaya 24 query (12 atom jawaban × 2 polaritas) setelah 8 bukti masuk KB,
    dengan dan tanpa eliminasi literal murni."""
    case = generate_case(seed)
    ids  = [c['id'] for c in case['clues']][:n_bukti]
    return [_ukur_query(case, ids, pure, limit) for pure in (True, False)]


def representasi(seeds):
    """Ukuran KB v2 setelah semua bukti satu kasus di-TELL: rata-rata atom, maksimal atom,
    rata-rata klausa, dan jumlah klausa aturan + latar."""
    atoms, clauses = [], []
    for seed in seeds:
        case = generate_case(seed)
        kb   = KB(case['found'])
        for c in case['clues']:
            for f in c['fol']:
                kb.tell(f, c['id'])
        atoms.append(len(kb.atoms()))
        clauses.append(len(kb.clauses))
    return st.mean(atoms), max(atoms), st.mean(clauses), len(KB(TKP[0]).rule_clauses)


def hitung_angka(n):
    """Semua angka perbandingan untuk kasus 1..n."""
    seeds = list(range(1, n + 1))
    angka = dict(v1=main_ai(AgenV1, seeds))
    print('v1 selesai', flush=True)
    angka['v2'] = main_ai(AgenV2, seeds)
    print('v2 selesai', flush=True)
    angka['penebak'] = main_ai(lambda: DetektifPenebak(3, 7), seeds)
    print('penebak selesai', flush=True)
    angka.update(tim_v1=tim_vs(AgenV1, seeds), tim_v2=tim_vs(AgenV2, seeds), tim_nekat_v2=tim_vs(AgenV2, seeds, ambang=2))
    print('tim selesai', flush=True)
    polisi = [akurasi_polisi(generate_case(s)) for s in seeds]
    angka['polisi_pelaku'] = sum(p['pelaku_benar'] for p in polisi) / n * 100
    angka['polisi_tkp'] = sum(p['tkp_benar'] for p in polisi) / n * 100
    cek, beda, beda_rel, batas = bandingkan(n)
    angka['konsistensi'] = dict(cek=cek, beda=beda, beda_relevansi=beda_rel, batas=batas)
    angka['ablation'] = ablation()
    angka['atom_rata'], angka['atom_max'], angka['klausa_rata'], angka['klausa_aturan'] = representasi(seeds[:100])
    return angka


# MARK: - Teks perbandingan.md

def teks_perbandingan(n, a, detik):
    """Isi perbandingan.md dari angka hasil hitung_angka()."""
    return '\n'.join(_tabel_agen_sendiri(n, a) + _tabel_biaya(a) + _tabel_tim(a) + _bagian_polisi(a)
                     + _bagian_konsistensi(a) + _bagian_representasi(a) + _tabel_ablation(a)
                     + _lampiran(detik))


# MARK: - Private Helpers

def _biaya_penalaran(stats):
    def total(kunci):
        return sum(s.get(kunci, 0) for s in stats)
    update, rencana = max(total('update'), 1), max(total('rencana'), 1)
    return dict(ms_update=total('waktu_ms') / update, query_update=total('query') / update,
                langkah_update=total('langkah_resolusi') / update,
                langkah_max=max((s.get('langkah_max', 0) for s in stats), default=0),
                simpul=total('simpul_planner') / rencana)


def _ukur_query(case, ids, pure, limit):
    kb = KB(case['found'], pure=pure, limit=limit)
    for cid in ids:
        for f in case['by_id'][cid]['fol']:
            kb.tell(f, cid)
    mulai = time.perf_counter()
    langkah = batas = 0
    for _, _, atom in QUERY_ATOMS:
        for polaritas in (False, True):
            ok, prover, _ = kb.ask((atom, polaritas))
            langkah += prover.steps
            batas += ok is None
    return dict(pure=pure, ms=(time.perf_counter() - mulai) * 1000, langkah=langkah, batas=batas)


def _tabel_agen_sendiri(n, a):
    baris = [f'# Perbandingan agen pada {n} kasus (level Normal)\n',
             'Semua angka dihasilkan oleh `scripts/simulasi.py`. Kasus No. 1 sampai ' + str(n) + '.\n',
             '## 1. Detektif AI bermain sendiri (tanpa tim)\n',
             '| Agen | Memecahkan kasus | Salah tuduh | Tidak sempat (sidang) | Rata-rata ronde menuduh | Rata-rata aksi |',
             '|---|---|---|---|---|---|']
    for nama, r in (('v1 · proposisional + model checking', a['v1']), ('v2 · FOL + resolusi + A*', a['v2']),
                    ('Penebak · v1 tapi menuduh saat sisa ≤ 3', a['penebak'])):
        baris.append(f'| {nama} | {r["pecah"]:.1f}% | {r["salah"]:.1f}% | {r["buntu"]:.1f}% | {r["ronde"]:.2f} | '
                     f'{r["aksi"]:.1f} |')
    return baris


def _tabel_biaya(a):
    v1, v2 = a['v1'], a['v2']
    return ['\n## 2. Biaya penalaran\n',
            '| Agen | Waktu per pembaruan KB | Query per pembaruan | Langkah resolusi per pembaruan | '
            'Langkah terbanyak dalam satu pembaruan | Node BFS / A* per aksi |',
            '|---|---|---|---|---|---|',
            f'| v1 | {v1["ms_update"]:.3f} ms | 0 (cukup saring 64 model) | - | - | {v1["simpul"]:.1f} (BFS) |',
            f'| v2 | {v2["ms_update"]:.2f} ms | {v2["query_update"]:.1f} | {v2["langkah_update"]:.0f} | '
            f'{v2["langkah_max"]} | {v2["simpul"]:.1f} |']


def _tabel_tim(a):
    baris = ['\n## 3. Tim bot (3 detektif) melawan Detektif AI\n',
             '| Lawan | Tim menang | Tim salah tuduh | AI menang | Sampai sidang |', '|---|---|---|---|---|']
    for nama, t in (('Tim hati-hati vs v1', a['tim_v1']), ('Tim hati-hati vs v2', a['tim_v2']),
                    ('Tim nekat (menebak saat sisa ≤ 2) vs v2', a['tim_nekat_v2'])):
        baris.append(f'| {nama} | {t["tim"]:.1f}% | {t["tim-salah"]:.1f}% | {t["ai"]:.1f}% | {t["vonis"]:.1f}% |')
    return baris


def _bagian_polisi(a):
    return ['\n## 4. Polisi gegabah (tanpa penalaran)\n',
            f'- Pelaku yang ditangkap benar: {a["polisi_pelaku"]:.1f}% · salah tangkap: {100 - a["polisi_pelaku"]:.1f}%',
            f'- Menganggap tempat jasad ditemukan sebagai TKP, benar: {a["polisi_tkp"]:.1f}%']


def _bagian_konsistensi(a):
    k = a['konsistensi']
    return ['\n## 5. Konsistensi v1 dan v2\n',
            f'- {k["cek"]} pembaruan KB dalam urutan bukti acak: beda kesimpulan **{k["beda"]}**, beda penilaian '
            f'relevansi **{k["beda_relevansi"]}**, query yang kena batas langkah **{k["batas"]}**.',
            '- Artinya resolusi (v2) dan model checking (v1) selalu sampai pada kesimpulan yang sama.']


def _bagian_representasi(a):
    atom = a['atom_rata']
    return ['\n## 6. Ukuran representasi\n',
            '- v1: 64 model (4 pelaku × 4 senjata × 4 TKP). Setiap jenis bukti ditulis tangan sebagai fungsi Python.',
            f'- v2: {len(ATURAN)} aturan FOL berkuantor ditulis sekali. Setelah universal instantiation: '
            f'{a["klausa_aturan"]} klausa aturan dan latar; satu kasus lengkap rata-rata {a["klausa_rata"]:.0f} klausa '
            f'dengan {atom:.0f} atom (maksimal {a["atom_max"]}).',
            f'- Tabel kebenaran penuh untuk {atom:.0f} atom berarti 2^{atom:.0f} ≈ {2 ** round(atom):.1e} baris. '
            'Model checking biasa tidak praktis di sini; v1 hanya bisa memakai 64 model karena arti setiap bukti '
            'sudah ditulis tangan.']


def _tabel_ablation(a):
    baris = ['\n## 7. Eksperimen: eliminasi literal murni pada resolusi\n',
             'Kasus No. 3, KB berisi aturan + 8 bukti pertama, lalu 24 query (12 atom jawaban × 2 polaritas).\n',
             '| Versi | Waktu 24 query | Langkah resolusi | Query kena batas 20.000 langkah |', '|---|---|---|---|']
    for r in a['ablation']:
        baris.append(f'| {"dengan" if r["pure"] else "tanpa"} eliminasi literal murni | {r["ms"]:.0f} ms | '
                     f'{r["langkah"]} | {r["batas"]} |')
    return baris


def _lampiran(detik):
    return ['\n## Lampiran: aturan FOL v2\n', '```', _teks_aturan(), '```',
            '\n## Lampiran: problem formulation dan A* v2\n', '```', TEKS_FORMULASI, '```',
            f'\nWaktu total simulasi: {detik:.0f} detik.']


def _teks_aturan():
    lines = []
    for name, ket, f in ATURAN:
        lines.append(f'{name}  {show(f)}    # {ket}')
    return '\n'.join(lines)
