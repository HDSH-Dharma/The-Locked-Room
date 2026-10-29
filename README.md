# Rumah Terkunci · Agen Python

Game deduksi pembunuhan: tim 3 orang berlomba dengan Detektif AI untuk menemukan pelaku, senjata, dan TKP.
Folder ini berisi dua versi Detektif AI yang benar-benar dijalankan dan dibandingkan.

| Versi | Materi | Representasi | Inferensi | Gerak |
|---|---|---|---|---|
| v1 (`agen_v1.py`) | Lecture 04 · Propositional Logic | 64 model, bukti ditulis sebagai fungsi Python | Model checking | BFS ke ruangan belum digeledah / tersangka belum ditanya terdekat |
| v2 (`agen_v2.py`) | Lecture 05 · FOL, Reasoning and Planning | 18 aturan FOL berkuantor + fakta dari bukti | Universal instantiation → CNF → resolusi | Problem formulation (ACTIONS, RESULT, goal test) + A* |

Tidak butuh library tambahan. Cukup Python 3.9 atau lebih baru.

## Menjalankan

```bash
python simulasi.py          # transkrip satu permainan + perbandingan 300 kasus (± 5 menit)
python simulasi.py 50       # versi cepat, 50 kasus
python uji_konsistensi.py   # cek v1 dan v2 selalu menyimpulkan hal yang sama (300 kasus)
python uji_planning.py      # cek A* terhadap BFS
```

Hasil ditulis ke folder `hasil/`.

## Isi folder

| File | Isi |
|---|---|
| `kasus.py` | Data rumah, tersangka, senjata, dan generator kasus. Nomor kasus yang sama selalu menghasilkan kasus yang sama. Setiap bukti punya bentuk proposisional (untuk v1) dan FOL (untuk v2). |
| `fol.py` | Sintaks FOL, universal instantiation (reduksi ke proposisional), konversi CNF. |
| `resolusi.py` | Resolusi refutasi dengan resolusi unit, eliminasi literal murni, dan set of support. Mencatat langkah bukti. |
| `planning.py` | Problem formulation gerak AI: state, ACTIONS(s) (`Pindah`, `Teleport`, `Geledah`, `Interogasi`, `Tuduh`), RESULT(s, a), goal test, dan A* dengan heuristik jarak Manhattan. |
| `agen_v1.py` | Detektif AI versi awal. |
| `agen_v2.py` | Detektif AI versi materi terbaru, termasuk daftar aturan FOL. |
| `agen_baseline.py` | Polisi gegabah, detektif penebak, dan tim bot pengganti tim manusia. |
| `permainan.py` | Aturan permainan (ronde, aksi, sidang). |
| `simulasi.py` | Transkrip dan perbandingan. |
| `uji_konsistensi.py` | Uji v1 vs v2: kesimpulan harus sama setelah setiap bukti. |
| `uji_planning.py` | Uji A*: rencana sama pendek dengan BFS, heuristik admissible, jumlah node A* vs BFS. |

## Cara main singkat

1. Jasad Tuan Hartono ditemukan di salah satu ruangan. Polisi langsung menangkap seseorang berdasarkan motif dan gosip.
2. Tiap ronde, detektif 1, 2, 3 masing-masing 1 aksi: pindah ke ruangan sebelah, geledah ruangan yang belum digeledah, atau interogasi tersangka di ruangan itu. Isi ruangan baru ketahuan setelah digeledah; ruangan kosong tidak memberi bukti. Ruang Tamu sudah diperiksa polisi (isinya berkas polisi), jadi tidak bisa digeledah.
3. Pelaku selalu berbohong. Tersangka yang tidak bersalah selalu jujur. Kesaksian tidak pernah menyebut pelaku asli secara langsung.
4. Jasad bisa sudah dipindahkan, jadi tempat jasad ditemukan belum tentu TKP.
5. Detektif AI bergerak 2–3 aksi setelah tim. Ia hanya menuduh kalau KB ⊨ jawabannya.
6. Setelah ronde 7, sidang: tim boleh menuduh sekali lagi. Kalau tidak, hakim memvonis orang yang ditangkap polisi.

## Contoh perbedaan kode

Bukti "Hanya Budi dan Dimas yang cukup kuat untuk memindahkan jasad":

```python
# v1: arti bukti ditulis tangan sebagai fungsi atas 64 model
lambda m: m.r == found or m.s in ('budi', 'dimas')

# v2: aturan umum ditulis SEKALI, bukti hanya menambah fakta
('R16', ForAll(x, 'orang', Imp(And(P(x), Atom('Dipindahkan')), Atom('Kuat', x))))
[Atom('Kuat', 'Budi'), Atom('Kuat', 'Dimas'), Not(Atom('Kuat', 'Sari')), Not(Atom('Kuat', 'Nadia'))]
```

Di v1, pembuat kode harus menurunkan sendiri bahwa "jasad dipindahkan" sama dengan "TKP bukan tempat jasad ditemukan".
Di v2, hubungan itu ditulis sebagai aturan R11 dan diturunkan oleh resolusi.
