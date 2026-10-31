"""
permainan_engine.py
Engine — aturan permainan Rumah Terkunci.

Satu ronde:
1. Tim: detektif 1, 2, 3 masing-masing 1 aksi (pindah / geledah / interogasi / teleport).
   Boleh menuduh kapan saja di giliran tim.
   Geledah: semua ruangan yang belum digeledah boleh digeledah, isinya baru diketahui
   setelah digeledah (ruangan kosong tidak memberi bukti). Ruang Tamu sudah diperiksa polisi,
   jadi tidak bisa digeledah. Aturan ini sama untuk tim dan AI.
2. Detektif AI: jumlah aksi sesuai pola level. Menuduh hanya kalau prasyarat terpenuhi.
Setelah ronde 7: sidang. Tim boleh menuduh sekali lagi; kalau tidak, hasilnya seri
(hakim memvonis orang yang ditangkap polisi). Tuduhan pertama yang benar menang, tuduhan
yang salah kalah.

Fitur tambahan (bisa dimatikan, misalnya untuk simulasi tanpa teleport dan menguping):
- denah    : '9', '12', atau '16' ruangan
- teleport : 1 teleport tersembunyi di ruangan berisi bukti; milik pihak pertama yang
             menggeledah ruangan itu; lompat serong 1-2 kotak, 1 aksi, sekali pakai
- menguping: kalau geledah/interogasi dilakukan di ruangan yang ditempati pion lawan,
             lawan hanya mendengar TOPIK bukti (tersangka/senjata/ruangan/jasad)
- uji      : test mode. Tuduhan AI disembunyikan dan tidak mengakhiri permainan; game
             lanjut sampai tim menuduh atau sidang setelah ronde 7.

Dua cara menjalankan:
- jalan()  : seluruh permainan sekaligus, tim berupa objek Tim (TimBot, TimRekaman).
- per langkah untuk UI: mulai(), lalu aksi_tim(d, aksi) tiga kali, giliran_ai(),
  ulangi sampai sidang. tuduh_tim(jawaban) boleh kapan saja di giliran tim atau saat sidang.
Keduanya memakai giliran AI yang sama (_jalankan_giliran_ai), jadi hasilnya selalu sama.
"""
import random
from collections import Counter

from models.permainan_model import JUMLAH_DETEKTIF, LEVELS
from models.rumah_model import MAX_ROUNDS, S_IDS, START, World
from services.denah_service import pakai_denah, serong
from services.kasus_service import generate_case, lengkapi
from services.rumah_service import neighbors

# MARK: - Permainan

class Permainan:
    def __init__(self, seed, ai, tim=None, *, level='normal', denah='9', teleport=False, menguping=False,
                 pola=None, uji=False):
        pakai_denah(denah)
        self.case          = lengkapi(generate_case(seed))
        self.ai            = ai
        self.tim           = tim
        self.level         = level
        self.pola          = pola or LEVELS[level]
        self.teleport      = teleport
        self.menguping     = menguping
        self.uji           = uji
        self.aksi_ronde    = 0          # aksi tim yang sudah dipakai di ronde ini (mode per langkah)
        self.sidang_dibuka = False
        self.ai_selesai    = False      # test mode: AI sudah menuduh diam-diam, tapi tetap bergerak
        self.tuduhan_ai    = None       # test mode: tuduhan AI yang disembunyikan
        self.ronde         = 1
        self.hasil         = None
        self.events        = []         # (ronde, pelaku, jenis, data)
        self.stat          = Counter()  # menguping, teleport
        self.ai_pos        = START
        self.ai_searched   = set()
        self.ai_asked      = set()
        self.ai_aksi       = 0
        self.tim_pos       = {d: START for d in range(1, JUMLAH_DETEKTIF + 1)}
        self.tim_searched  = set()
        self.tim_asked     = set()
        self.tim_aksi_n    = 0
        self.tp_room       = self.case['teleport'] if teleport else None
        self.tp_holder     = None       # None | ('tim', d) | 'ai' | 'terpakai'

    # MARK: - Seluruh permainan sekaligus

    def jalan(self):
        self.mulai()
        for ronde in range(1, MAX_ROUNDS + 1):
            self.ronde = ronde
            if self.tim:
                self.tim.giliran(self)
                if self.hasil:
                    return self.hasil
            self._jalankan_giliran_ai()
            if self.hasil:
                return self.hasil
        return self._sidang()

    # MARK: - Per langkah (UI)

    def mulai(self):
        """Awal permainan: AI dan tim membaca berkas polisi. Mengembalikan id berkas."""
        dossier = [c['id'] for c in self.case['clues'] if c['kind'] == 'berkas']
        self.ai.mulai(self.case)
        self.log('ai', 'amati', self.ai.amati(dossier, 1))
        if self.tim:
            self.tim.mulai(self.case)
            self.tim.amati(dossier)
        self.ronde, self.aksi_ronde = 1, 0
        return dossier

    def giliran_tim(self):
        """Detektif yang sedang jalan (1, 2, 3), atau None kalau giliran tim sudah habis."""
        if self.hasil or self.sidang_dibuka or self.aksi_ronde >= JUMLAH_DETEKTIF:
            return None
        return self.aksi_ronde + 1

    def aksi_legal(self, d):
        """Semua aksi yang boleh dilakukan detektif d dari posisinya sekarang."""
        pos  = self.tim_pos[d]
        acts = [('pindah', nb) for nb in neighbors(pos)]
        if self.tp_holder == ('tim', d):
            acts += [('teleport', x) for x in serong(pos)]
        if pos != START and pos not in self.tim_searched:      # Ruang Tamu sudah diperiksa polisi
            acts.append(('geledah', pos))
        acts += [('interogasi', s) for s in S_IDS if self.case['loc'][s] == pos and s not in self.tim_asked]
        return acts

    def aksi_tim(self, d, aksi):
        """Satu aksi detektif d. Detektif jalan berurutan 1, 2, 3. Mengembalikan id bukti yang ditemukan."""
        assert d == self.giliran_tim(), f'bukan giliran detektif {d}'
        found = self.tim_aksi(d, tuple(aksi))
        self.aksi_ronde += 1
        return found

    def giliran_ai(self):
        """Giliran Detektif AI setelah 3 aksi tim, lalu pindah ke ronde berikutnya atau sidang.
        Mengembalikan daftar (posisi AI sebelum aksi, aksi) untuk ditampilkan UI."""
        assert not self.hasil and not self.sidang_dibuka
        langkah = self._jalankan_giliran_ai()
        if not self.hasil:
            self._lanjut_ronde()
        return langkah

    def tuduh_tim(self, jawaban):
        """Tuduhan tim: (pelaku, senjata, TKP). Saat sidang, None berarti tim tidak menuduh
        dan hakim memvonis orang yang ditangkap polisi."""
        assert not self.hasil
        if jawaban is None:
            assert self.sidang_dibuka, 'tim hanya boleh tidak menuduh saat sidang'
            self._vonis_hakim()
        else:
            self.tuduh('tim', World(*jawaban))
        return self.hasil

    # MARK: - Aksi dan tuduhan (dipakai tim bot dan rekaman)

    def tim_aksi(self, d, act):
        """Jalankan satu aksi detektif d tanpa cek giliran. Mengembalikan id bukti yang ditemukan."""
        jenis, target = act
        found = getattr(self, f'_tim_{jenis}')(d, target)
        self.tim_aksi_n += 1
        self.log('tim', 'aksi', dict(d=d, act=act, found=found))
        return found

    def tuduh(self, siapa, guess):
        benar      = guess == self.case['sol']
        tipe       = {'tim': 'tim' if benar else 'tim-salah', 'ai': 'ai' if benar else 'ai-salah'}[siapa]
        self.hasil = dict(tipe=tipe, tebakan=guess, ronde=self.ronde)
        self.log(siapa, 'tuduh', dict(guess=guess, benar=benar))

    # MARK: - Hasil dan log

    def hasil_akhir(self):
        """Hasil melawan AI. Mode normal: sama dengan self.hasil. Test mode: hasil kalau tuduhan AI
        tidak disembunyikan, yaitu siapa yang menuduh lebih dulu; sama dengan replay melawan AI yang sama.
        Tim jalan lebih dulu di setiap ronde, dan sidang terjadi setelah giliran AI di ronde 7."""
        t = self.tuduhan_ai
        if not self.uji or not self.hasil or not t:
            return self.hasil
        ronde_tim = MAX_ROUNDS + 1 if self.sidang_dibuka else self.hasil['ronde']
        if t['ronde'] < ronde_tim:
            return dict(tipe='ai' if t['benar'] else 'ai-salah', tebakan=t['tebakan'], ronde=t['ronde'])
        return self.hasil

    def ke_log(self, pemain, ai_live, durasi_detik):
        """Isi file log JSON untuk replay. Field yang dibaca replay dan evaluasi: seed, pemain,
        ai_live, mode, aksi_tim, tuduhan_tim, hasil."""
        return dict(seed=self.case['seed'], pemain=pemain, ai_live=ai_live, durasi_detik=round(durasi_detik),
                    mode='uji' if self.uji else 'normal', aturan='proposal',
                    aksi_tim=self._aksi_tim_tercatat(), tuduhan_tim=self._tuduhan_tim_tercatat(),
                    hasil=self.hasil_akhir()['tipe'] if self.hasil else None)

    def log(self, siapa, jenis, data):
        self.events.append((self.ronde, siapa, jenis, data))

    # MARK: - Private · Aksi tim

    def _tim_pindah(self, d, ruang):
        assert ruang in neighbors(self.tim_pos[d])
        self.tim_pos[d] = ruang
        return []

    def _tim_teleport(self, d, ruang):
        assert self.tp_holder == ('tim', d) and ruang in serong(self.tim_pos[d])
        self.tim_pos[d] = ruang
        self.tp_holder = 'terpakai'
        self.stat['tp_dipakai_tim'] += 1
        return []

    def _tim_geledah(self, d, ruang):
        assert ruang == self.tim_pos[d] and ruang != START and ruang not in self.tim_searched
        self.tim_searched.add(ruang)
        return self._geledah('tim', ruang, ('tim', d))

    def _tim_interogasi(self, d, tersangka):
        pos = self.tim_pos[d]
        assert self.case['loc'][tersangka] == pos and tersangka not in self.tim_asked
        self.tim_asked.add(tersangka)
        return self._interogasi('tim', tersangka, pos)

    # MARK: - Private · Geledah, interogasi, teleport, dan menguping (sama untuk tim dan AI)

    def _geledah(self, pelaku, ruang, pemilik_teleport):
        ids = list(self.case['room_clues'][ruang])
        self._ambil_teleport(ruang, pemilik_teleport)
        self._kuping(pelaku, 'geledah', ruang, ruang, ids)
        return ids

    def _interogasi(self, pelaku, tersangka, ruang):
        ids = [self.case['testimony_of'][tersangka]]
        self._kuping(pelaku, 'interogasi', tersangka, ruang, ids)
        return ids

    def _ambil_teleport(self, room, pemilik):
        if self.tp_room == room and self.tp_holder is None:
            self.tp_holder = pemilik
            self.tp_room   = None
            siapa          = 'tim' if pemilik != 'ai' else 'ai'
            self.stat[f'tp_ditemukan_{siapa}'] += 1
            self.stat['tp_ronde_ditemukan'] = self.ronde
            self.log(siapa, 'teleport', dict(room=room))

    def _kuping(self, pelaku, jenis, target, room, ids):
        """Lawan yang berada di ruangan yang sama mendengar topik bukti, bukan isinya."""
        if not self.menguping:
            return
        topik = [self.case['by_id'][i]['topik'] for i in ids]
        data  = dict(jenis=jenis, target=target, topik=topik)
        if pelaku == 'tim' and self.ai_pos == room:
            self.ai.dengar(jenis, target, topik)
            self.stat['ai_menguping'] += 1
            self.log('ai', 'menguping', data)
        elif pelaku == 'ai' and self.tim and room in self.tim_pos.values():
            self.tim.dengar(jenis, target, topik)
            self.stat['tim_menguping'] += 1
            self.log('tim', 'menguping', data)

    # MARK: - Private · Giliran AI (dipakai jalan() dan giliran_ai())

    def _jalankan_giliran_ai(self):
        """Semua aksi AI di ronde ini. Mengembalikan daftar (posisi AI sebelum aksi, aksi)."""
        langkah = []
        for i in range(self._jatah_aksi_ai()):
            if self._ai_menuduh_dan_berhenti():
                break
            act, info = self._aksi_ai_berikutnya(i)
            if act is None:
                break
            langkah.append((self.ai_pos, act))
            self._ai_jalankan(act, info)
        if not self.hasil and not self.ai_selesai:
            self._ai_coba_tuduh()
        return langkah

    def _jatah_aksi_ai(self):
        return self.pola[(self.ronde - 1) % len(self.pola)]

    def _ai_menuduh_dan_berhenti(self):
        """Mode normal: tuduhan AI mengakhiri game. Test mode: tuduhan disimpan diam-diam dan AI
        tetap memakai semua aksinya, supaya pemain tidak bisa menebak bahwa AI sudah menuduh."""
        return not self.ai_selesai and self._ai_coba_tuduh() and not self.uji

    def _aksi_ai_berikutnya(self, i):
        act, info = self.ai.aksi(self.ai_pos, self.ai_searched, self.ai_asked, punya_tp=self.tp_holder == 'ai')
        if act is not None:
            return act, info
        if not self.ai_selesai:
            self.log('ai', 'tunggu', {})
            return None, {}
        return self._langkah_acak(i), {}

    def _langkah_acak(self, i):
        """Test mode setelah tuduhan tersembunyi: AI yang kehabisan target tetap bergerak.
        Seed tetap per kasus, ronde, dan urutan aksi, jadi game yang sama selalu sama."""
        rng = random.Random(self.case['seed'] * 100 + self.ronde * 10 + i)
        return 'pindah', rng.choice(neighbors(self.ai_pos))

    def _ai_coba_tuduh(self):
        jawaban = self.ai.tuduhan()
        if not jawaban:
            return False
        if self.uji:
            self._simpan_tuduhan_tersembunyi(jawaban)
        else:
            self.tuduh('ai', jawaban)
        return True

    def _simpan_tuduhan_tersembunyi(self, jawaban):
        """Test mode: tuduhan pertama disimpan diam-diam, tim dan AI tetap lanjut bermain."""
        if not self.tuduhan_ai:
            benar           = jawaban == self.case['sol']
            self.tuduhan_ai = dict(tebakan=jawaban, ronde=self.ronde, benar=benar)
            self.log('ai', 'tuduh-tersembunyi', dict(guess=jawaban, benar=benar))
        self.ai_selesai = True

    def _ai_jalankan(self, act, info):
        jenis, target = act
        self.ai_aksi += 1
        self.log('ai', 'aksi', dict(act=act, info=info))
        ids = getattr(self, f'_ai_{jenis}')(target)
        if ids is not None:
            self.log('ai', 'amati', self.ai.amati(ids, self.ronde))

    def _ai_pindah(self, ruang):
        assert ruang in neighbors(self.ai_pos)
        self.ai_pos = ruang

    def _ai_teleport(self, ruang):
        assert self.tp_holder == 'ai' and ruang in serong(self.ai_pos)
        self.ai_pos    = ruang
        self.tp_holder = 'terpakai'
        self.stat['tp_dipakai_ai'] += 1

    def _ai_geledah(self, ruang):
        assert ruang == self.ai_pos and ruang != START and ruang not in self.ai_searched
        self.ai_searched.add(ruang)
        return self._geledah('ai', ruang, 'ai')

    def _ai_interogasi(self, tersangka):
        self.ai_asked.add(tersangka)
        return self._interogasi('ai', tersangka, self.ai_pos)

    # MARK: - Private · Ronde dan sidang

    def _lanjut_ronde(self):
        if self.ronde < MAX_ROUNDS:
            self.ronde += 1
            self.aksi_ronde = 0
        else:
            self.sidang_dibuka = True

    def _sidang(self):
        self.ronde = MAX_ROUNDS
        jawaban    = self.tim.sidang() if self.tim else None
        if jawaban:
            self.tuduh('tim', jawaban)
        else:
            self._vonis_hakim()
        return self.hasil

    def _vonis_hakim(self):
        """Tidak ada yang menuduh sampai sidang: hakim memvonis orang yang ditangkap polisi (seri)."""
        self.hasil = dict(tipe='vonis', tebakan=None, ronde=MAX_ROUNDS)
        self.log('hakim', 'vonis', dict(arrested=self.case['arrested']))

    # MARK: - Private · Log

    def _aksi_tim_tercatat(self):
        return [[r, data['d'], list(data['act'])] for r, siapa, jenis, data in self.events
                if siapa == 'tim' and jenis == 'aksi']

    def _tuduhan_tim_tercatat(self):
        return next((dict(ronde=r, jawaban=list(data['guess']), sidang=self.sidang_dibuka)
                     for r, siapa, jenis, data in self.events if siapa == 'tim' and jenis == 'tuduh'), None)
