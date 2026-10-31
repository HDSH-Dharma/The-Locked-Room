"""
halaman_view.py
View — tata letak halaman: halaman awal, kepala permainan, dan dua kolom (peta, aksi).
"""
import streamlit as st

from models.ui_model import CARA_MAIN, CERITA
from views import aksi_view, catatan_view, hasil_view, peta_view, sidebar_view

# MARK: - Halaman

def tampilkan_aplikasi():
    st.set_page_config(page_title='Rumah Terkunci', layout='wide')
    with st.sidebar:
        sidebar_view.tampilkan()
    if 'vm' not in st.session_state:
        _halaman_awal()
        return
    vm      = st.session_state.vm
    d_aktif = vm.giliran_aktif()
    _kepala_permainan(vm, d_aktif)
    kiri, kanan = st.columns([3, 2], gap='large')
    with kiri:
        peta_view.tampilkan(vm, d_aktif)
    with kanan:
        _kolom_aksi(vm, d_aktif)


# MARK: - Private Helpers

def _halaman_awal():
    st.title('Rumah Terkunci')
    st.info(CERITA)
    st.markdown(CARA_MAIN)
    st.write('Pilih inisial dan mode di samping, lalu tekan **Mulai**.')


def _kepala_permainan(vm, d_aktif):
    st.title(vm.judul())
    st.info(vm.cerita_kasus())
    kolom = st.columns(4)
    for i, (label, nilai) in enumerate(vm.metrik(d_aktif)):
        kolom[i].metric(label, nilai)


def _kolom_aksi(vm, d_aktif):
    if vm.selesai():
        hasil_view.tampilkan(vm)
    elif vm.sidang_dibuka():
        st.subheader('Sidang')
        st.write('Ronde 7 sudah habis. Tim boleh menuduh sekali lagi, atau menyerahkan ke hakim.')
        aksi_view.panel_tuduh(vm, sidang=True)
    elif d_aktif:
        aksi_view.panel_aksi(vm, d_aktif)
        st.divider()
        aksi_view.panel_tuduh(vm)
    with st.expander('Catatan petunjuk', expanded=True):
        catatan_view.tampilkan(vm)
