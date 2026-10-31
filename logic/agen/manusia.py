"""
manusia.py
Logic — tim manusia untuk UI. Aksinya datang dari tombol, jadi kelas ini tidak punya logika sendiri.
"""
from logic.agen.kontrak import Tim

# MARK: - Tim manusia

class TimManusia(Tim):
    """Tim untuk Permainan saat dimainkan manusia. Aksi tim datang dari tombol UI; topik yang
    terdengar dari AI dicatat engine sebagai event ('tim', 'menguping')."""
    nama = 'manusia'
