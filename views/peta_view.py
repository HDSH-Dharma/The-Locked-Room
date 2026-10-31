"""
peta_view.py
View — kolom kiri: peta rumah, animasi giliran Detektif AI, status teleport, dan riwayat gerak AI.
"""
import time

import streamlit as st

from models.ui_model import JEDA_ANIMASI
from views.komponen_view import peta_html

# MARK: - Kolom peta

def tampilkan(vm, d_aktif):
    ph_peta = st.empty()
    ph_info = st.empty()
    if st.session_state.get('ai_pending') and not vm.selesai():
        st.session_state.ai_pending = False
        ph_peta.markdown(peta_html(vm.sel_peta()), unsafe_allow_html=True)
        _animasi_ai(vm, ph_peta, ph_info)
        st.rerun()
    ph_peta.markdown(peta_html(vm.sel_peta(aktif=d_aktif)), unsafe_allow_html=True)
    if vm.pesan:
        ph_info.info(vm.pesan)
    st.caption(vm.status_bawah_peta())
    with st.expander('Gerak Detektif AI', expanded=vm.buka_gerak_ai()):
        st.markdown(vm.teks_gerak_ai())


# MARK: - Private Helpers

def _animasi_ai(vm, ph_peta, ph_info):
    for pos, teks in vm.jalankan_giliran_ai():
        if pos is not None:
            ph_peta.markdown(peta_html(vm.sel_peta(ai_pos=pos)), unsafe_allow_html=True)
        ph_info.info(teks)
        time.sleep(JEDA_ANIMASI)
