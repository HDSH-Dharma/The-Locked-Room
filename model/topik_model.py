"""
topik_model.py
Model — pemetaan predikat FOL ke topik bukti untuk fitur menguping. Data saja.
"""

# MARK: - Topik

TOPIK_PREDIKAT = {
    'tersangka': {'Pelaku', 'AdaAlibi', 'Kuat', 'PegangKunci', 'Ukuran43', 'JejakSepatu43',
                  'PuntungRokok', 'WasiatDiubah', 'DuaGelasKopi'},
    'senjata': {'Senjata', 'Utuh', 'LukaBerdarah'},
    'ruangan': {'TKP', 'Kosong', 'SerpihanKayu', 'NodaBasah', 'JendelaLotengTerbuka', 'LampuBerkedip'},
    'jasad': {'Dipindahkan', 'LebamTidakSesuai', 'LebamSesuai', 'AdaSeretan', 'AnjingMenggonggong'},
}
