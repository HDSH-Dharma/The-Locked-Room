"""
teks_model.py
Model — template teks aksi dan kesimpulan untuk UI dan laporan. Data saja; pengisiannya di teks_service.
"""

# MARK: - Template

TEKS_AKSI = {'pindah': 'pindah ke {}', 'teleport': 'teleport ke {}', 'geledah': 'menggeledah {}',
              'interogasi': 'menginterogasi {}'}
FAKTA_PASTI = {'s': 'Pelaku pasti {}', 'w': 'Senjata pasti {}', 'r': 'TKP pasti {}'}
FAKTA_GUGUR = {'s': '{} bukan pelaku', 'w': 'Senjata bukan {}', 'r': 'TKP bukan {}'}
