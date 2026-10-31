"""
sidebar_ui.py
UI — sidebar "Game baru". Logikanya ada di LayarSidebar.
"""
import streamlit as st

from logic.layar.layar_permainan import LayarPermainan
from logic.layar.layar_sidebar import LayarSidebar
from model.ui_model import CARA_MAIN

# MARK: - Sidebar

def tampilkan():
    layar    = LayarSidebar(st.session_state.get('layar'))
    terkunci = layar.terkunci()
    st.header('Game baru')
    pemain = st.selectbox('Inisial pemain', layar.pemain(), index=None, placeholder='Pilih inisial', disabled=terkunci)
    mode = st.radio('Mode', ['Normal', 'Test mode'], horizontal=True, disabled=terkunci,
                    help='Test mode: tanpa animasi, tuduhan AI disembunyikan, game lanjut sampai tim menuduh atau ronde 7 habis.')
    if layar.pakai_pembagian(mode):
        pilihan = _pilihan_dari_pembagian(layar, pemain)
    else:
        pilihan = _pilihan_manual(layar, pemain, mode, terkunci)
    if st.button('Mulai', type='primary', width='stretch', disabled=pilihan is None or terkunci):
        _mulai_game(pemain, pilihan)
    keterangan = layar.keterangan_bawah(pemain)
    if keterangan:
        st.caption(keterangan)
    if layar.ada_game():
        st.divider()
        st.markdown(CARA_MAIN)


# MARK: - Private Helpers

def _pilihan_dari_pembagian(layar, pemain):
    keterangan, pilihan = layar.jatah(pemain)
    if keterangan:
        st.caption(keterangan)
    return pilihan


def _pilihan_manual(layar, pemain, mode, terkunci):
    if layar.latihan(mode):
        nomor = st.number_input('Nomor latihan', min_value=1, max_value=layar.batas_latihan(), value=1, step=1,
                                disabled=terkunci)
    else:
        nomor = st.number_input('Nomor kasus', min_value=1, max_value=layar.batas_kasus(), value=1, step=1,
                                disabled=terkunci)
    ai_live = st.selectbox('Lawan AI', layar.daftar_lawan(), disabled=terkunci)
    return layar.pilihan_manual(pemain, mode, nomor, ai_live)


def _mulai_game(pemain, pilihan):
    st.session_state.layar      = LayarPermainan(pemain, *pilihan)
    st.session_state.ai_pending = False
    st.session_state.catatan    = ''
    st.rerun()
