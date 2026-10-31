"""
manusia_agent.py
Agent — tim manusia untuk UI. Aksinya datang dari tombol, jadi kelas ini tidak punya logika sendiri.
"""
from agents.kontrak_agent import Tim

# MARK: - Tim manusia

class TimManusia(Tim):
    """Tim untuk Permainan saat dimainkan manusia. Aksi tim datang dari tombol UI; topik yang
    terdengar dari AI dicatat engine sebagai event ('tim', 'menguping')."""
    nama = 'manusia'
