"""
peta_ui.py
UI — kolom kiri: peta rumah, animasi giliran Detektif AI, status teleport, dan riwayat gerak AI.
"""
import time

import streamlit as st

from model.ui_model import JEDA_ANIMASI
from ui.komponen_ui import peta_html

# MARK: - Kolom peta

def tampilkan(layar, d_aktif):
    ph_peta = st.empty()
    ph_info = st.empty()
    if st.session_state.get('ai_pending') and not layar.selesai():
        st.session_state.ai_pending = False
        ph_peta.markdown(peta_html(layar.sel_peta()), unsafe_allow_html=True)
        _animasi_ai(layar, ph_peta, ph_info)
        st.rerun()
    ph_peta.markdown(peta_html(layar.sel_peta(aktif=d_aktif)), unsafe_allow_html=True)
    if layar.pesan:
        ph_info.info(layar.pesan)
    st.caption(layar.status_bawah_peta())
    with st.expander('Gerak Detektif AI', expanded=layar.buka_gerak_ai()):
        st.markdown(layar.teks_gerak_ai())


# MARK: - Private Helpers

def _animasi_ai(layar, ph_peta, ph_info):
    for pos, teks in layar.jalankan_giliran_ai():
        if pos is not None:
            ph_peta.markdown(peta_html(layar.sel_peta(ai_pos=pos)), unsafe_allow_html=True)
        ph_info.info(teks)
        time.sleep(JEDA_ANIMASI)
