"""
catatan_view.py
View — catatan petunjuk tim: berkas polisi, bukti yang ditemukan, topik yang terdengar, dan catatan bebas.
"""
import streamlit as st

# MARK: - Catatan

def tampilkan(vm):
    st.markdown('**Berkas polisi**')
    for baris in vm.daftar_berkas():
        st.markdown(baris)
    st.markdown('**Bukti yang ditemukan tim**')
    temuan = vm.daftar_temuan_tim()
    if not temuan:
        st.caption('Belum ada.')
    for baris in temuan:
        st.markdown(baris)
    terdengar = vm.daftar_terdengar()
    if terdengar:
        st.markdown('**Terdengar dari Detektif AI** (hanya topik)')
        for baris in terdengar:
            st.markdown(baris)
    st.text_area('Catatan tim', key='catatan', height=120, placeholder='Tulis dugaan kalian di sini...')
