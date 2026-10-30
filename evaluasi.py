"""Evaluasi: semua log test mode diputar ulang melawan v2, v1, polisi dan penebak.

  python evaluasi.py      -> hasil/evaluasi.csv (semua baris) dan hasil/evaluasi.md (tabel laporan)
"""
import csv
import glob
import json
import math
import os
from collections import Counter, defaultdict

from replay import AGEN, replay


def moe(p, n):
    """Margin of error 95% untuk proporsi p dari n game."""
    return 1.96 * math.sqrt(p * (1 - p) / n) if n else 0


def persen(k, n):
    return f'{100 * k / n:.1f}% ± {100 * moe(k / n, n):.1f}' if n else '-'


def baca_log():
    logs = [json.load(open(f)) for f in sorted(glob.glob('logs/*.json'))]   # logs/latihan/ tidak ikut
    return [log for log in logs if log.get('mode') == 'uji']


def jalankan(logs):
    baris = []
    for log in logs:
        for nama, buat in AGEN.items():
            agen = buat()
            g, h, konflik = replay(log, agen)
            label = [(e['relevan'], g.case['by_id'][e['id']]['relevant']) for e in getattr(agen, 'log', [])]
            baris.append(dict(seed=log['seed'], pemain=log['pemain'], ai_live=log['ai_live'], ai=nama,
                              tipe=h['tipe'], ronde=h['ronde'], aksi_ai=g.ai_aksi, konflik_teleport=konflik,
                              label=label))
    return baris


def ringkas(baris):
    per_ai = defaultdict(list)
    for b in baris:
        per_ai[b['ai']].append(b)
    out = {}
    for nama, rows in per_ai.items():
        n = len(rows)
        c = Counter(b['tipe'] for b in rows)
        menang_ai = [b for b in rows if b['tipe'] == 'ai']
        # useless = bukti tidak berguna; positif = AI menilai "tidak berguna"
        pasangan = [p for b in rows for p in b['label']]
        tp = sum(1 for pred, benar in pasangan if not pred and not benar)
        fp = sum(1 for pred, benar in pasangan if not pred and benar)
        fn = sum(1 for pred, benar in pasangan if pred and not benar)
        out[nama] = dict(
            n=n,
            pemain_menang=persen(c['tim'] + c['ai-salah'], n),
            ai_menang=persen(c['ai'] + c['tim-salah'], n),
            seri=persen(c['vonis'], n),
            presisi_tuduhan=f'{100 * c["ai"] / (c["ai"] + c["ai-salah"]):.1f}%' if c['ai'] + c['ai-salah'] else '-',
            ronde_ai_menang=f'{sum(b["ronde"] for b in menang_ai) / len(menang_ai):.2f}' if menang_ai else '-',
            aksi_ai=f'{sum(b["aksi_ai"] for b in rows) / n:.1f}',
            presisi_useless=f'{100 * tp / (tp + fp):.1f}%' if tp + fp else '-',
            recall_useless=f'{100 * tp / (tp + fn):.1f}%' if tp + fn else '-',
            konflik_teleport=sum(b['konflik_teleport'] for b in rows))
    return out


def per_pemain(baris, ai='v2'):
    rows = defaultdict(list)
    for b in baris:
        if b['ai'] == ai:
            rows[b['pemain']].append(b)
    return {p: persen(sum(b['tipe'] in ('tim', 'ai-salah') for b in rs), len(rs)) for p, rs in sorted(rows.items())}


def tulis(baris, ringkasan, pemain):
    os.makedirs('hasil', exist_ok=True)
    with open('hasil/evaluasi.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=[k for k in baris[0] if k != 'label'], extrasaction='ignore')
        w.writeheader()
        w.writerows(baris)
    kolom = [('pemain_menang', 'Pemain menang'), ('ai_menang', 'AI menang'), ('seri', 'Seri'),
             ('presisi_tuduhan', 'Presisi tuduhan AI'), ('ronde_ai_menang', 'Ronde saat AI menang'),
             ('aksi_ai', 'Aksi AI'), ('presisi_useless', 'Presisi useless'), ('recall_useless', 'Recall useless'),
             ('konflik_teleport', 'Konflik teleport')]
    n = next(iter(ringkasan.values()))['n']
    L = [f'# Evaluasi replay ({n} log test mode)\n',
         '| AI | ' + ' | '.join(k for _, k in kolom) + ' |', '|---' * (len(kolom) + 1) + '|']
    for nama, r in ringkasan.items():
        L.append(f'| {nama} | ' + ' | '.join(str(r[k]) for k, _ in kolom) + ' |')
    L += ['\n## Pemain menang melawan v2, per pemain\n', '| Pemain | Pemain menang |', '|---|---|']
    L += [f'| {p} | {v} |' for p, v in pemain.items()]
    with open('hasil/evaluasi.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    logs = baca_log()
    baris = jalankan(logs)
    tulis(baris, ringkas(baris), per_pemain(baris))

