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

import agen_baseline
from agen_v1 import AgenV1
from agen_v2 import AgenV2
from kasus import S_IDS, W_IDS, TKP, R_IDS, POS, START, MAX_ROUNDS, sn, wn, rn
from permainan import Permainan, teks_aksi, teks_jawaban
from simulasi import teks_bukti, fakta

LOGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
LAWAN = {'v2': AgenV2, 'v1': AgenV1, 'penebak': lambda: agen_baseline.DetektifPenebak(3, 0)}
if hasattr(agen_baseline, 'AIPolisi'):
    LAWAN['polisi'] = agen_baseline.AIPolisi
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
.tag.bukti {border-color: #c99a06; color: #c99a06;}
.ket {opacity: .75; font-size: 0.75rem;}
</style>
"""


class TimManusia:
    """Objek tim untuk Permainan saat dimainkan manusia. Aksi tim datang dari tombol UI;
    topik yang terdengar dari AI dicatat engine sebagai event ('tim', 'menguping')."""

    def mulai(self, case):
        pass

    def amati(self, ids):
        pass

    def dengar(self, jenis, target, topik):
        pass


# ---------------------------------------------------------------- game baru dan log
def game_baru(pemain, seed, ai_live, uji, tanda):
    ss = st.session_state
    g = Permainan(seed, LAWAN[ai_live](), TimManusia(), teleport=True, menguping=True, uji=uji)
    g.mulai()
    ss.game, ss.ai_live, ss.pemain, ss.tanda = g, ai_live, pemain, tanda
    ss.t_mulai, ss.t_selesai, ss.log_path = time.time(), None, None
    ss.ai_pending, ss.pesan, ss.catatan = False, None, ''


def simpan_log(g):
    ss = st.session_state
    folder = LOGS if g.uji else os.path.join(LOGS, 'latihan')
    os.makedirs(folder, exist_ok=True)
    data = g.ke_log(ss.pemain, ss.ai_live, ss.t_selesai - ss.t_mulai, ss.tanda)
    base = f'{ss.pemain}_{g.case["seed"]}'
    path, i = os.path.join(folder, base + '.json'), 2
    while os.path.exists(path):          # jangan menimpa log lama dengan kasus yang sama
        path, i = os.path.join(folder, f'{base}_{i}.json'), i + 1
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return path


# ---------------------------------------------------------------- aksi dari tombol
def klik_aksi(d, act):
    g = st.session_state.game
    if g.giliran_tim() != d or act not in g.aksi_legal(d):
        return                            # klik basi (misalnya tombol ditekan dua kali)
    tp_sebelum = g.tp_holder
    found = g.aksi_tim(d, act)
    teks = f'Detektif {d} {teks_aksi(act)}.'
    if act[0] in ('geledah', 'interogasi'):
        teks += ' Bukti baru: ' + ('; '.join(teks_bukti(g.case, i) for i in found) if found else 'tidak ada.')
    if tp_sebelum is None and g.tp_holder == ('tim', d):
        teks += f' Detektif {d} menemukan teleport!'
    st.session_state.pesan = teks
    if g.giliran_tim() is None:
        st.session_state.ai_pending = True


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


# ---------------------------------------------------------------- tampilan
def peta_html(g, ai_pos=None, aktif=None):
    ai_pos = ai_pos or g.ai_pos
    sel = []
    for room in sorted(R_IDS, key=lambda r: POS[r]):
        isi = [f'<div class="nama">{rn(room)}</div>']
        pion = [f'<span class="chip" style="background:{WARNA_D[d]}">D{d}</span>'
                for d in (1, 2, 3) if g.tim_pos[d] == room]
        if ai_pos == room:
            pion.append('<span class="chip" style="background:#c0392b">AI</span>')
        if pion:
            isi.append(''.join(pion) + '<br>')
        tag = []
        if st.session_state.tanda and g.case['room_clues'][room] and room not in g.tim_searched:
            tag.append('<span class="tag bukti">ada bukti</span>')
        if room in g.tim_searched:
            tag.append('<span class="tag">digeledah tim</span>')
        if room in g.ai_searched:
            tag.append('<span class="tag">digeledah AI</span>')
        if room == g.case['found']:
            tag.append('<span class="tag">jasad ditemukan</span>')
        if tag:
            isi.append(''.join(tag) + '<br>')
        orang = [sn(s) + (' (ditangkap)' if s == g.case['arrested'] else '')
                 for s in S_IDS if g.case['loc'][s] == room]
        if orang:
            isi.append(f'<span class="ket">{", ".join(orang)}</span>')
        kelas = 'ruang aktif' if aktif and g.tim_pos[aktif] == room else 'ruang'
        sel.append(f'<div class="{kelas}">{"".join(isi)}</div>')
    return CSS + f'<div class="peta">{"".join(sel)}</div>'


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


def panel_aksi(g, d):
    legal = g.aksi_legal(d)
    pos = g.tim_pos[d]
    st.markdown(f'**Detektif {d}** di **{rn(pos)}**')
    r = g.ronde

    st.caption('Pindah')
    for act in [a for a in legal if a[0] == 'pindah']:
        st.button(f'Pindah ke {rn(act[1])}', key=f'p-{r}-{d}-{act[1]}', on_click=klik_aksi, args=(d, act),
                  width='stretch')

    st.caption('Teleport (serong 1–2 kotak, sekali pakai)')
    tele = [a for a in legal if a[0] == 'teleport']
    if not tele:
        st.button('Teleport', key=f't-{r}-{d}', disabled=True, width='stretch',
                  help='Detektif ini tidak memegang teleport.')
    for act in tele:
        st.button(f'Teleport ke {rn(act[1])}', key=f't-{r}-{d}-{act[1]}', on_click=klik_aksi, args=(d, act),
                  width='stretch')

    st.caption('Geledah dan interogasi')
    gel = [a for a in legal if a[0] == 'geledah']
    if gel:
        st.button(f'Geledah {rn(pos)}', key=f'g-{r}-{d}', on_click=klik_aksi, args=(d, gel[0]),
                  type='primary', width='stretch')
    else:
        alasan = 'Ruangan ini sudah digeledah tim.' if pos in g.tim_searched else 'Tidak ada yang bisa digeledah di sini.'
        st.button('Geledah', key=f'g-{r}-{d}', disabled=True, width='stretch', help=alasan)
    tanya = [a for a in legal if a[0] == 'interogasi']
    for act in tanya:
        st.button(f'Interogasi {sn(act[1])}', key=f'i-{r}-{d}-{act[1]}', on_click=klik_aksi, args=(d, act),
                  type='primary', width='stretch')
    if not tanya:
        st.button('Interogasi', key=f'i-{r}-{d}', disabled=True, width='stretch',
                  help='Tidak ada tersangka yang belum ditanya di ruangan ini.')


def panel_tuduh(g, sidang=False):
    with st.form('form_tuduh'):
        st.markdown('**Tuduh** · hanya sekali. Kalau salah, tim kalah.')
        st.selectbox('Pelaku', S_IDS, format_func=sn, key='tuduh_s')
        st.selectbox('Senjata', W_IDS, format_func=wn, key='tuduh_w')
        st.selectbox('TKP', TKP, format_func=rn, key='tuduh_r')
        st.form_submit_button('Tuduh sekarang', on_click=klik_tuduh, type='primary', width='stretch')
    if sidang:
        st.button('Tidak menuduh, serahkan ke hakim', on_click=klik_serahkan, width='stretch')


def catatan_petunjuk(g):
    case = g.case
    st.markdown('**Berkas polisi**')
    for c in case['clues']:
        if c['kind'] == 'berkas':
            st.markdown(f'- {c["text"]}')
    temuan = [(r, data['d'], i) for r, siapa, jenis, data in g.events
              if siapa == 'tim' and jenis == 'aksi' for i in data['found']]
    st.markdown('**Bukti yang ditemukan tim**')
    if not temuan:
        st.caption('Belum ada.')
    for r, d, i in temuan:
        st.markdown(f'- R{r} · D{d}: {teks_bukti(case, i)}')
    dengar = [(r, data) for r, siapa, jenis, data in g.events if siapa == 'tim' and jenis == 'menguping']
    if dengar:
        st.markdown('**Terdengar dari Detektif AI** (hanya topik)')
        for r, data in dengar:
            target = rn(data['target']) if data['jenis'] == 'geledah' else sn(data['target'])
            st.markdown(f'- R{r}: AI {data["jenis"]} {target} → topik {", ".join(data["topik"])}')
    st.text_area('Catatan tim', key='catatan', height=120, placeholder='Tulis dugaan kalian di sini...')


def gerak_ai(g):
    baris = []
    for r, siapa, jenis, data in g.events:
        if siapa == 'ai' and jenis == 'aksi':
            baris.append(f'- R{r}: {teks_aksi(data["act"])}')
        elif siapa == 'ai' and jenis == 'menguping':
            target = rn(data['target']) if data['jenis'] == 'geledah' else sn(data['target'])
            baris.append(f'- R{r}: AI menguping tim ({data["jenis"]} {target})')
        elif siapa == 'ai' and jenis == 'teleport':
            baris.append(f'- R{r}: AI menemukan teleport')
    st.markdown('\n'.join(baris) if baris else 'Belum bergerak.')


def trace_sementara(g):
    """Reasoning trace dari event permainan. Dipakai sampai trace_teks() dari Dharma tersedia."""
    case, L = g.case, []
    for r, siapa, jenis, data in g.events:
        if siapa == 'ai' and jenis == 'aksi':
            rencana = data['info'].get('rencana')
            L.append(f'R{r} AKSI {teks_aksi(data["act"])}' + (f'   rencana: {" -> ".join(rencana)}' if rencana else ''))
        elif siapa == 'ai' and jenis == 'amati':
            for e in data:
                L.append(f'R{r} BUKTI {teks_bukti(case, e["id"])}')
                if 'fol' in e:
                    L.append(f'     TELL {"; ".join(e["fol"])}')
                    if not e['relevan']:
                        L.append(f'     tidak relevan: {e["alasan"]}')
                    baru = ', '.join(fakta(c, v, s) for (c, v), s in e['baru']) or 'belum ada kesimpulan baru'
                    L.append(f'     ASK  {e["query"]} query, {e["langkah"]} langkah resolusi -> {baru}')
                else:
                    L.append(f'     model {e["sebelum"]} -> {e["sesudah"]}')
    ai = g.ai
    if getattr(ai, 'terbukti', None):
        L.append('')
        L.append(f'Terbukti({teks_jawaban(ai.terbukti)}). Bukti resolusi untuk pelaku: KB ∧ ¬Pelaku(x) ⊢ □')
        for i, (a, b, res) in enumerate(ai.bukti('s', ai.terbukti.s, True), 1):
            L.append(f'{i:>3}. {a}')
            L.append(f'     + {b}')
            L.append(f'     ⇒ {res}')
    return L


def layar_selesai(g):
    ss = st.session_state
    if ss.t_selesai is None:
        ss.t_selesai = time.time()
        ss.log_path = simpan_log(g)
    if g.uji:
        # Hasil di layar test mode baru final setelah dibandingkan dengan tuduhan AI yang disembunyikan.
        st.info(TUDUHAN_TIM_TEKS[g.hasil['tipe']])
        if g.tuduhan_ai:
            t = g.tuduhan_ai
            st.markdown(f'Detektif AI ({ss.ai_live}) diam-diam sudah menuduh di ronde {t["ronde"]}: '
                        f'**{teks_jawaban(t["tebakan"])}**')
        else:
            st.markdown(f'Detektif AI ({ss.ai_live}) belum menemukan jawaban sampai sidang.')
    jenis, teks = HASIL_TEKS[g.hasil_akhir()['tipe']]
    getattr(st, jenis)(f'Hasil melawan AI: {teks}' if g.uji else teks)
    if g.hasil['tebakan']:
        st.markdown(f'Tuduhan tim: **{teks_jawaban(g.hasil["tebakan"])}** di ronde {g.hasil["ronde"]}')
    st.markdown(f'Jawaban sebenarnya: **{teks_jawaban(g.case["sol"])}**')
    menit, detik = divmod(int(ss.t_selesai - ss.t_mulai), 60)
    st.caption(f'Durasi {menit} menit {detik} detik · log tersimpan di {os.path.relpath(ss.log_path)}')
    with st.expander('Reasoning trace Detektif AI', expanded=True):
        trace = g.ai.trace_teks() if hasattr(g.ai, 'trace_teks') else trace_sementara(g)
        st.code('\n'.join(trace) or 'AI tidak mengamati bukti apa pun.', language=None)


# ---------------------------------------------------------------- halaman
st.set_page_config(page_title='Rumah Terkunci', layout='wide')
ss = st.session_state

with st.sidebar:
    st.header('Game baru')
    pemain = st.text_input('Inisial pemain', max_chars=4, placeholder='GK').strip().upper()
    seed = st.number_input('Nomor kasus', min_value=1, max_value=300, value=1, step=1)
    ai_live = st.selectbox('Lawan AI', list(LAWAN))
    mode = st.radio('Mode', ['Normal', 'Test mode'], horizontal=True,
                    help='Test mode: tanpa animasi, tuduhan AI disembunyikan, game lanjut sampai tim menuduh atau ronde 7 habis.')
    tanda = st.checkbox('Tandai ruangan berisi bukti', value=True)
    if st.button('Mulai', type='primary', width='stretch', disabled=not pemain.isalnum()):
        game_baru(pemain, int(seed), ai_live, mode == 'Test mode', tanda)
        st.rerun()
    if not pemain.isalnum():
        st.caption('Isi inisial (huruf/angka) untuk mulai.')
    st.divider()
    st.markdown('**Cara main**\n'
                '1. Tiap ronde, Detektif 1, 2, 3 masing-masing 1 aksi.\n'
                '2. Setelah aksi ketiga, Detektif AI jalan 2–3 aksi.\n'
                '3. Pelaku selalu bohong; yang tidak bersalah selalu jujur.\n'
                '4. Jasad bisa sudah dipindahkan dari TKP.\n'
                '5. Menuduh boleh kapan saja di giliran tim, tapi hanya sekali.\n'
                f'6. Setelah ronde {MAX_ROUNDS}: sidang. Kalau tim tidak menuduh, hasilnya seri.')

if 'game' not in ss:
    st.title('Rumah Terkunci')
    st.write('Isi inisial di samping, pilih nomor kasus dan lawan AI, lalu tekan **Mulai**.')
    st.stop()

g = ss.game
mode_teks = 'Test mode' if g.uji else 'Normal'
st.title(f'Rumah Terkunci · Kasus {g.case["seed"]}')
d_aktif = g.giliran_tim()
if g.hasil:
    giliran = 'Selesai'
elif g.sidang_dibuka:
    giliran = 'Sidang'
elif d_aktif:
    giliran = f'Detektif {d_aktif}'
else:
    giliran = 'Detektif AI'
m1, m2, m3, m4 = st.columns(4)
m1.metric('Ronde', f'{g.ronde}/{MAX_ROUNDS}')
m2.metric('Giliran', giliran)
m3.metric('Lawan', ss.ai_live)
m4.metric('Mode', mode_teks)

kiri, kanan = st.columns([3, 2], gap='large')
with kiri:
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

with kanan:
    if g.hasil:
        layar_selesai(g)
    elif g.sidang_dibuka:
        st.subheader('Sidang')
        st.write('Ronde 7 sudah habis. Tim boleh menuduh sekali lagi, atau menyerahkan ke hakim.')
        panel_tuduh(g, sidang=True)
    elif d_aktif:
        panel_aksi(g, d_aktif)
        st.divider()
        panel_tuduh(g)
    with st.expander('Catatan petunjuk', expanded=True):
        catatan_petunjuk(g)
