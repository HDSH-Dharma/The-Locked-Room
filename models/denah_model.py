"""
denah_model.py
Model — data denah rumah (9, 12, dan 16 ruangan). Data saja, tanpa logika.

Setiap ruangan: (id, nama tampil, baris, kolom). Denah 9 ruangan dipakai di game. Denah 12 dan 16
menambah kolom/baris baru (Ruang Tamu tetap titik awal) untuk menguji skala, misalnya A* vs BFS
di rumah yang lebih besar.
"""

# MARK: - Denah

LAYOUTS = {
    '9': [
        ('gudang', 'Gudang', 0, 0), ('loteng', 'Loteng', 0, 1), ('kamar', 'Kamar Tidur', 0, 2),
        ('perpus', 'Perpustakaan', 1, 0), ('dapur', 'Dapur', 1, 1), ('kmandi', 'Kamar Mandi', 1, 2),
        ('rtamu', 'Ruang Tamu', 2, 0), ('rmakan', 'Ruang Makan', 2, 1), ('taman', 'Taman', 2, 2),
    ],
    '12': [
        ('gudang', 'Gudang', 0, 0), ('loteng', 'Loteng', 0, 1),
        ('kamar', 'Kamar Tidur', 0, 2), ('balkon', 'Balkon', 0, 3),
        ('perpus', 'Perpustakaan', 1, 0), ('dapur', 'Dapur', 1, 1),
        ('kmandi', 'Kamar Mandi', 1, 2), ('rkerja', 'Ruang Kerja', 1, 3),
        ('rtamu', 'Ruang Tamu', 2, 0), ('rmakan', 'Ruang Makan', 2, 1),
        ('taman', 'Taman', 2, 2), ('garasi', 'Garasi', 2, 3),
    ],
    '16': [
        ('gudang', 'Gudang', 0, 0), ('loteng', 'Loteng', 0, 1),
        ('kamar', 'Kamar Tidur', 0, 2), ('balkon', 'Balkon', 0, 3),
        ('perpus', 'Perpustakaan', 1, 0), ('dapur', 'Dapur', 1, 1),
        ('kmandi', 'Kamar Mandi', 1, 2), ('rkerja', 'Ruang Kerja', 1, 3),
        ('rmusik', 'Ruang Musik', 2, 0), ('rmakan', 'Ruang Makan', 2, 1),
        ('taman', 'Taman', 2, 2), ('garasi', 'Garasi', 2, 3),
        ('rtamu', 'Ruang Tamu', 3, 0), ('teras', 'Teras', 3, 1),
        ('kolam', 'Kolam Renang', 3, 2), ('gazebo', 'Gazebo', 3, 3),
    ],
}
