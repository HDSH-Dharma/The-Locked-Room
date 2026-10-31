"""
ringkasan.py
Logic — evaluasi: semua log test mode diputar ulang melawan setiap Detektif AI di logic/agen/daftar.py,
lalu diringkas menjadi metrik proposal (menang, presisi tuduhan, presisi/recall bukti tidak berguna).
"""
import csv
import math
from collections import Counter, defaultdict

from logic.agen.daftar import LAWAN_AI
from logic.evaluasi.log import muat_log
from logic.evaluasi.replay import replay
from model.evaluasi_model import KOLOM_LAPORAN, MENANG_AI, MENANG_PEMAIN

# MARK: - Angka dasar

def moe(p, n):
    """Margin of error 95% untuk proporsi p dari n game."""
    return 1.96 * math.sqrt(p * (1 - p) / n) if n else 0


def persen(k, n):
    return f'{100 * k / n:.1f}% ± {100 * moe(k / n, n):.1f}' if n else '-'


def rasio(pembilang, penyebut, format_angka='{:.1f}%', skala=100):
    return format_angka.format(skala * pembilang / penyebut) if penyebut else '-'


# MARK: - Replay semua log

def baca_log():
    """Log test mode di logs/ (logs/latihan/ tidak ikut)."""
    return [log for _, log in muat_log() if log.get('mode') == 'uji']


def jalankan(logs):
    """Satu baris per (log, Detektif AI)."""
    return [_baris_replay(log, nama, buat_agen()) for log in logs for nama, buat_agen in LAWAN_AI.items()]


# MARK: - Ringkasan

def ringkas(baris):
    per_ai = defaultdict(list)
    for b in baris:
        per_ai[b['ai']].append(b)
    return {nama: ringkas_ai(rows) for nama, rows in per_ai.items()}


def ringkas_ai(rows):
    n    = len(rows)
    tipe = Counter(b['tipe'] for b in rows)
    presisi_useless, recall_useless = _presisi_recall_useless(rows)
    return dict(
        n=n,
        pemain_menang=persen(sum(tipe[t] for t in MENANG_PEMAIN), n),
        ai_menang=persen(sum(tipe[t] for t in MENANG_AI), n),
        seri=persen(tipe['vonis'], n),
        presisi_tuduhan=rasio(tipe['ai'], tipe['ai'] + tipe['ai-salah']),
        ronde_ai_menang=_rata_ronde_ai_menang(rows),
        aksi_ai=f'{sum(b["aksi_ai"] for b in rows) / n:.1f}',
        presisi_useless=presisi_useless,
        recall_useless=recall_useless,
        konflik_teleport=sum(b['konflik_teleport'] for b in rows))


def per_pemain(baris, ai='v2'):
    rows = defaultdict(list)
    for b in baris:
        if b['ai'] == ai:
            rows[b['pemain']].append(b)
    return {p: persen(sum(b['tipe'] in MENANG_PEMAIN for b in rs), len(rs)) for p, rs in sorted(rows.items())}


# MARK: - Keluaran

def tulis_csv(baris, path):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[k for k in baris[0] if k != 'label'], extrasaction='ignore')
        writer.writeheader()
        writer.writerows(baris)


def tabel_markdown(ringkasan, pemain):
    n = next(iter(ringkasan.values()))['n']
    baris = [f'# Evaluasi replay ({n} log test mode)\n',
             '| AI | ' + ' | '.join(judul for _, judul in KOLOM_LAPORAN) + ' |',
             '|---' * (len(KOLOM_LAPORAN) + 1) + '|']
    baris += [f'| {nama} | ' + ' | '.join(str(r[k]) for k, _ in KOLOM_LAPORAN) + ' |' for nama, r in ringkasan.items()]
    baris += ['\n## Pemain menang melawan v2, per pemain\n', '| Pemain | Pemain menang |', '|---|---|']
    baris += [f'| {p} | {v} |' for p, v in pemain.items()]
    return '\n'.join(baris)


# MARK: - Private Helpers

def _baris_replay(log, nama, agen):
    game, hasil, konflik = replay(log, agen)
    label = [(e['relevan'], game.case['by_id'][e['id']]['relevant']) for e in getattr(agen, 'log', [])]
    return dict(seed=log['seed'], pemain=log['pemain'], ai_live=log['ai_live'], ai=nama, tipe=hasil['tipe'],
                ronde=hasil['ronde'], aksi_ai=game.ai_aksi, konflik_teleport=konflik, label=label)


def _rata_ronde_ai_menang(rows):
    ronde = [b['ronde'] for b in rows if b['tipe'] == 'ai']
    return rasio(sum(ronde), len(ronde), '{:.2f}', skala=1)


def _presisi_recall_useless(rows):
    """Kelas positif = bukti tidak berguna. Pasangan label = (penilaian AI, kebenaran generator)."""
    pasangan = [p for b in rows for p in b['label']]
    tp       = sum(1 for pred, benar in pasangan if not pred and not benar)
    fp       = sum(1 for pred, benar in pasangan if not pred and benar)
    fn       = sum(1 for pred, benar in pasangan if pred and not benar)
    return rasio(tp, tp + fp), rasio(tp, tp + fn)
