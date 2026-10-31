"""
aksi_ui.py
UI — tombol aksi detektif dan form tuduhan. Daftar tombol disiapkan LayarPermainan.
"""
import streamlit as st

# MARK: - Panel aksi

def panel_aksi(layar, d):
    st.markdown(layar.judul_panel_aksi(d))
    for keterangan, daftar in layar.tombol_aksi(d):
        st.caption(keterangan)
        for t in daftar:
            _tombol(d, t)


# MARK: - Panel tuduhan

def panel_tuduh(layar, sidang=False):
    with st.form('form_tuduh'):
        st.markdown('**Tuduh** · hanya sekali. Kalau salah, tim kalah.')
        for label, pilihan, format_func, key in layar.pilihan_tuduhan():
            st.selectbox(label, pilihan, format_func=format_func, key=key)
        st.form_submit_button('Tuduh sekarang', on_click=_klik_tuduh, type='primary', width='stretch')
    if sidang:
        st.button('Tidak menuduh, serahkan ke hakim', on_click=_klik_serahkan, width='stretch')


# MARK: - Private Helpers

def _tombol(d, t):
    if t['disabled']:
        st.button(t['label'], key=t['key'], disabled=True, width='stretch', help=t['help'])
    else:
        st.button(t['label'], key=t['key'], on_click=_klik_aksi, args=(d, t['aksi']),
                  type='primary' if t['primary'] else 'secondary', width='stretch')


# Callback tombol membaca st.session_state.layar saat diklik, jadi selalu game yang sedang berjalan.
def _klik_aksi(d, aksi):
    if st.session_state.layar.jalankan_aksi(d, aksi):
        st.session_state.ai_pending = True


def _klik_tuduh():
    ss = st.session_state
    ss.layar.tuduh((ss.tuduh_s, ss.tuduh_w, ss.tuduh_r))


def _klik_serahkan():
    st.session_state.layar.serahkan_ke_hakim()
