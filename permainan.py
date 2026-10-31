"""
Aturan permainan Rumah Terkunci untuk simulasi.

Satu ronde:
1. Tim: detektif 1, 2, 3 masing-masing 1 aksi (pindah / geledah / interogasi / teleport).
   Boleh menuduh kapan saja di giliran tim.
   Geledah: semua ruangan yang belum digeledah boleh digeledah, isinya baru diketahui
   setelah digeledah (ruangan kosong tidak memberi bukti). Ruang Tamu sudah diperiksa polisi,
   jadi tidak bisa digeledah. Aturan ini sama untuk tim dan AI.
2. Detektif AI: jumlah aksi sesuai pola level. Menuduh hanya kalau prasyarat terpenuhi.
Setelah ronde 7: sidang. Tim boleh menuduh sekali lagi; kalau tidak, hasilnya seri
(hakim memvonis orang yang ditangkap polisi).

Fitur tambahan (bisa dimatikan supaya aturan lama tetap bisa diuji):
- denah    : '9', '12', atau '16' ruangan
- teleport : 1 teleport tersembunyi di ruangan berisi bukti; milik pihak pertama yang
             menggeledah ruangan itu; lompat serong 1-2 kotak, 1 aksi, sekali pakai
- menguping: kalau geledah/interogasi dilakukan di ruangan yang ditempati pion lawan,
             lawan hanya mendengar TOPIK bukti (tersangka/senjata/ruangan/jasad)
- uji      : test mode. Tuduhan AI disembunyikan dan tidak mengakhiri permainan; game
             lanjut sampai tim menuduh atau sidang setelah ronde 7.

Dua cara menjalankan:
- jalan()  : seluruh permainan sekaligus, tim berupa objek agen (TimBot, TimRekaman).
- per langkah untuk UI: mulai(), lalu aksi_tim(d, aksi) tiga kali, giliran_ai(),
  ulangi sampai sidang. tuduh_tim(jawaban) boleh kapan saja di giliran tim atau saat sidang.
"""
import random
from collections import Counter
from kasus import generate_case, START, MAX_ROUNDS, S_IDS, World, neighbors, sn, wn, rn
from denah import pakai_denah, lengkapi, serong

LEVELS = {'mudah': [2], 'normal': [2, 2, 3], 'sulit': [2, 3], 'ahli': [3]}
LEVELS_LAMA = {'mudah': [2], 'normal': [3, 2], 'sulit': [3]}


def teks_aksi(act):
    kind, arg = act
    if kind == 'pindah':
        return f'pindah ke {rn(arg)}'
    if kind == 'teleport':
        return f'teleport ke {rn(arg)}'
    if kind == 'geledah':
        return f'menggeledah {rn(arg)}'
    return f'menginterogasi {sn(arg)}'


def teks_jawaban(m):
    return f'{sn(m.s)} · {wn(m.w)} · {rn(m.r)}'


class Permainan:
    def __init__(self, seed, ai, tim=None, level='normal', denah='9', teleport=False, menguping=False,
                 pola=None, uji=False):
        pakai_denah(denah)
        self.case = lengkapi(generate_case(seed))
        self.ai, self.tim, self.level = ai, tim, level
        self.pola = pola or LEVELS[level]
        self.teleport, self.menguping = teleport, menguping
        self.uji = uji
        self.aksi_ronde = 0       # aksi tim yang sudah dipakai di ronde ini (mode per langkah)
        self.sidang_dibuka = False
        self.ai_selesai = False   # test mode: AI sudah menuduh diam-diam, tapi tetap bergerak
        self.tuduhan_ai = None    # test mode: tuduhan AI yang disembunyikan
        self.ronde = 1
        self.hasil = None
        self.events = []          # (ronde, pelaku, jenis, data)
        self.stat = Counter()     # menguping, teleport
        self.ai_pos = START
        self.ai_searched, self.ai_asked = set(), set()
        self.ai_aksi = 0
        self.tim_pos = {1: START, 2: START, 3: START}
        self.tim_searched, self.tim_asked = set(), set()
        self.tim_aksi_n = 0
        self.tp_room = self.case['teleport'] if teleport else None
        self.tp_holder = None     # None | ('tim', d) | 'ai' | 'terpakai'

    def log(self, siapa, jenis, data):
        self.events.append((self.ronde, siapa, jenis, data))

    # ---------- teleport dan menguping ----------
    def _ambil_teleport(self, room, pemilik):
        if self.tp_room == room and self.tp_holder is None:
            self.tp_holder = pemilik
            self.tp_room = None
            siapa = 'tim' if pemilik != 'ai' else 'ai'
            self.stat[f'tp_ditemukan_{siapa}'] += 1
            self.stat['tp_ronde_ditemukan'] = self.ronde
            self.log(siapa, 'teleport', dict(room=room))

    def _kuping(self, pelaku, jenis, target, room, ids):
        if not self.menguping:
            return
        topik = [self.case['by_id'][i]['topik'] for i in ids]
        if pelaku == 'tim' and self.ai_pos == room:
            self.ai.dengar(jenis, target, topik)
            self.stat['ai_menguping'] += 1
            self.log('ai', 'menguping', dict(jenis=jenis, target=target, topik=topik))
        elif pelaku == 'ai' and self.tim and room in self.tim_pos.values():
            self.tim.dengar(jenis, target, topik)
            self.stat['tim_menguping'] += 1
            self.log('tim', 'menguping', dict(jenis=jenis, target=target, topik=topik))

    # ---------- aksi tim ----------
    def tim_aksi(self, d, act):
        kind, arg = act
        pos = self.tim_pos[d]
        found = []
        if kind == 'pindah':
            assert arg in neighbors(pos)
            self.tim_pos[d] = arg
        elif kind == 'teleport':
            assert self.tp_holder == ('tim', d) and arg in serong(pos)
            self.tim_pos[d] = arg
            self.tp_holder = 'terpakai'
            self.stat['tp_dipakai_tim'] += 1
        elif kind == 'geledah':
            assert arg == pos and arg != START and arg not in self.tim_searched
            self.tim_searched.add(arg)
            found = list(self.case['room_clues'][arg])
            self._ambil_teleport(arg, ('tim', d))
            self._kuping('tim', 'geledah', arg, pos, found)
        else:
            assert self.case['loc'][arg] == pos and arg not in self.tim_asked
            self.tim_asked.add(arg)
            found = [self.case['testimony_of'][arg]]
            self._kuping('tim', 'interogasi', arg, pos, found)
        self.tim_aksi_n += 1
        self.log('tim', 'aksi', dict(d=d, act=act, found=found))
        return found

    def tuduh(self, siapa, guess):
        sol = self.case['sol']
        benar = guess == sol
        tipe = {'tim': 'tim' if benar else 'tim-salah', 'ai': 'ai' if benar else 'ai-salah'}[siapa]
        self.hasil = dict(tipe=tipe, tebakan=guess, ronde=self.ronde)
        self.log(siapa, 'tuduh', dict(guess=guess, benar=benar))

    # ---------- jalannya permainan ----------
    def jalan(self):
        case = self.case
        dossier = [c['id'] for c in case['clues'] if c['kind'] == 'berkas']
        self.ai.mulai(case)
        self.log('ai', 'amati', self.ai.amati(dossier, 1))
        if self.tim:
            self.tim.mulai(case)
            self.tim.amati(dossier)
        pattern = self.pola
        for ronde in range(1, MAX_ROUNDS + 1):
            self.ronde = ronde
            if self.tim:
                self.tim.giliran(self)
                if self.hasil:
                    return self.hasil
            for _ in range(pattern[(ronde - 1) % len(pattern)]):
                if self._ai_coba_tuduh():
                    return self.hasil
                act, info = self.ai.aksi(self.ai_pos, self.ai_searched, self.ai_asked,
                                         punya_tp=self.tp_holder == 'ai')
                if act is None:
                    self.log('ai', 'tunggu', {})
                    break
                self._ai_jalankan(act, info, ronde)
            if self._ai_coba_tuduh():
                return self.hasil
        # sidang
        self.ronde = MAX_ROUNDS
        if self.tim:
            g = self.tim.sidang()
            if g:
                self.tuduh('tim', g)
                return self.hasil
        self.hasil = dict(tipe='vonis', tebakan=None, ronde=MAX_ROUNDS)
        self.log('hakim', 'vonis', dict(arrested=case['arrested']))
        return self.hasil

    # ---------- jalannya permainan per langkah (untuk UI) ----------
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
        if self.hasil or self.sidang_dibuka or self.aksi_ronde >= 3:
            return None
        return self.aksi_ronde + 1

    def aksi_legal(self, d):
        """Semua aksi yang boleh dilakukan detektif d dari posisinya sekarang."""
        pos = self.tim_pos[d]
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
        langkah = []
        for i in range(self.pola[(self.ronde - 1) % len(self.pola)]):
            # Test mode: AI tetap memakai semua aksinya setelah menuduh, supaya pemain tidak bisa menebak.
            if not self.ai_selesai and self._ai_coba_tuduh() and not self.uji:
                break
            act, info = self.ai.aksi(self.ai_pos, self.ai_searched, self.ai_asked,
                                     punya_tp=self.tp_holder == 'ai')
            if act is None:
                if not self.ai_selesai:
                    self.log('ai', 'tunggu', {})
                    break
                rng = random.Random(self.case['seed'] * 100 + self.ronde * 10 + i)
                act, info = ('pindah', rng.choice(neighbors(self.ai_pos))), {}
            langkah.append((self.ai_pos, act))
            self._ai_jalankan(act, info, self.ronde)
        if not self.hasil and not self.ai_selesai:
            self._ai_coba_tuduh()
        if not self.hasil:
            if self.ronde < MAX_ROUNDS:
                self.ronde += 1
                self.aksi_ronde = 0
            else:
                self.sidang_dibuka = True
        return langkah

    def tuduh_tim(self, jawaban):
        """Tuduhan tim: (pelaku, senjata, TKP). Saat sidang, None berarti tim tidak menuduh
        dan hakim memvonis orang yang ditangkap polisi."""
        assert not self.hasil
        if jawaban is None:
            assert self.sidang_dibuka, 'tim hanya boleh tidak menuduh saat sidang'
            self.hasil = dict(tipe='vonis', tebakan=None, ronde=MAX_ROUNDS)
            self.log('hakim', 'vonis', dict(arrested=self.case['arrested']))
        else:
            self.tuduh('tim', World(*jawaban))
        return self.hasil

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
        """Isi file log JSON untuk replay (format hasil rapat, ditambah mode, aturan, sidang)."""
        tuduhan = next((dict(ronde=r, jawaban=list(data['guess']), sidang=self.sidang_dibuka)
                        for r, siapa, jenis, data in self.events if siapa == 'tim' and jenis == 'tuduh'), None)
        return dict(seed=self.case['seed'], pemain=pemain, ai_live=ai_live, durasi_detik=round(durasi_detik),
                    mode='uji' if self.uji else 'normal', aturan='proposal',
                    aksi_tim=[[r, data['d'], list(data['act'])]
                              for r, siapa, jenis, data in self.events if siapa == 'tim' and jenis == 'aksi'],
                    tuduhan_tim=tuduhan, hasil=self.hasil_akhir()['tipe'] if self.hasil else None)

    def _ai_coba_tuduh(self):
        g = self.ai.tuduhan()
        if g:
            if self.uji:
                # Test mode: tuduhan disimpan diam-diam, tim dan AI tetap lanjut bermain.
                if not self.tuduhan_ai:
                    self.tuduhan_ai = dict(tebakan=g, ronde=self.ronde, benar=g == self.case['sol'])
                    self.log('ai', 'tuduh-tersembunyi', dict(guess=g, benar=g == self.case['sol']))
                self.ai_selesai = True
                return True
            self.tuduh('ai', g)
            return True
        return False

    def _ai_jalankan(self, act, info, ronde):
        kind, arg = act
        self.ai_aksi += 1
        self.log('ai', 'aksi', dict(act=act, info=info))
        if kind == 'pindah':
            assert arg in neighbors(self.ai_pos)
            self.ai_pos = arg
            return
        if kind == 'teleport':
            assert self.tp_holder == 'ai' and arg in serong(self.ai_pos)
            self.ai_pos = arg
            self.tp_holder = 'terpakai'
            self.stat['tp_dipakai_ai'] += 1
            return
        if kind == 'geledah':
            assert arg == self.ai_pos and arg != START and arg not in self.ai_searched
            self.ai_searched.add(arg)
            ids = self.case['room_clues'][arg]
            self._ambil_teleport(arg, 'ai')
            self._kuping('ai', 'geledah', arg, self.ai_pos, ids)
        else:
            self.ai_asked.add(arg)
            ids = [self.case['testimony_of'][arg]]
            self._kuping('ai', 'interogasi', arg, self.ai_pos, ids)
        self.log('ai', 'amati', self.ai.amati(ids, ronde))
