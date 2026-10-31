"""
transkrip.py
Logic — transkrip satu permainan untuk laporan: jalannya v2 (TELL, ASK, rencana A*, bukti resolusi)
dan kasus yang sama dengan v1.
"""
from logic.agen.agen_v1 import AgenV1
from logic.agen.agen_v2 import AgenV2
from logic.agen.tim_bot import TimBot
from logic.kasus.kasus import generate_case
from logic.kasus.rumah import rn, sn
from logic.layar.teks import fakta, teks_aksi, teks_bukti, teks_jawaban
from logic.permainan.permainan import Permainan

# MARK: - Kasus demo

def pilih_kasus_demo(batas=400):
    """Kasus yang memperlihatkan semua mekanik: jasad dipindahkan, salah tangkap,
    kesaksian yang tidak berguna, dan Detektif AI v2 memecahkannya melawan tim bot."""
    for seed in range(1, batas):
        if _kasus_demo_cocok(seed):
            return seed
    return 1


# MARK: - Transkrip

def transkrip(seed, level='normal'):
    case  = generate_case(seed)
    ai    = AgenV2()
    game  = Permainan(seed, ai, TimBot(1), level=level)
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


# MARK: - Private Helpers

def _kasus_demo_cocok(seed):
    case = generate_case(seed)
    if not case['moved'] or case['arrested'] == case['sol'].s:
        return False
    if not any(k['kind'] == 'kesaksian' and not k['relevant'] for k in case['clues']):
        return False
    game  = Permainan(seed, AgenV2(), TimBot(1))
    hasil = game.jalan()
    if hasil['tipe'] != 'ai' or hasil['ronde'] < 5:
        return False
    dilihat_ai = {e['id'] for _, siapa, jenis, data in game.events if siapa == 'ai' and jenis == 'amati' for e in data}
    return any(not case['by_id'][i]['relevant'] and case['by_id'][i]['kind'] == 'kesaksian' for i in dilihat_ai)


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
    game  = Permainan(seed, AgenV1(), TimBot(1), level=level)
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
