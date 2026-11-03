# Rumah Terkunci · Agen Python

Game deduksi pembunuhan: tim 3 orang berlomba dengan Detektif AI untuk menemukan pelaku, senjata, dan TKP.
Folder ini berisi dua versi Detektif AI yang benar-benar dijalankan dan dibandingkan.

| Versi | Materi | Representasi | Inferensi | Gerak |
|---|---|---|---|---|
| v1 (`agen_v1.py`) | Lecture 04 · Propositional Logic | 64 model, bukti ditulis sebagai fungsi Python | Model checking | BFS ke ruangan belum digeledah / tersangka belum ditanya terdekat |
| v2 (`agen_v2.py`) | Lecture 05 · FOL, Reasoning and Planning | 18 aturan FOL berkuantor + fakta dari bukti | Universal instantiation → CNF → resolusi | Problem formulation (ACTIONS, RESULT, goal test) + A* |

Engine dan agen cukup Python 3.9 atau lebih baru tanpa library tambahan. UI memakai Streamlit
(`pip install -r requirements.txt`).

## Menjalankan

```bash
streamlit run app.py        # UI untuk playtest (Test mode) dan latihan (Normal)
python simulasi.py          # transkrip satu permainan + perbandingan 300 kasus (± 5 menit)
python simulasi.py 50       # versi cepat, 50 kasus
python uji_konsistensi.py   # cek v1 dan v2 selalu menyimpulkan hal yang sama (300 kasus)
python uji_planning.py      # cek A* terhadap BFS
python replay.py            # cek replay log di logs/ sama dengan hasil saat main
python evaluasi.py          # tabel evaluasi dari semua log test mode
```

Hasil ditulis ke folder `hasil/`.

## Isi folder

| File | Isi |
|---|---|
| `kasus.py` | Data rumah, tersangka, senjata, dan generator kasus. Nomor kasus yang sama selalu menghasilkan kasus yang sama. Setiap bukti punya bentuk proposisional (untuk v1) dan FOL (untuk v2). |
| `fol.py` | Sintaks FOL, universal instantiation (reduksi ke proposisional), konversi CNF. |
| `resolusi.py` | Resolusi refutasi dengan resolusi unit, eliminasi literal murni, dan set of support. Mencatat langkah bukti. |
| `planning.py` | Problem formulation gerak AI: state, ACTIONS(s) (`Pindah`, `Teleport`, `Geledah`, `Interogasi`, `Tuduh`), RESULT(s, a), goal test, dan A* dengan heuristik jarak Manhattan. |
| `antarmuka.py` | Kelas dasar `DetektifAI` dan `Tim` (kontrak dengan engine), serta mixin bersama untuk mencatat topik menguping dan model checking. |
| `agen_v1.py` | Detektif AI versi awal. |
| `agen_v2.py` | Detektif AI versi terbaru, termasuk daftar aturan FOL. |
| `agen_baseline.py` | Polisi, detektif penebak, AI diam, dan tim bot pengganti tim manusia. |
| `daftar_ai.py` | Daftar Detektif AI yang bisa dilawan, dipakai bersama oleh UI, replay, dan evaluasi. |
| `permainan.py` | Engine: aturan permainan (ronde, aksi, teleport, menguping, sidang, test mode, log). |
| `denah.py` | Denah rumah, jarak, teleport, dan topik bukti untuk menguping. |
| `teks.py` | Teks tampilan (aksi, jawaban, bukti, kesimpulan) untuk UI dan laporan. |
| `app.py` | UI Streamlit. |
| `buat_pembagian.py`, `pembagian.json` | Pembagian kasus playtest: 28 game per pemain (total 84), 7 per lawan AI. |
| `replay.py` | Memutar ulang aksi tim dari log melawan Detektif AI mana pun. |
| `evaluasi.py` | Tabel evaluasi dari replay semua log test mode. |
| `simulasi.py` | Transkrip dan perbandingan dengan tim bot. |
| `uji_konsistensi.py` | Uji v1 vs v2: kesimpulan harus sama setelah setiap bukti. |
| `uji_planning.py` | Uji A*: rencana sama pendek dengan BFS, heuristik admissible, jumlah node A* vs BFS. |

## Menambah Detektif AI baru

1. Buat kelas turunan `DetektifAI` (atau `AgenV1`/`AgenV2`) dan isi `mulai`, `amati`, `aksi`, dan `tuduhan`
   sesuai kebutuhan. Agen yang bergerak dengan A* atau BFS cukup mewarisi `PerencanaLangkah` dan mengisi `target()`.
2. Daftarkan kelasnya di `LAWAN_AI` (`daftar_ai.py`). UI, replay, dan evaluasi otomatis ikut memakainya.
3. Kalau perlu ikut dimainkan di playtest, tambahkan namanya ke `LAWAN` di `buat_pembagian.py`.

## Konvensi kode

- Nama untuk konsep game memakai bahasa Indonesia (`ronde`, `tuduhan`, `geledah`). Kunci data kasus
  (`case['clues']`, `room_clues`, `found`, `loc`) dan nama API lama (`generate_case`, `neighbors`) tetap
  bahasa Inggris karena dipakai di semua modul dan di log.
- Kode pencarian memakai notasi materi kuliah (AIMA): `frontier`, `parent`, `g`, `h`, `s`, `a`.
- Satu fungsi satu tugas; method yang diawali `_` hanya dipakai di dalam kelas atau modulnya.
- Komentar menjelaskan alasan atau aturan yang tidak terlihat dari kode, bukan mengulang isi kode.

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
