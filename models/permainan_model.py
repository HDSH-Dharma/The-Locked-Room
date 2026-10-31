"""
permainan_model.py
Model — konstanta engine: pola aksi AI per level dan jumlah detektif. Data saja.
"""

# MARK: - Level dan detektif

LEVELS          = {'mudah': [2], 'normal': [2, 2, 3], 'sulit': [2, 3], 'ahli': [3]}
JUMLAH_DETEKTIF = 3
DETEKTIF        = tuple(range(1, JUMLAH_DETEKTIF + 1))
