# Coding Agreement · Rumah Terkunci

Aturan menulis kode untuk semua anggota tim. Setiap PR ke `rapikan_kode` harus mengikuti aturan ini.

## 1. Tiga lapisan: UI, model, logic

| Folder | Isi | Boleh | Tidak boleh |
| --- | --- | --- | --- |
| `model/` | Data murni | Konstanta, tabel teks, `namedtuple`, konstruktor data, indeks turunan (comprehension) | Fungsi yang mengambil keputusan; import dari `logic/` atau `ui/` |
| `logic/` | Semua logika | Generator kasus, penalaran, agen, aturan permainan, logika layar, playtest, evaluasi | `st.*` (Streamlit); import dari `ui/` |
| `ui/` | Tampilan Streamlit saja | `st.*` dan if/else/for untuk menampilkan data yang disiapkan `logic/layar/` | Menghitung, memformat teks yang butuh logika, memanggil engine atau generator langsung |

Di dalam `logic/`, file dikelompokkan per konteks. Satu konteks satu folder:

| Folder | Konteks |
| --- | --- |
| `logic/kasus/` | RNG, nama tampil, generator kasus, denah dan teleport, topik menguping |
| `logic/penalaran/` | FOL, resolusi, KB (TELL/ASK), planning A*/BFS |
| `logic/agen/` | Kontrak `DetektifAI`/`Tim`, mixin, Detektif AI v1/v2, baseline, tim bot, tim rekaman, daftar lawan |
| `logic/permainan/` | Aturan permainan (`Permainan`) |
| `logic/layar/` | Logika layar UI (`LayarPermainan`, `LayarSidebar`) dan teks tampilan |
| `logic/playtest/` | Log game test mode, pembagian 300 kasus dan jatah tiap pemain, replay log |
| `logic/evaluasi/` | Ringkasan evaluasi dari log playtest, uji konsistensi, transkrip, perbandingan simulasi |

Di luar tiga lapisan itu hanya ada titik masuk: `app.py` (Streamlit, `streamlit run app.py`), `scripts/` (perintah command line), dan `tests/` (skrip uji).

Arah import yang boleh: `ui` → `logic` → `model`. `model` hanya mengimpor `model`. Tidak boleh ada import melingkar.

## 2. Penamaan

| Jenis | Aturan | Contoh |
| --- | --- | --- |
| File di `model/` | `<fitur>_model.py` | `rumah_model.py`, `bukti_model.py`, `aturan_model.py` |
| File di `ui/` | `<bagian layar>_ui.py` | `peta_ui.py`, `aksi_ui.py`, `hasil_ui.py` |
| File di `logic/<konteks>/` | `<fitur>.py`; folder sudah menyebut konteksnya | `logic/kasus/kasus.py`, `logic/penalaran/resolusi.py`, `logic/agen/agen_v2.py` |
| File titik masuk | `app.py`, `scripts/<perintah>.py`, `tests/uji_<topik>.py` | `scripts/simulasi.py`, `tests/uji_planning.py` |
| Kelas | PascalCase; logika layar diawali `Layar` | `Permainan`, `AgenV2`, `LayarPermainan` |
| Fungsi dan variabel | snake_case, bahasa Indonesia untuk konsep game | `tuduh_tim`, `jatah_berikutnya`, `ronde` |
| Istilah materi kuliah | Tetap seperti di slide | `frontier`, `parent`, `g`, `h`, `actions`, `result`, `KB`, `tell`, `ask` |
| Kunci data kasus dan API lama | Tetap bahasa Inggris (dipakai di log playtest) | `case['clues']`, `found`, `loc`, `generate_case` |
| Konstanta | HURUF_BESAR, di `model/` | `MAX_ROUNDS`, `PELUANG_TANGKAP_PELAKU` |
| Awalan `_` | Hanya dipakai di file atau kelas itu sendiri | `_pesan_aksi`, `_bfs` |

## 3. Isi satu file

Satu file membahas satu konteks. Kalau sebuah file mulai membahas dua hal, pecah menjadi dua file.

```python
"""
contoh.py
Logic — <isi file dalam satu kalimat>.

Penjelasan tambahan kalau perlu: aturan proposal yang dipegang, alasan desain.
"""
import json                                     # 1. standard library

from logic.kasus.acak import pick               # 2. modul proyek: logic, lalu model (urutan abjad)
from model.rumah_model import S_IDS, TKP

# MARK: - API                                   # 3. bagian publik, dikelompokkan per konteks

def fungsi_publik(seed):
    ...


# MARK: - Private Helpers                       # 4. helper privat selalu di paling bawah

def _helper(nilai):
    ...
```

- Baris pertama docstring adalah nama file, baris kedua `<Lapisan> — <isi file>`. Lapisan: Model, Logic, UI, Script, atau Test.
- Bagian dipisah dengan `# MARK: - <Judul>`. VS Code menampilkannya sebagai judul bagian di minimap.
- Urutan dalam file: konstanta atau state, lalu API publik per bagian, lalu `# MARK: - Private Helpers` di paling bawah.
- Urutan dalam kelas: `__init__`, method publik per bagian, lalu `# MARK: - Private · <konteks>` untuk method berawalan `_`.
- Satu fungsi satu tugas. Fungsi yang lebih dari ±25 baris atau bercabang banyak dipecah ke helper privat.
- Blok deklarasi yang berurutan diratakan tanda `=`-nya, begitu juga komentar di ujung barisnya:

```python
self.ronde         = 1
self.hasil         = None
self.events        = []         # (ronde, pelaku, jenis, data)
self.stat          = Counter()  # menguping, teleport
```

## 4. Aturan per lapisan

**Model tanpa logika.** Boleh menghitung indeks turunan sekali saat dimuat (`S_IDS = [s[0] for s in SUSPECTS]`). Tidak boleh ada fungsi yang mengambil keputusan.

**UI hanya menampilkan.** Semua teks, daftar tombol, dan keputusan tampil datang dari `logic/layar/`.

```python
# Salah: UI menghitung dan memformat sendiri
st.caption(f'Teleport: {"sudah dipakai" if g.tp_holder == "terpakai" else "..."}')

# Benar: logic/layar menyiapkan, UI menampilkan
st.caption(layar.status_bawah_peta())
```

**Logic tanpa `st.*`.** `logic/layar/` mengembalikan data siap tampil (string, list, dict) dan menjalankan aksi dari tombol. State tampilan sementara (misalnya `ai_pending`, isi kotak catatan) tetap di `st.session_state` milik UI.

**Tanpa state tersembunyi.** Satu-satunya pengecualian adalah denah aktif (`logic/kasus/denah.py`, `pakai_denah`), yang sudah didokumentasikan.

**Agen mewarisi kontrak.** Detektif AI baru mewarisi `DetektifAI` (atau `AgenV1`/`AgenV2`) dari `logic/agen/kontrak.py` dan didaftarkan di `logic/agen/daftar.py`. Agen yang bergerak dengan A* atau BFS cukup mewarisi `PerencanaLangkah` dan mengisi `target()`.

## 5. Komentar

- Docstring modul wajib. Docstring fungsi wajib untuk fungsi publik yang maksudnya tidak jelas dari namanya.
- Komentar menjelaskan alasan atau aturan, bukan mengulang isi kode.
- Bahasa Indonesia.
- Tidak boleh ada kode yang dimatikan (commented-out), TODO tanpa nama, atau komentar yang merujuk ke alat bantu penulis kode.

## 6. Jangan diubah selama dan setelah playtest

Perubahan berikut membuat 300 log playtest tidak bisa di-replay lagi:

- Urutan pemanggilan `rnd()` di `logic/kasus/kasus.py` dan isi `logic/kasus/acak.py`.
- Teks dan peluang di `model/bukti_model.py`, data di `model/rumah_model.py`, dan `pembagian.json`.
- Format log (`Permainan.ke_log`) dan kunci data kasus.

## 7. Git dan pull request

- Nama branch `<nama>/<topik>`, misalnya `grevi/ui-fix` atau `jason/evaluasi`.
- Semua PR ke `rapikan_kode`. `rapikan_kode` ke `main` digabung oleh Dharma.
- Judul commit singkat (maksimal 72 karakter), berupa kalimat perintah, bahasa Indonesia atau Inggris.
- Jangan commit `logs/latihan/`, `hasil/*.json`, `__pycache__/`, atau file konfigurasi editor dan alat pribadi.
- Log test mode (`logs/<inisial>_<kasus>.json`) di-commit oleh pemiliknya sendiri.

Sebelum membuka PR, jalankan dari folder repo (`pip install ruff` sekali; aturannya ada di `ruff.toml`):

```bash
ruff check .
python -m tests.uji_konsistensi 20
python -m tests.uji_planning 20
python -m tests.uji_replay          # kalau sudah ada log di logs/
streamlit run app.py                # mainkan satu game sampai selesai
```

## 8. Checklist PR

- [ ] File baru ada di lapisan yang tepat (`model/`, `logic/<konteks>/`, atau `ui/`) dan namanya mengikuti bagian 2
- [ ] Docstring modul (nama file + lapisan) dan bagian `# MARK: -`
- [ ] Helper privat di bagian paling bawah
- [ ] Model tanpa logika, UI tanpa logika, logic tanpa `st.*`
- [ ] Tidak ada fungsi yang lebih dari ±25 baris
- [ ] Tidak ada yang diubah dari daftar di bagian 6
- [ ] `ruff check .` bersih dan semua uji di atas lolos
