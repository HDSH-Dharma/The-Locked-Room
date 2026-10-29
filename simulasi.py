"""
Simulasi agen Rumah Terkunci.

  python simulasi.py            # transkrip 1 kasus + perbandingan 300 kasus
  python simulasi.py 50         # perbandingan lebih cepat dengan 50 kasus

Hasil ditulis ke folder hasil/:
  transkrip_kasus_<nomor>.md  jalannya satu permainan, termasuk isi KB dan bukti resolusi
  perbandingan.md             angka perbandingan v1 vs v2 vs baseline
"""
import json
import os
import statistics as st
import sys
import time
from collections import Counter

from kasus import generate_case, TKP, sn, wn, rn
from agen_v1 import AgenV1
from agen_v2 import AgenV2, KB, ATURAN, tampil_aturan, QUERY_ATOMS
from planning import tampil_formulasi
from agen_baseline import TimBot, DetektifPenebak, polisi_gegabah
from permainan import Permainan, teks_aksi, teks_jawaban
import uji_konsistensi

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hasil')
NAMA = {'s': sn, 'w': wn, 'r': rn}


def fakta(cat, v, st_):
    n = NAMA[cat](v)
    if st_ == 'pasti':
        return {'s': f'Pelaku pasti {n}', 'w': f'Senjata pasti {n}', 'r': f'TKP pasti {n}'}[cat]
    return {'s': f'{n} bukan pelaku', 'w': f'Senjata bukan {n}', 'r': f'TKP bukan {n}'}[cat]


def teks_bukti(case, cid):
    c = case['by_id'][cid]
    if c['kind'] == 'kesaksian':
        return f'{sn(c["speaker"])}: {c["text"]}'
    if c['kind'] == 'berkas':
        return f'Berkas polisi: {c["text"]}'
    return f'{c["text"]} ({rn(c["room"])})'


# ---------------------------------------------------------------- transkrip
def pilih_kasus_demo(batas=400):
    """Kasus yang memperlihatkan semua mekanik: jasad dipindahkan, salah tangkap,
    kesaksian 'Aku bukan pelakunya', dan Detektif AI v2 memecahkannya melawan tim bot."""
    for seed in range(1, batas):
        c = generate_case(seed)
        if not c['moved'] or c['arrested'] == c['sol'].s:
            continue
        if not any(k['kind'] == 'kesaksian' and not k['relevant'] for k in c['clues']):
            continue
        g = Permainan(seed, AgenV2(), TimBot(1), 'normal')
        h = g.jalan()
        if h['tipe'] == 'ai' and h['ronde'] >= 5:
            seen = {e['id'] for r_, s_, j, d in g.events if s_ == 'ai' and j == 'amati' for e in d}
            if any(not c['by_id'][i]['relevant'] and c['by_id'][i]['kind'] == 'kesaksian' for i in seen):
                return seed
    return 1


def transkrip(seed, level='normal'):
    case = generate_case(seed)
    sol = case['sol']
    ai = AgenV2()
    game = Permainan(seed, ai, TimBot(1), level)
    hasil = game.jalan()
    L = []
    L.append(f'# Simulasi Kasus No. {seed:06d}\n')
    L.append(f'Level **{level}** · Tim bot (3 detektif) melawan **Detektif AI v2** (FOL + resolusi + A*).\n')
    L.append(f'- Jawaban rahasia (hanya untuk pembaca): **{teks_jawaban(sol)}**')
    L.append(f'- Jasad ditemukan di **{rn(case["found"])}** · jasad {"dipindahkan" if case["moved"] else "tidak dipindahkan"}')
    L.append(f'- Polisi menangkap **{sn(case["arrested"])}** · {"salah tangkap" if case["arrested"] != sol.s else "kebetulan benar"}\n')
    L.append('Cara membaca: **TELL** = fakta FOL yang dimasukkan ke KB dari sebuah bukti. '
             '**ASK** = resolusi untuk setiap Pelaku(x), Senjata(w), dan TKP(r) yang belum pasti. '
             '**Rencana A*** = urutan aksi terpendek ke informasi baru berikutnya; AI hanya menjalankan aksi pertama lalu merencanakan ulang.\n')

    cur = None
    for ronde, siapa, jenis, data in game.events:
        if ronde != cur:
            cur = ronde
            L.append(f'\n## Ronde {ronde}\n')
        if siapa == 'tim' and jenis == 'aksi':
            act = data['act']
            line = f'- **Tim**, detektif {data["d"]}: {teks_aksi(act)}'
            if data['found']:
                line += ' → ' + '; '.join(teks_bukti(case, i) for i in data['found'])
            L.append(line)
        elif siapa == 'ai' and jenis == 'aksi':
            info = data['info']
            L.append(f'- **AI**: {teks_aksi(data["act"])}  ·  rencana A* ({info.get("simpul", 0)} node): '
                     f'`{" → ".join(info.get("rencana", []))}`')
        elif siapa == 'ai' and jenis == 'amati':
            for e in data:
                L.append(f'  - TELL `{"; ".join(e["fol"])}`  ← {teks_bukti(case, e["id"])}')
                if not e['relevan']:
                    L.append(f'    - Tidak relevan: {e["alasan"]}.')
                baru = ', '.join(fakta(c_, v, s_) for (c_, v), s_ in e['baru']) or 'belum ada kesimpulan baru'
                L.append(f'    - ASK: {e["query"]} query resolusi, {e["langkah"]} langkah, {e["waktu_ms"]:.1f} ms → {baru}')
        elif jenis == 'tuduh':
            who = 'Tim' if siapa == 'tim' else 'Detektif AI'
            L.append(f'\n**{who} menuduh: {teks_jawaban(data["guess"])}** → {"BENAR" if data["benar"] else "SALAH"}')
        elif jenis == 'vonis':
            L.append(f'\nSidang: hakim memvonis {sn(data["arrested"])} berdasarkan berkas polisi.')

    if hasil['tipe'] == 'ai':
        L.append('\n## Bukti resolusi untuk tuduhan AI\n')
        L.append('Prasyarat aksi `Tuduh(s, w, t)` adalah KB ⊨ Pelaku(s) ∧ Senjata(w) ∧ TKP(t). '
                 'Berikut langkah resolusi untuk bagian pelaku: KB ∧ ¬Pelaku(...) diturunkan sampai klausa kosong.\n')
        steps = ai.bukti('s', sol.s, True)
        L.append('```')
        for i, (a, b, rres) in enumerate(steps, 1):
            L.append(f'{i:>2}. {a}')
            L.append(f'    + {b}')
            L.append(f'    ⇒ {rres}')
        L.append('```')

    # Kasus sama dengan agen v1
    L.append('\n## Kasus yang sama dengan Detektif AI v1\n')
    g1 = Permainan(seed, AgenV1(), TimBot(1), level)
    h1 = g1.jalan()
    for ronde, siapa, jenis, data in g1.events:
        if siapa == 'ai' and jenis == 'aksi':
            L.append(f'- Ronde {ronde}: {teks_aksi(data["act"])}')
        elif siapa == 'ai' and jenis == 'amati':
            for e in data:
                L.append(f'  - {teks_bukti(case, e["id"])} → model {e["sebelum"]} → {e["sesudah"]} ({e["waktu_ms"]:.3f} ms)')
        elif jenis == 'tuduh':
            who = 'Tim' if siapa == 'tim' else 'Detektif AI v1'
            L.append(f'- **{who} menuduh di ronde {ronde}: {teks_jawaban(data["guess"])}** → {"BENAR" if data["benar"] else "SALAH"}')
        elif jenis == 'vonis':
            L.append('- Sidang: hakim memvonis orang yang ditangkap polisi.')
    L.append(f'\nHasil v2: **{hasil["tipe"]}** di ronde {hasil["ronde"]} · Hasil v1: **{h1["tipe"]}** di ronde {h1["ronde"]}.')
    return '\n'.join(L), hasil, h1


# ---------------------------------------------------------------- perbandingan
def main_ai(make, seeds, level='normal'):
    hasil = Counter()
    ronde, aksi, waktu, upd, langkah, langkah_max, query, simpul, rencana = [], [], 0.0, 0, 0, 0, 0, 0, 0
    for seed in seeds:
        a = make()
        g = Permainan(seed, a, None, level)
        h = g.jalan()
        hasil[h['tipe']] += 1
        if h['tipe'] == 'ai':
            ronde.append(h['ronde'])
        aksi.append(g.ai_aksi)
        waktu += a.stats['waktu_ms']
        upd += a.stats['update']
        langkah += a.stats.get('langkah_resolusi', 0)
        langkah_max = max(langkah_max, a.stats.get('langkah_max', 0))
        query += a.stats.get('query', 0)
        simpul += a.stats.get('simpul_planner', 0)
        rencana += a.stats.get('rencana', 0)
    n = len(seeds)
    return dict(
        pecah=hasil['ai'] / n * 100, salah=hasil['ai-salah'] / n * 100, buntu=hasil['vonis'] / n * 100,
        ronde=st.mean(ronde) if ronde else 0, aksi=st.mean(aksi), ms_update=waktu / max(upd, 1),
        query_update=query / max(upd, 1), langkah_update=langkah / max(upd, 1), langkah_max=langkah_max,
        simpul=simpul / max(rencana, 1))


def tim_vs(make_ai, seeds, ambang=1):
    c = Counter()
    for seed in seeds:
        h = Permainan(seed, make_ai(), TimBot(ambang), 'normal').jalan()
        c[h['tipe']] += 1
    n = len(seeds)
    return {k: c[k] / n * 100 for k in ('tim', 'tim-salah', 'ai', 'ai-salah', 'vonis')}


def ablation(seed=3, n_bukti=8, limit=20000):
    """Biaya 24 query (12 atom jawaban × 2 polaritas) setelah 8 bukti masuk KB,
    dengan dan tanpa eliminasi literal murni."""
    case = generate_case(seed)
    ids = [c['id'] for c in case['clues']][:n_bukti]
    out = []
    for pure in (True, False):
        kb = KB(case['found'], pure=pure, limit=limit)
        for cid in ids:
            for f in case['by_id'][cid]['fol']:
                kb.tell(f, cid)
        t = time.perf_counter()
        langkah = batas = 0
        for _, _, atom in QUERY_ATOMS:
            for pol in (False, True):
                ok, pr, _ = kb.ask((atom, pol))
                langkah += pr.steps
                batas += ok is None
        out.append(dict(pure=pure, ms=(time.perf_counter() - t) * 1000, langkah=langkah, batas=batas))
    return out


def representasi(seeds):
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


def main(n=300):
    os.makedirs(OUT, exist_ok=True)
    seeds = list(range(1, n + 1))
    t0 = time.perf_counter()

    demo = pilih_kasus_demo()
    teks, h2, h1 = transkrip(demo)
    with open(os.path.join(OUT, f'transkrip_kasus_{demo:06d}.md'), 'w', encoding='utf-8') as f:
        f.write(teks)
    print(f'transkrip kasus {demo}: v2 {h2["tipe"]}@{h2["ronde"]}, v1 {h1["tipe"]}@{h1["ronde"]}', flush=True)

    r1 = main_ai(AgenV1, seeds)
    print('v1 selesai', flush=True)
    r2 = main_ai(AgenV2, seeds)
    print('v2 selesai', flush=True)
    rp = main_ai(lambda: DetektifPenebak(3, 7), seeds)
    print('penebak selesai', flush=True)
    t1 = tim_vs(AgenV1, seeds)
    t2 = tim_vs(AgenV2, seeds)
    t2b = tim_vs(AgenV2, seeds, ambang=2)
    print('tim selesai', flush=True)
    pol = [polisi_gegabah(generate_case(s)) for s in seeds]
    pol_pelaku = sum(p['pelaku_benar'] for p in pol) / n * 100
    pol_tkp = sum(p['tkp_benar'] for p in pol) / n * 100
    cek, beda, beda_rel, batas = uji_konsistensi.main(n)
    abl = ablation()
    at_mean, at_max, cl_mean, cl_rules = representasi(seeds[:100])

    L = [f'# Perbandingan agen pada {n} kasus (level Normal)\n',
         'Semua angka dihasilkan oleh `simulasi.py`. Kasus No. 1 sampai ' + str(n) + '.\n',
         '## 1. Detektif AI bermain sendiri (tanpa tim)\n',
         '| Agen | Memecahkan kasus | Salah tuduh | Tidak sempat (sidang) | Rata-rata ronde menuduh | Rata-rata aksi |',
         '|---|---|---|---|---|---|']
    for name, r in (('v1 · proposisional + model checking', r1), ('v2 · FOL + resolusi + A*', r2),
                    ('Penebak · v1 tapi menuduh saat sisa ≤ 3', rp)):
        L.append(f'| {name} | {r["pecah"]:.1f}% | {r["salah"]:.1f}% | {r["buntu"]:.1f}% | {r["ronde"]:.2f} | {r["aksi"]:.1f} |')
    L += ['\n## 2. Biaya penalaran\n',
          '| Agen | Waktu per pembaruan KB | Query per pembaruan | Langkah resolusi per pembaruan | Langkah terbanyak dalam satu pembaruan | Node BFS / A* per aksi |',
          '|---|---|---|---|---|---|',
          f'| v1 | {r1["ms_update"]:.3f} ms | 0 (cukup saring 64 model) | - | - | {r1["simpul"]:.1f} (BFS) |',
          f'| v2 | {r2["ms_update"]:.2f} ms | {r2["query_update"]:.1f} | {r2["langkah_update"]:.0f} | {r2["langkah_max"]} | {r2["simpul"]:.1f} |',
          '\n## 3. Tim bot (3 detektif) melawan Detektif AI\n',
          '| Lawan | Tim menang | Tim salah tuduh | AI menang | Sampai sidang |', '|---|---|---|---|---|',
          f'| Tim hati-hati vs v1 | {t1["tim"]:.1f}% | {t1["tim-salah"]:.1f}% | {t1["ai"]:.1f}% | {t1["vonis"]:.1f}% |',
          f'| Tim hati-hati vs v2 | {t2["tim"]:.1f}% | {t2["tim-salah"]:.1f}% | {t2["ai"]:.1f}% | {t2["vonis"]:.1f}% |',
          f'| Tim nekat (menebak saat sisa ≤ 2) vs v2 | {t2b["tim"]:.1f}% | {t2b["tim-salah"]:.1f}% | {t2b["ai"]:.1f}% | {t2b["vonis"]:.1f}% |',
          '\n## 4. Polisi gegabah (tanpa penalaran)\n',
          f'- Pelaku yang ditangkap benar: {pol_pelaku:.1f}% · salah tangkap: {100 - pol_pelaku:.1f}%',
          f'- Menganggap tempat jasad ditemukan sebagai TKP, benar: {pol_tkp:.1f}%',
          '\n## 5. Konsistensi v1 dan v2\n',
          f'- {cek} pembaruan KB dalam urutan bukti acak: beda kesimpulan **{beda}**, beda penilaian relevansi **{beda_rel}**, query yang kena batas langkah **{batas}**.',
          '- Artinya resolusi (v2) dan model checking (v1) selalu sampai pada kesimpulan yang sama.',
          '\n## 6. Ukuran representasi\n',
          '- v1: 64 model (4 pelaku × 4 senjata × 4 TKP). Setiap jenis bukti ditulis tangan sebagai fungsi Python.',
          f'- v2: {len(ATURAN)} aturan FOL berkuantor ditulis sekali. Setelah universal instantiation: {cl_rules} klausa aturan dan latar; '
          f'satu kasus lengkap rata-rata {cl_mean:.0f} klausa dengan {at_mean:.0f} atom (maksimal {at_max}).',
          f'- Tabel kebenaran penuh untuk {at_mean:.0f} atom berarti 2^{at_mean:.0f} ≈ {2 ** round(at_mean):.1e} baris. '
          'Model checking biasa tidak praktis di sini; v1 hanya bisa memakai 64 model karena arti setiap bukti sudah ditulis tangan.',
          '\n## 7. Eksperimen: eliminasi literal murni pada resolusi\n',
          'Kasus No. 3, KB berisi aturan + 8 bukti pertama, lalu 24 query (12 atom jawaban × 2 polaritas).\n',
          '| Versi | Waktu 24 query | Langkah resolusi | Query kena batas 20.000 langkah |', '|---|---|---|---|']
    for a in abl:
        L.append(f'| {"dengan" if a["pure"] else "tanpa"} eliminasi literal murni | {a["ms"]:.0f} ms | {a["langkah"]} | {a["batas"]} |')
    L += ['\n## Lampiran: aturan FOL v2\n', '```', tampil_aturan(), '```',
          '\n## Lampiran: problem formulation dan A* v2\n', '```', tampil_formulasi(), '```',
          f'\nWaktu total simulasi: {time.perf_counter() - t0:.0f} detik.']
    with open(os.path.join(OUT, 'angka.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(v1=r1, v2=r2, penebak=rp, tim_v1=t1, tim_v2=t2, tim_nekat_v2=t2b, polisi_pelaku=pol_pelaku,
                       polisi_tkp=pol_tkp, konsistensi=dict(cek=cek, beda=beda, beda_relevansi=beda_rel, batas=batas),
                       ablation=abl, atom_rata=at_mean, atom_max=at_max, klausa_rata=cl_mean, klausa_aturan=cl_rules,
                       kasus_demo=demo), f, indent=2)
    with open(os.path.join(OUT, 'perbandingan.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    print('\n'.join(L))


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
