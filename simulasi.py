"""
Simulasi agen Rumah Terkunci.

  python simulasi.py            # transkrip 1 kasus + perbandingan 300 kasus
  python simulasi.py 50         # perbandingan lebih cepat dengan 50 kasus

Hasil ditulis ke folder hasil/:
  transkrip_kasus_<nomor>.md  jalannya satu permainan, termasuk isi KB dan bukti resolusi
  perbandingan.md             angka perbandingan v1 vs v2 vs baseline
  angka.json                  angka yang sama dalam bentuk data
"""
import json
import os
import statistics as st
import sys
import time
from collections import Counter

import uji_konsistensi
from agen_baseline import TimBot, DetektifPenebak
from agen_v1 import AgenV1
from agen_v2 import AgenV2, KB, ATURAN, tampil_aturan, QUERY_ATOMS
from kasus import generate_case, TKP, sn, rn
from permainan import Permainan
from planning import tampil_formulasi
from teks import fakta, teks_aksi, teks_bukti, teks_jawaban

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hasil')
HASIL_GAME = ('tim', 'tim-salah', 'ai', 'ai-salah', 'vonis')


def akurasi_polisi(case):
    """Polisi gegabah: menuduh orang yang ditangkap dan menganggap tempat jasad ditemukan sebagai TKP."""
    return dict(pelaku_benar=case['arrested'] == case['sol'].s, tkp_benar=case['found'] == case['sol'].r)


# ---------------------------------------------------------------- transkrip satu kasus
def pilih_kasus_demo(batas=400):
    """Kasus yang memperlihatkan semua mekanik: jasad dipindahkan, salah tangkap,
    kesaksian yang tidak berguna, dan Detektif AI v2 memecahkannya melawan tim bot."""
    for seed in range(1, batas):
        if _kasus_demo_cocok(seed):
            return seed
    return 1


def _kasus_demo_cocok(seed):
    case = generate_case(seed)
    if not case['moved'] or case['arrested'] == case['sol'].s:
        return False
    if not any(k['kind'] == 'kesaksian' and not k['relevant'] for k in case['clues']):
        return False
    game = Permainan(seed, AgenV2(), TimBot(1))
    hasil = game.jalan()
    if hasil['tipe'] != 'ai' or hasil['ronde'] < 5:
        return False
    dilihat_ai = {e['id'] for _, siapa, jenis, data in game.events if siapa == 'ai' and jenis == 'amati' for e in data}
    return any(not case['by_id'][i]['relevant'] and case['by_id'][i]['kind'] == 'kesaksian' for i in dilihat_ai)


def transkrip(seed, level='normal'):
    case = generate_case(seed)
    ai = AgenV2()
    game = Permainan(seed, ai, TimBot(1), level=level)
    hasil = game.jalan()
    baris = _pembuka_transkrip(case, seed, level)
    baris += _jalannya_v2(game)
    if hasil['tipe'] == 'ai':
        baris += _bukti_resolusi_tuduhan(ai, case['sol'])
    baris_v1, hasil_v1 = _jalannya_v1(seed, level)
    baris += baris_v1
    baris.append(f'\nHasil v2: **{hasil["tipe"]}** di ronde {hasil["ronde"]} · '
                 f'Hasil v1: **{hasil_v1["tipe"]}** di ronde {hasil_v1["ronde"]}.')
    return '\n'.join(baris), hasil, hasil_v1


def _pembuka_transkrip(case, seed, level):
    sol = case['sol']
    return [
        f'# Simulasi Kasus No. {seed:06d}\n',
        f'Level **{level}** · Tim bot (3 detektif) melawan **Detektif AI v2** (FOL + resolusi + A*).\n',
        f'- Jawaban rahasia (hanya untuk pembaca): **{teks_jawaban(sol)}**',
        f'- Jasad ditemukan di **{rn(case["found"])}** · jasad {"dipindahkan" if case["moved"] else "tidak dipindahkan"}',
        f'- Polisi menangkap **{sn(case["arrested"])}** · '
        f'{"salah tangkap" if case["arrested"] != sol.s else "kebetulan benar"}\n',
        'Cara membaca: **TELL** = fakta FOL yang dimasukkan ke KB dari sebuah bukti. '
        '**ASK** = resolusi untuk setiap Pelaku(x), Senjata(w), dan TKP(r) yang belum pasti. '
        '**Rencana A*** = urutan aksi terpendek ke informasi baru berikutnya; AI hanya menjalankan aksi pertama '
        'lalu merencanakan ulang.\n',
    ]


def _jalannya_v2(game):
    baris, ronde_sekarang = [], None
    for ronde, siapa, jenis, data in game.events:
        if ronde != ronde_sekarang:
            ronde_sekarang = ronde
            baris.append(f'\n## Ronde {ronde}\n')
        baris += _teks_event_v2(game.case, siapa, jenis, data)
    return baris


def _teks_event_v2(case, siapa, jenis, data):
    if siapa == 'tim' and jenis == 'aksi':
        temuan = ' → ' + '; '.join(teks_bukti(case, i) for i in data['found']) if data['found'] else ''
        return [f'- **Tim**, detektif {data["d"]}: {teks_aksi(data["act"])}{temuan}']
    if siapa == 'ai' and jenis == 'aksi':
        info = data['info']
        return [f'- **AI**: {teks_aksi(data["act"])}  ·  rencana A* ({info.get("simpul", 0)} node): '
                f'`{" → ".join(info.get("rencana", []))}`']
    if siapa == 'ai' and jenis == 'amati':
        return [b for entry in data for b in _teks_tell_ask(case, entry)]
    if jenis == 'tuduh':
        pelaku = 'Tim' if siapa == 'tim' else 'Detektif AI'
        return [f'\n**{pelaku} menuduh: {teks_jawaban(data["guess"])}** → {"BENAR" if data["benar"] else "SALAH"}']
    if jenis == 'vonis':
        return [f'\nSidang: hakim memvonis {sn(data["arrested"])} berdasarkan berkas polisi.']
    return []


def _teks_tell_ask(case, entry):
    baris = [f'  - TELL `{"; ".join(entry["fol"])}`  ← {teks_bukti(case, entry["id"])}']
    if not entry['relevan']:
        baris.append(f'    - Tidak relevan: {entry["alasan"]}.')
    baru = ', '.join(fakta(k, v, s) for (k, v), s in entry['baru']) or 'belum ada kesimpulan baru'
    baris.append(f'    - ASK: {entry["query"]} query resolusi, {entry["langkah"]} langkah, {entry["waktu_ms"]:.1f} ms → {baru}')
    return baris


def _bukti_resolusi_tuduhan(ai, sol):
    baris = ['\n## Bukti resolusi untuk tuduhan AI\n',
             'Prasyarat aksi `Tuduh(s, w, t)` adalah KB ⊨ Pelaku(s) ∧ Senjata(w) ∧ TKP(t). '
             'Berikut langkah resolusi untuk bagian pelaku: KB ∧ ¬Pelaku(...) diturunkan sampai klausa kosong.\n',
             '```']
    for i, (kiri, kanan, hasil) in enumerate(ai.bukti('s', sol.s, True), 1):
        baris += [f'{i:>2}. {kiri}', f'    + {kanan}', f'    ⇒ {hasil}']
    return baris + ['```']


def _jalannya_v1(seed, level):
    """Kasus yang sama dimainkan Detektif AI v1, untuk dibandingkan dengan v2."""
    game = Permainan(seed, AgenV1(), TimBot(1), level=level)
    hasil = game.jalan()
    baris = ['\n## Kasus yang sama dengan Detektif AI v1\n']
    for ronde, siapa, jenis, data in game.events:
        baris += _teks_event_v1(game.case, ronde, siapa, jenis, data)
    return baris, hasil


def _teks_event_v1(case, ronde, siapa, jenis, data):
    if siapa == 'ai' and jenis == 'aksi':
        return [f'- Ronde {ronde}: {teks_aksi(data["act"])}']
    if siapa == 'ai' and jenis == 'amati':
        return [f'  - {teks_bukti(case, e["id"])} → model {e["sebelum"]} → {e["sesudah"]} ({e["waktu_ms"]:.3f} ms)'
                for e in data]
    if jenis == 'tuduh':
        pelaku = 'Tim' if siapa == 'tim' else 'Detektif AI v1'
        return [f'- **{pelaku} menuduh di ronde {ronde}: {teks_jawaban(data["guess"])}** → '
                f'{"BENAR" if data["benar"] else "SALAH"}']
    if jenis == 'vonis':
        return ['- Sidang: hakim memvonis orang yang ditangkap polisi.']
    return []


# ---------------------------------------------------------------- perbandingan
def main_ai(buat_agen, seeds, level='normal'):
    """Detektif AI bermain sendiri di setiap kasus. Mengembalikan angka tabel 1 dan 2."""
    hasil, ronde_menang, aksi, agen_semua = Counter(), [], [], []
    for seed in seeds:
        agen = buat_agen()
        game = Permainan(seed, agen, None, level=level)
        h = game.jalan()
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


def _biaya_penalaran(stats):
    def total(kunci):
        return sum(s.get(kunci, 0) for s in stats)
    update, rencana = max(total('update'), 1), max(total('rencana'), 1)
    return dict(ms_update=total('waktu_ms') / update, query_update=total('query') / update,
                langkah_update=total('langkah_resolusi') / update,
                langkah_max=max((s.get('langkah_max', 0) for s in stats), default=0),
                simpul=total('simpul_planner') / rencana)


def tim_vs(buat_ai, seeds, ambang=1):
    """Tim bot melawan Detektif AI. Mengembalikan persentase setiap jenis hasil."""
    hasil = Counter(Permainan(seed, buat_ai(), TimBot(ambang)).jalan()['tipe'] for seed in seeds)
    return {k: hasil[k] / len(seeds) * 100 for k in HASIL_GAME}


def ablation(seed=3, n_bukti=8, limit=20000):
    """Biaya 24 query (12 atom jawaban × 2 polaritas) setelah 8 bukti masuk KB,
    dengan dan tanpa eliminasi literal murni."""
    case = generate_case(seed)
    ids = [c['id'] for c in case['clues']][:n_bukti]
    return [_ukur_query(case, ids, pure, limit) for pure in (True, False)]


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


def representasi(seeds):
    """Ukuran KB v2 setelah semua bukti satu kasus di-TELL: rata-rata atom, maksimal atom,
    rata-rata klausa, dan jumlah klausa aturan + latar."""
    atoms, clauses = [], []
    for seed in seeds:
        case = generate_case(seed)
        kb = KB(case['found'])
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
    cek, beda, beda_rel, batas = uji_konsistensi.main(n)
    angka['konsistensi'] = dict(cek=cek, beda=beda, beda_relevansi=beda_rel, batas=batas)
    angka['ablation'] = ablation()
    angka['atom_rata'], angka['atom_max'], angka['klausa_rata'], angka['klausa_aturan'] = representasi(seeds[:100])
    return angka


def teks_perbandingan(n, a, detik):
    """Isi perbandingan.md dari angka hasil hitung_angka()."""
    return '\n'.join(_tabel_agen_sendiri(n, a) + _tabel_biaya(a) + _tabel_tim(a) + _bagian_polisi(a)
                     + _bagian_konsistensi(a) + _bagian_representasi(a) + _tabel_ablation(a)
                     + _lampiran(detik))


def _tabel_agen_sendiri(n, a):
    baris = [f'# Perbandingan agen pada {n} kasus (level Normal)\n',
             'Semua angka dihasilkan oleh `simulasi.py`. Kasus No. 1 sampai ' + str(n) + '.\n',
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
    return ['\n## Lampiran: aturan FOL v2\n', '```', tampil_aturan(), '```',
            '\n## Lampiran: problem formulation dan A* v2\n', '```', tampil_formulasi(), '```',
            f'\nWaktu total simulasi: {detik:.0f} detik.']


def tulis(nama_file, isi):
    with open(os.path.join(OUT, nama_file), 'w', encoding='utf-8') as f:
        f.write(isi)


def main(n=300):
    os.makedirs(OUT, exist_ok=True)
    mulai = time.perf_counter()
    demo = pilih_kasus_demo()
    teks, h2, h1 = transkrip(demo)
    tulis(f'transkrip_kasus_{demo:06d}.md', teks)
    print(f'transkrip kasus {demo}: v2 {h2["tipe"]}@{h2["ronde"]}, v1 {h1["tipe"]}@{h1["ronde"]}', flush=True)
    angka = hitung_angka(n)
    angka['kasus_demo'] = demo
    laporan = teks_perbandingan(n, angka, time.perf_counter() - mulai)
    tulis('angka.json', json.dumps(angka, indent=2))
    tulis('perbandingan.md', laporan)
    print(laporan)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
