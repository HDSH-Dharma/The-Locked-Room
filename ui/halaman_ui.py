"""
halaman_ui.py
UI — tata letak halaman: halaman awal, kepala permainan, dan dua kolom (peta, aksi).
"""
import streamlit as st

from model.ui_model import CARA_MAIN, CERITA
from ui import aksi_ui, catatan_ui, hasil_ui, peta_ui, sidebar_ui

# MARK: - Halaman

def tampilkan_aplikasi():
    st.set_page_config(page_title='Rumah Terkunci', layout='wide')
    with st.sidebar:
        sidebar_ui.tampilkan()
    if 'layar' not in st.session_state:
        _halaman_awal()
        return
    layar   = st.session_state.layar
    d_aktif = layar.giliran_aktif()
    _kepala_permainan(layar, d_aktif)
    kiri, kanan = st.columns([3, 2], gap='large')
    with kiri:
        peta_ui.tampilkan(layar, d_aktif)
    with kanan:
        _kolom_aksi(layar, d_aktif)


# MARK: - Private Helpers

def _halaman_awal():
    st.title('Rumah Terkunci')
    st.info(CERITA)
    st.markdown(CARA_MAIN)
    st.write('Pilih inisial dan mode di samping, lalu tekan **Mulai**.')


def _kepala_permainan(layar, d_aktif):
    st.title(layar.judul())
    st.info(layar.cerita_kasus())
    kolom = st.columns(4)
    for i, (label, nilai) in enumerate(layar.metrik(d_aktif)):
        kolom[i].metric(label, nilai)


def _kolom_aksi(layar, d_aktif):
    if layar.selesai():
        hasil_ui.tampilkan(layar)
    elif layar.sidang_dibuka():
        st.subheader('Sidang')
        st.write('Ronde 7 sudah habis. Tim boleh menuduh sekali lagi, atau menyerahkan ke hakim.')
        aksi_ui.panel_tuduh(layar, sidang=True)
    elif d_aktif:
        aksi_ui.panel_aksi(layar, d_aktif)
        st.divider()
        aksi_ui.panel_tuduh(layar)
    with st.expander('Catatan petunjuk', expanded=True):
        catatan_ui.tampilkan(layar)
