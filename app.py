"""
UI Streamlit Rumah Terkunci: tim 3 detektif melawan Detektif AI.

  streamlit run app.py

- Mode normal : aksi AI ditampilkan satu per satu (animasi), tuduhan AI langsung mengakhiri game.
- Test mode   : AI langsung jalan tanpa animasi, tuduhan AI disembunyikan, dan game lanjut
                sampai tim menuduh atau sidang setelah ronde 7.
Setiap game test mode yang selesai disimpan ke logs/<inisial>_<seed>.json untuk replay.
Game mode normal adalah latihan; lognya disimpan ke logs/latihan/ yang tidak masuk git.
"""
import json
import os
import time

import streamlit as st

from antarmuka import Tim
from daftar_ai import LAWAN_AI
from kasus import S_IDS, W_IDS, TKP, R_IDS, POS, START, MAX_ROUNDS, WAKTU_KEMATIAN, sn, wn, rn
from permainan import Permainan
from teks import fakta, target_menguping, teks_aksi, teks_bukti, teks_jawaban

FOLDER_REPO = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(FOLDER_REPO, 'logs')
PATH_PEMBAGIAN = os.path.join(FOLDER_REPO, 'pembagian.json')
PEMAIN = ['GK', 'JC', 'HD']
LATIHAN = 300                # kasus 1–300 untuk playtest; latihan ke-n memakai kasus 300 + n
JUMLAH_LATIHAN = 50
JEDA_ANIMASI = 0.9
WARNA_D = {1: '#2f6fd6', 2: '#1f9d55', 3: '#d9822b'}

HASIL_TEKS = {
    'tim': ('success', 'Tim menang! Tuduhan kalian benar.'),
    'tim-salah': ('error', 'Tuduhan tim salah. Tim kalah.'),
    'ai': ('error', 'Detektif AI menuduh lebih dulu dan benar. AI menang.'),
    'ai-salah': ('success', 'Detektif AI salah tuduh. Tim menang.'),
    'vonis': ('warning', 'Tim tidak menuduh. Hakim memvonis orang yang ditangkap polisi. Hasil seri.'),
}
TUDUHAN_TIM_TEKS = {
    'tim': 'Tuduhan kalian benar.',
    'tim-salah': 'Tuduhan kalian salah.',
    'vonis': 'Kalian tidak menuduh sampai sidang.',
}

CERITA = (f'**Tuan Hartono ditemukan tewas di rumahnya**, dengan perkiraan waktu kematian pukul {WAKTU_KEMATIAN}. '
          'Polisi langsung menganggap ruangan tempat jasad ditemukan sebagai TKP dan menangkap seorang tersangka, '
          f'padahal berkasnya hanya berisi motif dan gosip. Sidang dimulai setelah ronde {MAX_ROUNDS}. '
          'Temukan pelaku, senjata, dan TKP yang sebenarnya sebelum Detektif AI.')
CARA_MAIN = ('**Cara main**\n'
             '1. Tiap ronde, Detektif 1, 2, 3 masing-masing 1 aksi.\n'
             '2. Setelah aksi ketiga, Detektif AI jalan 2–3 aksi.\n'
             '3. Semua ruangan yang belum digeledah boleh digeledah, kecuali Ruang Tamu (sudah diperiksa polisi). '
             'Isinya baru ketahuan setelah digeledah, dan ruangan bisa saja kosong.\n'
             '4. Pelaku selalu bohong; yang tidak bersalah selalu jujur.\n'
             '5. Jasad bisa sudah dipindahkan dari TKP.\n'
             '6. Menuduh boleh kapan saja di giliran tim, tapi hanya sekali.\n'
             f'7. Setelah ronde {MAX_ROUNDS}: sidang. Kalau tim tidak menuduh, hasilnya seri.')

CSS = """
<style>
.peta {display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; max-width: 560px;}
.ruang {border: 1px solid rgba(128,128,128,.45); border-radius: 8px; padding: 8px; min-height: 118px;
        font-size: 0.82rem; line-height: 1.35; background: rgba(128,128,128,.06);}
.ruang.aktif {outline: 3px solid #2f6fd6; outline-offset: -2px;}
.ruang .nama {font-weight: 700; font-size: 0.9rem; margin-bottom: 4px;}
.chip {display: inline-block; color: #fff; border-radius: 10px; padding: 0 7px; margin: 1px 2px 1px 0;
       font-size: 0.75rem; font-weight: 700;}
.tag {display: inline-block; border: 1px solid rgba(128,128,128,.6); border-radius: 6px; padding: 0 5px;
      margin: 1px 2px 1px 0; font-size: 0.72rem;}
.ket {opacity: .75; font-size: 0.75rem;}
</style>
"""


class TimManusia(Tim):
    """Tim untuk Permainan saat dimainkan manusia. Aksi tim datang dari tombol UI; topik yang
    terdengar dari AI dicatat engine sebagai event ('tim', 'menguping')."""
    nama = 'manusia'


# ---------------------------------------------------------------- pembagian kasus dan log
def muat_pembagian():
    """Isi pembagian.json: {inisial: [{no, seed, lawan}, ...]}. Kosong kalau file belum ada."""
    if not os.path.exists(PATH_PEMBAGIAN):
        return {}
    with open(PATH_PEMBAGIAN, encoding='utf-8') as f:
        return json.load(f)


PEMBAGIAN = muat_pembagian()


def jatah_berikutnya(pemain):
    """Game test mode berikutnya dari pembagian.json: entri pertama yang belum punya log."""
    for e in PEMBAGIAN.get(pemain, []):
        if not os.path.exists(os.path.join(LOGS, f'{pemain}_{e["seed"]}.json')):
            return e
    return None


def game_baru(pemain, seed, ai_live, uji):
    ss = st.session_state
    g = Permainan(seed, LAWAN_AI[ai_live](), TimManusia(), teleport=True, menguping=True, uji=uji)
    g.mulai()
    ss.game, ss.ai_live, ss.pemain = g, ai_live, pemain
    ss.t_mulai, ss.t_selesai, ss.log_path = time.time(), None, None
    ss.ai_pending, ss.pesan, ss.catatan = False, None, ''


def simpan_log(g):
    ss = st.session_state
    folder = LOGS if g.uji else os.path.join(LOGS, 'latihan')
    os.makedirs(folder, exist_ok=True)
    path = _path_log_baru(folder, f'{ss.pemain}_{g.case["seed"]}')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(g.ke_log(ss.pemain, ss.ai_live, ss.t_selesai - ss.t_mulai), f, ensure_ascii=False, indent=1)
    return path


def _path_log_baru(folder, nama):
    """Nama file yang belum dipakai, supaya log lama dengan kasus yang sama tidak tertimpa."""
    path, i = os.path.join(folder, nama + '.json'), 2
    while os.path.exists(path):
        path, i = os.path.join(folder, f'{nama}_{i}.json'), i + 1
    return path


# ---------------------------------------------------------------- aksi dari tombol
def klik_aksi(d, act):
    g = st.session_state.game
    if g.giliran_tim() != d or act not in g.aksi_legal(d):
        return                            # klik basi (misalnya tombol ditekan dua kali)
    tp_sebelum = g.tp_holder
    found = g.aksi_tim(d, act)
    st.session_state.pesan = _pesan_aksi(g, d, act, found, tp_sebelum)
    if g.giliran_tim() is None:
        st.session_state.ai_pending = True


def _pesan_aksi(g, d, act, found, tp_sebelum):
    teks = f'Detektif {d} {teks_aksi(act)}.'
    if act[0] in ('geledah', 'interogasi'):
        teks += ' Bukti baru: ' + ('; '.join(teks_bukti(g.case, i) for i in found) if found else 'tidak ada.')
    if tp_sebelum is None and g.tp_holder == ('tim', d):
        teks += f' Detektif {d} menemukan teleport!'
    return teks


def klik_tuduh():
    ss = st.session_state
    g = ss.game
    if g.hasil or (g.giliran_tim() is None and not g.sidang_dibuka):
        return
    g.tuduh_tim((ss.tuduh_s, ss.tuduh_w, ss.tuduh_r))


def klik_serahkan():
    g = st.session_state.game
    if g.sidang_dibuka and not g.hasil:
        g.tuduh_tim(None)


# ---------------------------------------------------------------- peta
def peta_html(g, ai_pos=None, aktif=None):
    ai_pos = ai_pos or g.ai_pos
    sel = []
    for room in sorted(R_IDS, key=lambda r: POS[r]):
        isi = [f'<div class="nama">{rn(room)}</div>'] + _baris_isi_ruangan(g, room, ai_pos)
        kelas = 'ruang aktif' if aktif and g.tim_pos[aktif] == room else 'ruang'
        sel.append(f'<div class="{kelas}">{"".join(isi)}</div>')
    return CSS + f'<div class="peta">{"".join(sel)}</div>'


def _baris_isi_ruangan(g, room, ai_pos):
    pion, tag, orang = _pion(g, room, ai_pos), _tag_ruangan(g, room), _orang_di_ruangan(g, room)
    baris = []
    if pion:
        baris.append(''.join(pion) + '<br>')
    if tag:
        baris.append(''.join(tag) + '<br>')
    if orang:
        baris.append(f'<span class="ket">{", ".join(orang)}</span>')
    return baris


def _pion(g, room, ai_pos):
    pion = [f'<span class="chip" style="background:{WARNA_D[d]}">D{d}</span>' for d in (1, 2, 3) if g.tim_pos[d] == room]
    if ai_pos == room:
        pion.append('<span class="chip" style="background:#c0392b">AI</span>')
    return pion


def _tag_ruangan(g, room):
    tanda = [(room == START, 'sudah diperiksa polisi'), (room in g.tim_searched, 'digeledah tim'),
             (room in g.ai_searched, 'digeledah AI'), (room == g.case['found'], 'jasad ditemukan')]
    return [f'<span class="tag">{teks}</span>' for ada, teks in tanda if ada]


def _orang_di_ruangan(g, room):
    return [sn(s) + (' (ditangkap)' if s == g.case['arrested'] else '') for s in S_IDS if g.case['loc'][s] == room]


def status_teleport(g):
    h = g.tp_holder
    if h is None:
        return 'belum ditemukan (tersembunyi di salah satu ruangan berisi bukti)'
    if h == 'terpakai':
        return 'sudah dipakai'
    if h == 'ai':
        return 'dipegang Detektif AI'
    return f'dipegang Detektif {h[1]}'


def animasi_ai(g, ph_peta, ph_info):
    """Jalankan giliran AI. Mode normal: tampilkan setiap aksi AI di peta satu per satu."""
    langkah = g.giliran_ai()
    st.session_state.pesan = 'Giliran Detektif AI selesai: ' + (
        '; '.join(teks_aksi(act) for _, act in langkah) if langkah else 'tidak bergerak') + '.'
    if g.uji:
        return
    pos = langkah[0][0] if langkah else g.ai_pos
    for i, (_, act) in enumerate(langkah, 1):
        if act[0] in ('pindah', 'teleport'):
            pos = act[1]
        ph_peta.markdown(peta_html(g, ai_pos=pos), unsafe_allow_html=True)
        ph_info.info(f'Giliran Detektif AI, aksi {i}/{len(langkah)}: {teks_aksi(act)}')
        time.sleep(JEDA_ANIMASI)
    if not langkah:
        ph_info.info('Detektif AI tidak bergerak di ronde ini.')
        time.sleep(JEDA_ANIMASI)


# ---------------------------------------------------------------- panel aksi dan tuduhan
def panel_aksi(g, d):
    legal = g.aksi_legal(d)
    st.markdown(f'**Detektif {d}** di **{rn(g.tim_pos[d])}**')
    _tombol_pindah(g, d, legal)
    _tombol_teleport(g, d, legal)
    st.caption('Geledah dan interogasi')
    _tombol_geledah(g, d, legal)
    _tombol_interogasi(g, d, legal)


def _tombol_pindah(g, d, legal):
    st.caption('Pindah')
    for act in [a for a in legal if a[0] == 'pindah']:
        st.button(f'Pindah ke {rn(act[1])}', key=f'p-{g.ronde}-{d}-{act[1]}', on_click=klik_aksi, args=(d, act),
                  width='stretch')


def _tombol_teleport(g, d, legal):
    st.caption('Teleport (serong 1–2 kotak, sekali pakai)')
    tele = [a for a in legal if a[0] == 'teleport']
    if not tele:
        st.button('Teleport', key=f't-{g.ronde}-{d}', disabled=True, width='stretch',
                  help='Detektif ini tidak memegang teleport.')
    for act in tele:
        st.button(f'Teleport ke {rn(act[1])}', key=f't-{g.ronde}-{d}-{act[1]}', on_click=klik_aksi, args=(d, act),
                  width='stretch')


def _tombol_geledah(g, d, legal):
    pos, key = g.tim_pos[d], f'g-{g.ronde}-{d}'
    gel = [a for a in legal if a[0] == 'geledah']
    if gel:
        st.button(f'Geledah {rn(pos)}', key=key, on_click=klik_aksi, args=(d, gel[0]), type='primary', width='stretch')
    elif pos == START:
        st.button('Sudah diperiksa polisi', key=key, disabled=True, width='stretch')
    else:
        st.button('Geledah', key=key, disabled=True, width='stretch', help='Ruangan ini sudah digeledah tim.')


def _tombol_interogasi(g, d, legal):
    tanya = [a for a in legal if a[0] == 'interogasi']
    for act in tanya:
        st.button(f'Interogasi {sn(act[1])}', key=f'i-{g.ronde}-{d}-{act[1]}', on_click=klik_aksi, args=(d, act),
                  type='primary', width='stretch')
    if not tanya:
        st.button('Interogasi', key=f'i-{g.ronde}-{d}', disabled=True, width='stretch',
                  help='Tidak ada tersangka yang belum ditanya di ruangan ini.')


def panel_tuduh(sidang=False):
    with st.form('form_tuduh'):
        st.markdown('**Tuduh** · hanya sekali. Kalau salah, tim kalah.')
        st.selectbox('Pelaku', S_IDS, format_func=sn, key='tuduh_s')
        st.selectbox('Senjata', W_IDS, format_func=wn, key='tuduh_w')
        st.selectbox('TKP', TKP, format_func=rn, key='tuduh_r')
        st.form_submit_button('Tuduh sekarang', on_click=klik_tuduh, type='primary', width='stretch')
    if sidang:
        st.button('Tidak menuduh, serahkan ke hakim', on_click=klik_serahkan, width='stretch')


# ---------------------------------------------------------------- catatan dan gerak AI
def catatan_petunjuk(g):
    _daftar_berkas(g)
    _daftar_temuan_tim(g)
    _daftar_terdengar(g)
    st.text_area('Catatan tim', key='catatan', height=120, placeholder='Tulis dugaan kalian di sini...')


def _daftar_berkas(g):
    st.markdown('**Berkas polisi**')
    for c in g.case['clues']:
        if c['kind'] == 'berkas':
            st.markdown(f'- {c["text"]}')


def _daftar_temuan_tim(g):
    temuan = [(r, data['d'], i) for r, siapa, jenis, data in g.events
              if siapa == 'tim' and jenis == 'aksi' for i in data['found']]
    st.markdown('**Bukti yang ditemukan tim**')
    if not temuan:
        st.caption('Belum ada.')
    for r, d, i in temuan:
        st.markdown(f'- R{r} · D{d}: {teks_bukti(g.case, i)}')


def _daftar_terdengar(g):
    dengar = [(r, data) for r, siapa, jenis, data in g.events if siapa == 'tim' and jenis == 'menguping']
    if dengar:
        st.markdown('**Terdengar dari Detektif AI** (hanya topik)')
        for r, data in dengar:
            st.markdown(f'- R{r}: AI {data["jenis"]} {target_menguping(data)} → topik {", ".join(data["topik"])}')


def gerak_ai(g):
    baris = [teks for r, siapa, jenis, data in g.events if siapa == 'ai'
             for teks in [_teks_gerak_ai(r, jenis, data)] if teks]
    st.markdown('\n'.join(baris) if baris else 'Belum bergerak.')


def _teks_gerak_ai(r, jenis, data):
    if jenis == 'aksi':
        return f'- R{r}: {teks_aksi(data["act"])}'
    if jenis == 'menguping':
        return f'- R{r}: AI menguping tim ({data["jenis"]} {target_menguping(data)})'
    if jenis == 'teleport':
        return f'- R{r}: AI menemukan teleport'
    return None


# ---------------------------------------------------------------- layar selesai
def trace_dari_event(g):
    """Reasoning trace dari event permainan, untuk Detektif AI yang tidak punya trace_teks() sendiri."""
    lines = []
    for r, siapa, jenis, data in g.events:
        if siapa == 'ai' and jenis == 'aksi':
            lines.append(_trace_aksi(r, data))
        elif siapa == 'ai' and jenis == 'amati':
            lines += [line for e in data for line in _trace_amati(g.case, r, e)]
    return lines + _trace_bukti_tuduhan(g.ai)


def _trace_aksi(r, data):
    rencana = data['info'].get('rencana')
    return f'R{r} AKSI {teks_aksi(data["act"])}' + (f'   rencana: {" -> ".join(rencana)}' if rencana else '')


def _trace_amati(case, r, e):
    lines = [f'R{r} BUKTI {teks_bukti(case, e["id"])}']
    if 'fol' not in e:
        return lines + [f'     model {e["sebelum"]} -> {e["sesudah"]}']
    lines.append(f'     TELL {"; ".join(e["fol"])}')
    if not e['relevan']:
        lines.append(f'     tidak relevan: {e["alasan"]}')
    baru = ', '.join(fakta(c, v, s) for (c, v), s in e['baru']) or 'belum ada kesimpulan baru'
    return lines + [f'     ASK  {e["query"]} query, {e["langkah"]} langkah resolusi -> {baru}']


def _trace_bukti_tuduhan(ai):
    if not getattr(ai, 'terbukti', None):
        return []
    lines = ['', f'Terbukti({teks_jawaban(ai.terbukti)}). Bukti resolusi untuk pelaku: KB ∧ ¬Pelaku(x) ⊢ □']
    for i, (a, b, res) in enumerate(ai.bukti('s', ai.terbukti.s, True), 1):
        lines += [f'{i:>3}. {a}', f'     + {b}', f'     ⇒ {res}']
    return lines


def layar_selesai(g):
    ss = st.session_state
    if ss.t_selesai is None:
        ss.t_selesai = time.time()
        ss.log_path = simpan_log(g)
    if g.uji:
        _tuduhan_tersembunyi_ai(g)
    jenis, teks = HASIL_TEKS[g.hasil_akhir()['tipe']]
    getattr(st, jenis)(f'Hasil melawan AI: {teks}' if g.uji else teks)
    if g.hasil['tebakan']:
        st.markdown(f'Tuduhan tim: **{teks_jawaban(g.hasil["tebakan"])}** di ronde {g.hasil["ronde"]}')
    st.markdown(f'Jawaban sebenarnya: **{teks_jawaban(g.case["sol"])}**')
    menit, detik = divmod(int(ss.t_selesai - ss.t_mulai), 60)
    st.caption(f'Durasi {menit} menit {detik} detik · log tersimpan di {os.path.relpath(ss.log_path)}')
    with st.expander('Reasoning trace Detektif AI', expanded=True):
        trace = g.ai.trace_teks() or trace_dari_event(g)
        st.code('\n'.join(trace) or 'AI tidak mengamati bukti apa pun.', language=None)


def _tuduhan_tersembunyi_ai(g):
    """Test mode: hasil di layar baru final setelah dibandingkan dengan tuduhan AI yang disembunyikan."""
    ai_live = st.session_state.ai_live
    st.info(TUDUHAN_TIM_TEKS[g.hasil['tipe']])
    if g.tuduhan_ai:
        t = g.tuduhan_ai
        st.markdown(f'Detektif AI ({ai_live}) diam-diam sudah menuduh di ronde {t["ronde"]}: '
                    f'**{teks_jawaban(t["tebakan"])}**')
    else:
        st.markdown(f'Detektif AI ({ai_live}) belum menemukan jawaban sampai sidang.')


# ---------------------------------------------------------------- sidebar
def sidebar():
    ss = st.session_state
    st.header('Game baru')
    terkunci = 'game' in ss and not ss.game.hasil      # pengaturan tidak bisa diubah selama game berjalan
    pemain = st.selectbox('Inisial pemain', PEMAIN, index=None, placeholder='Pilih inisial', disabled=terkunci)
    mode = st.radio('Mode', ['Normal', 'Test mode'], horizontal=True, disabled=terkunci,
                    help='Test mode: tanpa animasi, tuduhan AI disembunyikan, game lanjut sampai tim menuduh atau ronde 7 habis.')
    if mode == 'Test mode' and PEMBAGIAN:
        pilihan = _pilihan_dari_pembagian(pemain)
    else:
        pilihan = _pilihan_manual(pemain, mode, terkunci)
    if st.button('Mulai', type='primary', width='stretch', disabled=pilihan is None or terkunci):
        game_baru(pemain, *pilihan)
        st.rerun()
    if terkunci:
        st.caption('Game sedang berjalan. Pengaturan terkunci sampai game selesai. Refresh halaman untuk membatalkan.')
    elif not pemain:
        st.caption('Pilih inisial untuk mulai.')
    if 'game' in ss:
        st.divider()
        st.markdown(CARA_MAIN)


def _pilihan_dari_pembagian(pemain):
    """Test mode: kasus dan lawan diambil dari pembagian.json, jadi pemain tidak tahu sedang
    melawan AI yang mana. Mengembalikan (seed, lawan, uji) atau None."""
    jatah = jatah_berikutnya(pemain) if pemain else None
    if jatah:
        st.caption(f'Game ke-{jatah["no"]} · Kasus {jatah["seed"]} · lawan dirahasiakan')
        return jatah['seed'], jatah['lawan'], True
    if pemain:
        st.caption('Semua game jatahmu sudah selesai.')
    return None


def _pilihan_manual(pemain, mode, terkunci):
    """Mode normal (latihan, kasus 301–350 supaya kasus playtest tidak bocor), atau test mode
    tanpa pembagian.json. Mengembalikan (seed, lawan, uji) atau None kalau inisial belum dipilih."""
    if mode == 'Normal':
        seed = LATIHAN + st.number_input('Nomor latihan', min_value=1, max_value=JUMLAH_LATIHAN, value=1, step=1,
                                         disabled=terkunci)
    else:
        seed = st.number_input('Nomor kasus', min_value=1, max_value=LATIHAN, value=1, step=1, disabled=terkunci)
    ai_live = st.selectbox('Lawan AI', list(LAWAN_AI), disabled=terkunci)
    return (int(seed), ai_live, mode == 'Test mode') if pemain else None


# ---------------------------------------------------------------- halaman
def halaman_awal():
    st.title('Rumah Terkunci')
    st.info(CERITA)
    st.markdown(CARA_MAIN)
    st.write('Pilih inisial dan mode di samping, lalu tekan **Mulai**.')


def kepala_permainan(g, d_aktif):
    judul = f'Kasus {g.case["seed"]}' if g.uji else f'Latihan {g.case["seed"] - LATIHAN}'
    st.title(f'Rumah Terkunci · {judul}')
    st.info(f'**Tuan Hartono ditemukan tewas di rumahnya.** Jasadnya ditemukan pagi ini di **{rn(g.case["found"])}**, '
            f'dengan perkiraan waktu kematian pukul {WAKTU_KEMATIAN}. Polisi langsung menganggap '
            f'{rn(g.case["found"]).lower()} sebagai TKP dan menangkap **{sn(g.case["arrested"])}**, padahal berkasnya '
            f'hanya berisi motif dan gosip. Sidang dimulai setelah ronde {MAX_ROUNDS}. '
            'Temukan pelaku, senjata, dan TKP yang sebenarnya sebelum Detektif AI.')
    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Ronde', f'{g.ronde}/{MAX_ROUNDS}')
    m2.metric('Giliran', _teks_giliran(g, d_aktif))
    m3.metric('Lawan', 'Dirahasiakan' if g.uji and not g.hasil else st.session_state.ai_live)
    m4.metric('Mode', 'Test mode' if g.uji else 'Normal')


def _teks_giliran(g, d_aktif):
    if g.hasil:
        return 'Selesai'
    if g.sidang_dibuka:
        return 'Sidang'
    return f'Detektif {d_aktif}' if d_aktif else 'Detektif AI'


def kolom_peta(g, d_aktif):
    ss = st.session_state
    ph_peta = st.empty()
    ph_info = st.empty()
    if ss.ai_pending and not g.hasil:
        ss.ai_pending = False
        ph_peta.markdown(peta_html(g), unsafe_allow_html=True)
        animasi_ai(g, ph_peta, ph_info)
        st.rerun()
    ph_peta.markdown(peta_html(g, aktif=d_aktif), unsafe_allow_html=True)
    if ss.pesan:
        ph_info.info(ss.pesan)
    st.caption(f'Teleport: {status_teleport(g)} · Polisi menangkap {sn(g.case["arrested"])}')
    with st.expander('Gerak Detektif AI', expanded=not g.uji):
        gerak_ai(g)


def kolom_aksi(g, d_aktif):
    if g.hasil:
        layar_selesai(g)
    elif g.sidang_dibuka:
        st.subheader('Sidang')
        st.write('Ronde 7 sudah habis. Tim boleh menuduh sekali lagi, atau menyerahkan ke hakim.')
        panel_tuduh(sidang=True)
    elif d_aktif:
        panel_aksi(g, d_aktif)
        st.divider()
        panel_tuduh()
    with st.expander('Catatan petunjuk', expanded=True):
        catatan_petunjuk(g)


def main():
    st.set_page_config(page_title='Rumah Terkunci', layout='wide')
    with st.sidebar:
        sidebar()
    if 'game' not in st.session_state:
        halaman_awal()
        return
    g = st.session_state.game
    d_aktif = g.giliran_tim()
    kepala_permainan(g, d_aktif)
    kiri, kanan = st.columns([3, 2], gap='large')
    with kiri:
        kolom_peta(g, d_aktif)
    with kanan:
        kolom_aksi(g, d_aktif)


main()
