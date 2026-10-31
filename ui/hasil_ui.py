"""
hasil_ui.py
UI — layar selesai: hasil, jawaban sebenarnya, durasi, dan reasoning trace Detektif AI.
"""
import streamlit as st

# MARK: - Layar selesai

def tampilkan(layar):
    layar.selesaikan()
    r = layar.ringkasan_hasil()
    if r['uji']:
        st.info(r['tuduhan_tim_teks'])
        st.markdown(r['tuduhan_ai'])
    getattr(st, r['jenis'])(r['teks'])
    if r['tuduhan_tim']:
        st.markdown(r['tuduhan_tim'])
    st.markdown(r['jawaban'])
    st.caption(r['durasi'])
    with st.expander('Reasoning trace Detektif AI', expanded=True):
        st.code(layar.trace(), language=None)
