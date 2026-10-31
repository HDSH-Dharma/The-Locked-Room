"""
evaluasi_model.py
Model — definisi hasil game dan kolom tabel evaluasi. Data saja.
"""

# MARK: - Hasil game

HASIL_GAME    = ('tim', 'tim-salah', 'ai', 'ai-salah', 'vonis')
MENANG_PEMAIN = ('tim', 'ai-salah')  # tuduhan AI yang salah membuat AI kalah (proposal)
MENANG_AI     = ('ai', 'tim-salah')

# MARK: - Kolom laporan

KOLOM_LAPORAN = [('pemain_menang', 'Pemain menang'), ('ai_menang', 'AI menang'), ('seri', 'Seri'),
                 ('presisi_tuduhan', 'Presisi tuduhan AI'), ('ronde_ai_menang', 'Ronde saat AI menang'),
                 ('aksi_ai', 'Aksi AI'), ('presisi_useless', 'Presisi useless'), ('recall_useless', 'Recall useless'),
                 ('konflik_teleport', 'Konflik teleport')]
