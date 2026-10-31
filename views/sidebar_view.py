"""
sidebar_view.py
View — sidebar "Game baru". Logikanya ada di SidebarViewModel.
"""
import streamlit as st

from models.ui_model import CARA_MAIN
from viewmodels.permainan_viewmodel import PermainanViewModel
from viewmodels.sidebar_viewmodel import SidebarViewModel

# MARK: - Sidebar

def tampilkan():
    svm      = SidebarViewModel(st.session_state.get('vm'))
    terkunci = svm.terkunci()
    st.header('Game baru')
    pemain = st.selectbox('Inisial pemain', svm.pemain(), index=None, placeholder='Pilih inisial', disabled=terkunci)
    mode = st.radio('Mode', ['Normal', 'Test mode'], horizontal=True, disabled=terkunci,
                    help='Test mode: tanpa animasi, tuduhan AI disembunyikan, game lanjut sampai tim menuduh atau ronde 7 habis.')
    if svm.pakai_pembagian(mode):
        pilihan = _pilihan_dari_pembagian(svm, pemain)
    else:
        pilihan = _pilihan_manual(svm, pemain, mode, terkunci)
    if st.button('Mulai', type='primary', width='stretch', disabled=pilihan is None or terkunci):
        _mulai_game(pemain, pilihan)
    keterangan = svm.keterangan_bawah(pemain)
    if keterangan:
        st.caption(keterangan)
    if svm.ada_game():
        st.divider()
        st.markdown(CARA_MAIN)


# MARK: - Private Helpers

def _pilihan_dari_pembagian(svm, pemain):
    keterangan, pilihan = svm.jatah(pemain)
    if keterangan:
        st.caption(keterangan)
    return pilihan


def _pilihan_manual(svm, pemain, mode, terkunci):
    if svm.latihan(mode):
        nomor = st.number_input('Nomor latihan', min_value=1, max_value=svm.batas_latihan(), value=1, step=1,
                                disabled=terkunci)
    else:
        nomor = st.number_input('Nomor kasus', min_value=1, max_value=svm.batas_kasus(), value=1, step=1,
                                disabled=terkunci)
    ai_live = st.selectbox('Lawan AI', svm.daftar_lawan(), disabled=terkunci)
    return svm.pilihan_manual(pemain, mode, nomor, ai_live)


def _mulai_game(pemain, pilihan):
    st.session_state.vm         = PermainanViewModel(pemain, *pilihan)
    st.session_state.ai_pending = False
    st.session_state.catatan    = ''
    st.rerun()
