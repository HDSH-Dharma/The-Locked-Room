# Coding Agreement · Rumah Terkunci

Aturan menulis kode untuk semua anggota tim. Setiap PR ke `rapikan_kode` harus mengikuti aturan ini.

## 1. Satu folder satu peran

| Folder | Peran | Boleh berisi | Tidak boleh |
| --- | --- | --- | --- |
| `models/` | Data murni | Konstanta, tabel teks, `namedtuple`, konstruktor data, indeks turunan (comprehension) | Logika (if/loop keputusan), import dari folder lain selain `models/` |
| `services/` | Logika domain tanpa UI | Generator kasus, denah, FOL, resolusi, KB, planning, log, replay, evaluasi | `streamlit`, import dari `views/` atau `viewmodels/` |
| `agents/` | Pemain: Detektif AI dan tim | Turunan `DetektifAI`/`Tim` (`kontrak_agent.py`), mixin bersama (`mixin_agent.py`) | Aturan permainan, UI |
| `engine/` | Aturan permainan | `Permainan`: ronde, aksi, teleport, menguping, sidang, log | Logika agen, UI |
| `viewmodels/` | Semua logika UI | Menjalankan aksi dari tombol, menyiapkan teks, daftar tombol, isi peta, trace | Pemanggilan `st.*` |
| `views/` | Menampilkan saja | `st.*`, if/else/for untuk menampilkan data dari viewmodel | Menghitung, memformat teks yang butuh logika, memanggil engine atau service |
| `scripts/` | Titik masuk command line | `main()` yang memanggil service dan menulis file | Logika yang dipakai ulang (taruh di `services/`) |
| `tests/` | Skrip uji | Pembanding dan pengecekan | Logika yang dipakai modul lain |

`app.py` tetap di root sebagai titik masuk Streamlit (`streamlit run app.py`).

Arah import yang boleh: `views` → `viewmodels` → `engine`/`agents`/`services` → `models`. Tidak boleh ada import melingkar.

## 2. Penamaan

| Jenis | Aturan | Contoh |
| --- | --- | --- |
| File | `<fitur>_<peran>.py`, huruf kecil dan garis bawah | `rumah_model.py`, `kasus_service.py`, `v2_agent.py`, `permainan_engine.py`, `permainan_viewmodel.py`, `peta_view.py` |
| File yang dikecualikan | `app.py`, file di `scripts/`, `tests/uji_<topik>.py` | `scripts/simulasi.py`, `tests/uji_planning.py` |
| Kelas | PascalCase; viewmodel diakhiri `ViewModel` | `Permainan`, `AgenV2`, `PermainanViewModel` |
| Fungsi dan variabel | snake_case, bahasa Indonesia untuk konsep game | `tuduh_tim`, `jatah_berikutnya`, `ronde` |
| Istilah materi kuliah | Tetap seperti di slide | `frontier`, `parent`, `g`, `h`, `actions`, `result`, `KB`, `tell`, `ask` |
| Kunci data kasus dan API lama | Tetap bahasa Inggris (dipakai di log playtest) | `case['clues']`, `found`, `loc`, `generate_case` |
| Konstanta | HURUF_BESAR, di `models/` | `MAX_ROUNDS`, `PELUANG_TANGKAP_PELAKU` |
| Awalan `_` | Hanya dipakai di file atau kelas itu sendiri | `_pesan_aksi`, `_bfs` |

## 3. Isi satu file

Satu file membahas satu konteks. Kalau sebuah file mulai membahas dua hal, pecah menjadi dua file.

```python
"""
contoh_service.py
Service — <isi file dalam satu kalimat>.

Penjelasan tambahan kalau perlu: aturan proposal yang dipegang, alasan desain.
"""
import json                                     # 1. standard library

from models.rumah_model import S_IDS, TKP       # 2. modul proyek, urut folder lalu abjad
from services.acak_service import pick

# MARK: - API                                   # 3. bagian publik, dikelompokkan per konteks

def fungsi_publik(seed):
    ...


# MARK: - Private Helpers                       # 4. helper privat selalu di paling bawah

def _helper(nilai):
    ...
```

- Baris pertama docstring adalah nama file, baris kedua `<Peran> — <isi file>`. Peran: Model, Service, Agent, Engine, ViewModel, View, Script, atau Test.
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

**View hanya menampilkan.** Semua teks, daftar tombol, dan keputusan tampil datang dari viewmodel.

```python
# Salah: view menghitung dan memformat sendiri
st.caption(f'Teleport: {"sudah dipakai" if g.tp_holder == "terpakai" else "..."}')

# Benar: viewmodel menyiapkan, view menampilkan
st.caption(vm.status_bawah_peta())
```

**ViewModel tanpa `st.*`.** ViewModel mengembalikan data siap tampil (string, list, dict) dan menjalankan aksi dari tombol. State tampilan sementara (misalnya `ai_pending`, isi kotak catatan) tetap di `st.session_state` milik view.

**Service tanpa state tersembunyi.** Satu-satunya pengecualian adalah denah aktif (`denah_service.pakai_denah`), yang sudah didokumentasikan.

**Agent mewarisi kontrak.** Detektif AI baru mewarisi `DetektifAI` (atau `AgenV1`/`AgenV2`) dan didaftarkan di `agents/daftar_agent.py`. Agen yang bergerak dengan A* atau BFS cukup mewarisi `PerencanaLangkah` dan mengisi `target()`.

## 5. Komentar

- Docstring modul wajib. Docstring fungsi wajib untuk fungsi publik yang maksudnya tidak jelas dari namanya.
- Komentar menjelaskan alasan atau aturan, bukan mengulang isi kode.
- Bahasa Indonesia.
- Tidak boleh ada kode yang dimatikan (commented-out), TODO tanpa nama, atau komentar yang merujuk ke alat bantu penulis kode.

## 6. Jangan diubah selama dan setelah playtest

Perubahan berikut membuat 300 log playtest tidak bisa di-replay lagi:

- Urutan pemanggilan `rnd()` di `kasus_service.py` dan isi `acak_service.py`.
- Teks dan peluang di `models/bukti_model.py`, data di `models/rumah_model.py`, dan `pembagian.json`.
- Format log (`Permainan.ke_log`) dan kunci data kasus.

## 7. Git dan pull request

- Nama branch `<nama>/<topik>`, misalnya `grevi/ui-fix` atau `jason/evaluasi`.
- Semua PR ke `rapikan_kode`. `rapikan_kode` ke `main` digabung oleh Dharma.
- Judul commit singkat (maksimal 72 karakter), berupa kalimat perintah, bahasa Indonesia atau Inggris.
- Jangan commit `logs/latihan/`, `hasil/*.json`, `__pycache__/`, atau file konfigurasi editor dan alat pribadi.
- Log test mode (`logs/<inisial>_<kasus>.json`) di-commit oleh pemiliknya sendiri.

Sebelum membuka PR, jalankan dari folder repo:

```bash
ruff check --select F,E,W,B --line-length 130 .
python -m tests.uji_konsistensi 20
python -m tests.uji_planning 20
python -m tests.uji_replay          # kalau sudah ada log di logs/
streamlit run app.py                # mainkan satu game sampai selesai
```

## 8. Checklist PR

- [ ] File baru ada di folder peran yang tepat dan bernama `<fitur>_<peran>.py`
- [ ] Docstring modul (nama file + peran) dan bagian `# MARK: -`
- [ ] Helper privat di bagian paling bawah
- [ ] Model tanpa logika, view tanpa logika, viewmodel tanpa `st.*`
- [ ] Tidak ada fungsi yang lebih dari ±25 baris
- [ ] Tidak ada yang diubah dari daftar di bagian 6
- [ ] `ruff` bersih dan semua uji di atas lolos
