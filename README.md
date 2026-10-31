# Rumah Terkunci · Agen Python

Game deduksi pembunuhan: tim 3 orang berlomba dengan Detektif AI untuk menemukan pelaku, senjata, dan TKP.
Folder ini berisi dua versi Detektif AI yang benar-benar dijalankan dan dibandingkan.

| Versi | Materi | Representasi | Inferensi | Gerak |
|---|---|---|---|---|
| v1 (`logic/agen/agen_v1.py`) | Lecture 04 · Propositional Logic | 64 model, bukti ditulis sebagai fungsi Python | Model checking | BFS ke ruangan belum digeledah / tersangka belum ditanya terdekat |
| v2 (`logic/agen/agen_v2.py`) | Lecture 05 · FOL, Reasoning and Planning | 18 aturan FOL berkuantor + fakta dari bukti | Universal instantiation → CNF → resolusi | Problem formulation (ACTIONS, RESULT, goal test) + A* |

Engine dan agen cukup Python 3.9 atau lebih baru tanpa library tambahan. UI memakai Streamlit
(`pip install -r requirements.txt`).

## Menjalankan

Semua perintah dijalankan dari folder repo.

```bash
streamlit run app.py                # UI untuk playtest (Test mode) dan latihan (Normal)
python -m scripts.simulasi          # transkrip satu permainan + perbandingan 300 kasus (± 5 menit)
python -m scripts.simulasi 50       # versi cepat, 50 kasus
python -m scripts.evaluasi          # tabel evaluasi dari semua log test mode
python -m tests.uji_konsistensi     # cek v1 dan v2 selalu menyimpulkan hal yang sama (300 kasus)
python -m tests.uji_planning        # cek A* terhadap BFS
python -m tests.uji_replay          # cek replay log di logs/ sama dengan hasil saat main
```

Hasil ditulis ke folder `hasil/`.

## Struktur folder

Tiga lapisan: `model/` (data), `logic/` (semua logika, dikelompokkan per konteks), dan `ui/` (tampilan).
Aturan lengkapnya ada di [CODING_AGREEMENT.md](CODING_AGREEMENT.md).

| Folder | Isi |
|---|---|
| `model/` | Data saja: rumah dan tersangka (`rumah_model`), denah (`denah_model`), angka dan teks bukti (`bukti_model`), bentuk formula FOL (`fol_model`), 18 aturan FOL (`aturan_model`), topik menguping, state planning, teks UI, pembagian, folder, kolom evaluasi. |
| `logic/kasus/` | RNG mulberry32 (`acak`), nama tampil (`rumah`), generator kasus (`kasus`), denah dan teleport (`denah`), topik menguping (`topik`). |
| `logic/penalaran/` | FOL dan CNF (`fol`), resolusi refutasi (`resolusi`), KB dengan TELL/ASK (`kb`), problem formulation dan A*/BFS (`planning`). |
| `logic/agen/` | Kontrak `DetektifAI` dan `Tim` (`kontrak`), mixin bersama (`mixin`), Detektif AI v1 dan v2, baseline (polisi, penebak), tim bot, tim rekaman log, tim manusia, dan daftar `LAWAN_AI` (`daftar`). |
| `logic/permainan/` | Aturan permainan (`permainan`): ronde, aksi, teleport, menguping, sidang, test mode, log. |
| `logic/layar/` | Logika layar UI: `LayarPermainan` (aksi tombol, peta, catatan, trace, hasil), `LayarSidebar` (jatah game, pilihan latihan), dan teks tampilan (`teks`). |
| `logic/playtest/` | Log game test mode (`log`), pembagian 300 kasus dan jatah game tiap pemain (`pembagian`), replay log melawan Detektif AI mana pun (`replay`). |
| `logic/evaluasi/` | Ringkasan evaluasi dari log playtest (`ringkasan`), uji konsistensi v1 vs v2 (`konsistensi`), transkrip (`transkrip`), perbandingan simulasi (`perbandingan`). |
| `ui/` | Tampilan Streamlit: halaman, sidebar, peta, aksi, catatan, hasil, komponen. |
| `scripts/` | Perintah: `simulasi`, `evaluasi`, `buat_pembagian`. |
| `tests/` | Uji: `uji_konsistensi`, `uji_planning`, `uji_replay`. |
| `app.py` | Titik masuk Streamlit. |
| `pembagian.json` | Pembagian 300 kasus playtest: 100 per pemain, 25 per lawan AI. |

## Menambah Detektif AI baru

1. Buat file `logic/agen/<nama>.py` berisi turunan `DetektifAI` (atau `AgenV1`/`AgenV2`), dan isi `mulai`,
   `amati`, `aksi`, dan `tuduhan` sesuai kebutuhan. Agen yang bergerak dengan A* atau BFS cukup mewarisi
   `PerencanaLangkah` dan mengisi `target()`.
2. Daftarkan kelasnya di `LAWAN_AI` (`logic/agen/daftar.py`). UI, replay, dan evaluasi otomatis ikut memakainya.
3. Kalau perlu ikut dimainkan di playtest, tambahkan namanya ke `LAWAN` di `model/pembagian_model.py`.

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
