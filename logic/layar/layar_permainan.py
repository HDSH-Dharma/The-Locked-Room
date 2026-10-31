"""
layar_permainan.py
Logic — semua logika layar permainan: aksi dari tombol, isi peta, daftar tombol, catatan,
trace, hasil, dan penyimpanan log. UI cukup menampilkan apa yang disiapkan di sini.

Satu objek dipakai untuk satu game dan disimpan di st.session_state.layar.
"""
import os
import time

from logic.agen.daftar import LAWAN_AI
from logic.agen.manusia import TimManusia
from logic.kasus.rumah import rn, sn, wn
from logic.layar.teks import fakta, target_menguping, teks_aksi, teks_bukti, teks_jawaban
from logic.permainan.permainan import Permainan
from logic.playtest.log import simpan_log
from model.folder_model import FOLDER_LATIHAN, FOLDER_LOGS
from model.rumah_model import MAX_ROUNDS, POS, R_IDS, S_IDS, START, TKP, W_IDS, WAKTU_KEMATIAN
from model.ui_model import HASIL_TEKS, KASUS_PLAYTEST, TUDUHAN_TIM_TEKS, WARNA_AI, WARNA_D


class LayarPermainan:
    """Satu game yang sedang dimainkan di UI."""

    def __init__(self, pemain, seed, ai_live, uji):
        self.game = Permainan(seed, LAWAN_AI[ai_live](), TimManusia(), teleport=True, menguping=True, uji=uji)
        self.game.mulai()
        self.pemain    = pemain
        self.ai_live   = ai_live
        self.t_mulai   = time.time()
        self.t_selesai = None
        self.log_path  = None
        self.pesan     = None

    # MARK: - Aksi dari tombol

    def jalankan_aksi(self, d, act):
        """Aksi detektif d dari tombol. Mengembalikan True kalau sesudahnya giliran Detektif AI."""
        g = self.game
        if g.giliran_tim() != d or act not in g.aksi_legal(d):
            return False                        # klik basi (misalnya tombol ditekan dua kali)
        tp_sebelum = g.tp_holder
        found      = g.aksi_tim(d, act)
        self.pesan = self._pesan_aksi(d, act, found, tp_sebelum)
        return g.giliran_tim() is None

    def tuduh(self, jawaban):
        g = self.game
        if g.hasil or (g.giliran_tim() is None and not g.sidang_dibuka):
            return
        g.tuduh_tim(jawaban)

    def serahkan_ke_hakim(self):
        g = self.game
        if g.sidang_dibuka and not g.hasil:
            g.tuduh_tim(None)

    def jalankan_giliran_ai(self):
        """Giliran Detektif AI. Mengembalikan bingkai animasi (posisi AI atau None, teks info)
        untuk mode normal; test mode tanpa animasi, jadi daftarnya kosong."""
        g       = self.game
        langkah = g.giliran_ai()
        self.pesan = 'Giliran Detektif AI selesai: ' + (
            '; '.join(teks_aksi(act) for _, act in langkah) if langkah else 'tidak bergerak') + '.'
        if g.uji:
            return []
        return self._bingkai_animasi(langkah)

    def selesaikan(self):
        """Catat waktu selesai dan simpan log, sekali saja per game."""
        if self.t_selesai is not None:
            return
        g              = self.game
        self.t_selesai = time.time()
        folder         = FOLDER_LOGS if g.uji else FOLDER_LATIHAN
        isi            = g.ke_log(self.pemain, self.ai_live, self.t_selesai - self.t_mulai)
        self.log_path  = simpan_log(isi, folder, f'{self.pemain}_{g.case["seed"]}')

    # MARK: - Kepala halaman

    def giliran_aktif(self):
        return self.game.giliran_tim()

    def judul(self):
        g     = self.game
        judul = f'Kasus {g.case["seed"]}' if g.uji else f'Latihan {g.case["seed"] - KASUS_PLAYTEST}'
        return f'Rumah Terkunci · {judul}'

    def cerita_kasus(self):
        case = self.game.case
        return (f'**Tuan Hartono ditemukan tewas di rumahnya.** Jasadnya ditemukan pagi ini di **{rn(case["found"])}**, '
                f'dengan perkiraan waktu kematian pukul {WAKTU_KEMATIAN}. Polisi langsung menganggap '
                f'{rn(case["found"]).lower()} sebagai TKP dan menangkap **{sn(case["arrested"])}**, padahal berkasnya '
                f'hanya berisi motif dan gosip. Sidang dimulai setelah ronde {MAX_ROUNDS}. '
                'Temukan pelaku, senjata, dan TKP yang sebenarnya sebelum Detektif AI.')

    def metrik(self, d_aktif):
        """(label, nilai) untuk empat metrik di atas peta."""
        g = self.game
        return [('Ronde', f'{g.ronde}/{MAX_ROUNDS}'),
                ('Giliran', self._teks_giliran(d_aktif)),
                ('Lawan', 'Dirahasiakan' if g.uji and not g.hasil else self.ai_live),
                ('Mode', 'Test mode' if g.uji else 'Normal')]

    # MARK: - Peta

    def sel_peta(self, ai_pos=None, aktif=None):
        """Isi setiap kotak peta, urut baris lalu kolom: nama, pion, tanda, orang, dan apakah aktif."""
        g      = self.game
        ai_pos = ai_pos or g.ai_pos
        return [dict(nama=rn(room), pion=self._pion(room, ai_pos), tag=self._tag_ruangan(room),
                     orang=self._orang_di_ruangan(room), aktif=bool(aktif) and g.tim_pos[aktif] == room)
                for room in sorted(R_IDS, key=lambda r: POS[r])]

    def status_bawah_peta(self):
        return f'Teleport: {self._status_teleport()} · Polisi menangkap {sn(self.game.case["arrested"])}'

    def buka_gerak_ai(self):
        """Riwayat gerak AI dibuka otomatis di mode normal, ditutup di test mode."""
        return not self.game.uji

    def teks_gerak_ai(self):
        baris = [teks for r, siapa, jenis, data in self.game.events if siapa == 'ai'
                 for teks in [self._teks_gerak_ai(r, jenis, data)] if teks]
        return '\n'.join(baris) if baris else 'Belum bergerak.'

    # MARK: - Panel aksi dan tuduhan

    def judul_panel_aksi(self, d):
        return f'**Detektif {d}** di **{rn(self.game.tim_pos[d])}**'

    def tombol_aksi(self, d):
        """[(keterangan, [tombol, ...]), ...]. Setiap tombol: dict(label, key, aksi, disabled, help, primary)."""
        legal = self.game.aksi_legal(d)
        return [('Pindah', self._tombol_pindah(d, legal)),
                ('Teleport (serong 1–2 kotak, sekali pakai)', self._tombol_teleport(d, legal)),
                ('Geledah dan interogasi', self._tombol_geledah(d, legal) + self._tombol_interogasi(d, legal))]

    def pilihan_tuduhan(self):
        """(label, pilihan, format, key) untuk tiga kotak pilihan tuduhan."""
        return [('Pelaku', S_IDS, sn, 'tuduh_s'), ('Senjata', W_IDS, wn, 'tuduh_w'), ('TKP', TKP, rn, 'tuduh_r')]

    def sidang_dibuka(self):
        return self.game.sidang_dibuka

    def selesai(self):
        return bool(self.game.hasil)

    # MARK: - Catatan petunjuk

    def daftar_berkas(self):
        return [f'- {c["text"]}' for c in self.game.case['clues'] if c['kind'] == 'berkas']

    def daftar_temuan_tim(self):
        g = self.game
        return [f'- R{r} · D{data["d"]}: {teks_bukti(g.case, i)}' for r, siapa, jenis, data in g.events
                if siapa == 'tim' and jenis == 'aksi' for i in data['found']]

    def daftar_terdengar(self):
        return [f'- R{r}: AI {data["jenis"]} {target_menguping(data)} → topik {", ".join(data["topik"])}'
                for r, siapa, jenis, data in self.game.events if siapa == 'tim' and jenis == 'menguping']

    # MARK: - Layar selesai

    def ringkasan_hasil(self):
        """Semua teks layar selesai: tuduhan tersembunyi AI (test mode), hasil, tuduhan tim, jawaban, durasi."""
        g = self.game
        jenis, teks = HASIL_TEKS[g.hasil_akhir()['tipe']]
        menit, detik = divmod(int(self.t_selesai - self.t_mulai), 60)
        return dict(
            uji=g.uji,
            tuduhan_tim_teks=TUDUHAN_TIM_TEKS.get(g.hasil['tipe']),
            tuduhan_ai=self._teks_tuduhan_tersembunyi_ai(),
            jenis=jenis,
            teks=f'Hasil melawan AI: {teks}' if g.uji else teks,
            tuduhan_tim=(f'Tuduhan tim: **{teks_jawaban(g.hasil["tebakan"])}** di ronde {g.hasil["ronde"]}'
                         if g.hasil['tebakan'] else None),
            jawaban=f'Jawaban sebenarnya: **{teks_jawaban(g.case["sol"])}**',
            durasi=f'Durasi {menit} menit {detik} detik · log tersimpan di {os.path.relpath(self.log_path)}',
        )

    def trace(self):
        """Reasoning trace Detektif AI: dari agen kalau ada, selain itu disusun dari event."""
        trace = self.game.ai.trace_teks() or self._trace_dari_event()
        return '\n'.join(trace) or 'AI tidak mengamati bukti apa pun.'

    # MARK: - Private · Pesan dan animasi

    def _pesan_aksi(self, d, act, found, tp_sebelum):
        g    = self.game
        teks = f'Detektif {d} {teks_aksi(act)}.'
        if act[0] in ('geledah', 'interogasi'):
            teks += ' Bukti baru: ' + ('; '.join(teks_bukti(g.case, i) for i in found) if found else 'tidak ada.')
        if tp_sebelum is None and g.tp_holder == ('tim', d):
            teks += f' Detektif {d} menemukan teleport!'
        return teks

    def _bingkai_animasi(self, langkah):
        if not langkah:
            return [(None, 'Detektif AI tidak bergerak di ronde ini.')]
        bingkai, pos = [], langkah[0][0]
        for i, (_, act) in enumerate(langkah, 1):
            if act[0] in ('pindah', 'teleport'):
                pos = act[1]
            bingkai.append((pos, f'Giliran Detektif AI, aksi {i}/{len(langkah)}: {teks_aksi(act)}'))
        return bingkai

    def _teks_giliran(self, d_aktif):
        g = self.game
        if g.hasil:
            return 'Selesai'
        if g.sidang_dibuka:
            return 'Sidang'
        return f'Detektif {d_aktif}' if d_aktif else 'Detektif AI'

    # MARK: - Private · Peta

    def _pion(self, room, ai_pos):
        g    = self.game
        pion = [(f'D{d}', WARNA_D[d]) for d in (1, 2, 3) if g.tim_pos[d] == room]
        if ai_pos == room:
            pion.append(('AI', WARNA_AI))
        return pion

    def _tag_ruangan(self, room):
        g = self.game
        tanda = [(room == START, 'sudah diperiksa polisi'), (room in g.tim_searched, 'digeledah tim'),
                 (room in g.ai_searched, 'digeledah AI'), (room == g.case['found'], 'jasad ditemukan')]
        return [teks for ada, teks in tanda if ada]

    def _orang_di_ruangan(self, room):
        case = self.game.case
        return [sn(s) + (' (ditangkap)' if s == case['arrested'] else '') for s in S_IDS if case['loc'][s] == room]

    def _status_teleport(self):
        h = self.game.tp_holder
        if h is None:
            return 'belum ditemukan (tersembunyi di salah satu ruangan berisi bukti)'
        if h == 'terpakai':
            return 'sudah dipakai'
        if h == 'ai':
            return 'dipegang Detektif AI'
        return f'dipegang Detektif {h[1]}'

    def _teks_gerak_ai(self, r, jenis, data):
        if jenis == 'aksi':
            return f'- R{r}: {teks_aksi(data["act"])}'
        if jenis == 'menguping':
            return f'- R{r}: AI menguping tim ({data["jenis"]} {target_menguping(data)})'
        if jenis == 'teleport':
            return f'- R{r}: AI menemukan teleport'
        return None

    # MARK: - Private · Tombol aksi

    def _tombol_pindah(self, d, legal):
        r = self.game.ronde
        return [self._tombol(f'Pindah ke {rn(act[1])}', f'p-{r}-{d}-{act[1]}', act)
                for act in legal if act[0] == 'pindah']

    def _tombol_teleport(self, d, legal):
        r = self.game.ronde
        tele = [self._tombol(f'Teleport ke {rn(act[1])}', f't-{r}-{d}-{act[1]}', act)
                for act in legal if act[0] == 'teleport']
        if tele:
            return tele
        return [self._tombol('Teleport', f't-{r}-{d}', None, help='Detektif ini tidak memegang teleport.')]

    def _tombol_geledah(self, d, legal):
        g = self.game
        pos, key = g.tim_pos[d], f'g-{g.ronde}-{d}'
        gel = [a for a in legal if a[0] == 'geledah']
        if gel:
            return [self._tombol(f'Geledah {rn(pos)}', key, gel[0], primary=True)]
        if pos == START:
            return [self._tombol('Sudah diperiksa polisi', key, None)]
        return [self._tombol('Geledah', key, None, help='Ruangan ini sudah digeledah tim.')]

    def _tombol_interogasi(self, d, legal):
        r = self.game.ronde
        tanya = [self._tombol(f'Interogasi {sn(act[1])}', f'i-{r}-{d}-{act[1]}', act, primary=True)
                 for act in legal if act[0] == 'interogasi']
        if tanya:
            return tanya
        return [self._tombol('Interogasi', f'i-{r}-{d}', None,
                             help='Tidak ada tersangka yang belum ditanya di ruangan ini.')]

    def _tombol(self, label, key, aksi, help=None, primary=False):
        """Satu tombol. aksi None berarti tombol nonaktif."""
        return dict(label=label, key=key, aksi=aksi, disabled=aksi is None, help=help, primary=primary)

    # MARK: - Private · Layar selesai dan trace

    def _teks_tuduhan_tersembunyi_ai(self):
        """Test mode: tuduhan AI yang disembunyikan baru dibuka di layar selesai."""
        t = self.game.tuduhan_ai
        if t:
            return (f'Detektif AI ({self.ai_live}) diam-diam sudah menuduh di ronde {t["ronde"]}: '
                    f'**{teks_jawaban(t["tebakan"])}**')
        return f'Detektif AI ({self.ai_live}) belum menemukan jawaban sampai sidang.'

    def _trace_dari_event(self):
        """Reasoning trace dari event permainan, untuk Detektif AI yang tidak punya trace_teks() sendiri."""
        g     = self.game
        lines = []
        for r, siapa, jenis, data in g.events:
            if siapa == 'ai' and jenis == 'aksi':
                lines.append(self._trace_aksi(r, data))
            elif siapa == 'ai' and jenis == 'amati':
                lines += [line for e in data for line in self._trace_amati(r, e)]
        return lines + self._trace_bukti_tuduhan()

    def _trace_aksi(self, r, data):
        rencana = data['info'].get('rencana')
        return f'R{r} AKSI {teks_aksi(data["act"])}' + (f'   rencana: {" -> ".join(rencana)}' if rencana else '')

    def _trace_amati(self, r, e):
        lines = [f'R{r} BUKTI {teks_bukti(self.game.case, e["id"])}']
        if 'fol' not in e:
            return lines + [f'     model {e["sebelum"]} -> {e["sesudah"]}']
        lines.append(f'     TELL {"; ".join(e["fol"])}')
        if not e['relevan']:
            lines.append(f'     tidak relevan: {e["alasan"]}')
        baru = ', '.join(fakta(c, v, s) for (c, v), s in e['baru']) or 'belum ada kesimpulan baru'
        return lines + [f'     ASK  {e["query"]} query, {e["langkah"]} langkah resolusi -> {baru}']

    def _trace_bukti_tuduhan(self):
        ai = self.game.ai
        if not getattr(ai, 'terbukti', None):
            return []
        lines = ['', f'Terbukti({teks_jawaban(ai.terbukti)}). Bukti resolusi untuk pelaku: KB ∧ ¬Pelaku(x) ⊢ □']
        for i, (a, b, res) in enumerate(ai.bukti('s', ai.terbukti.s, True), 1):
            lines += [f'{i:>3}. {a}', f'     + {b}', f'     ⇒ {res}']
        return lines
