"""
app.py
Entry point UI Streamlit: tim 3 detektif melawan Detektif AI.

  streamlit run app.py

- Mode normal : aksi AI ditampilkan satu per satu (animasi), tuduhan AI langsung mengakhiri game.
- Test mode   : AI langsung jalan tanpa animasi, tuduhan AI disembunyikan, dan game lanjut
                sampai tim menuduh atau sidang setelah ronde 7.
Setiap game test mode yang selesai disimpan ke logs/<inisial>_<seed>.json untuk replay.
Game mode normal adalah latihan; lognya disimpan ke logs/latihan/ yang tidak masuk git.
"""
from views.halaman_view import tampilkan_aplikasi

tampilkan_aplikasi()
