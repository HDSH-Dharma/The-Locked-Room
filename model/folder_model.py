"""
folder_model.py
Model — lokasi folder dan file data, dihitung dari lokasi repo supaya perintah bisa dijalankan
dari folder mana pun.
"""
import os

# MARK: - Folder

ROOT           = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDER_LOGS    = os.path.join(ROOT, 'logs')
FOLDER_LATIHAN = os.path.join(FOLDER_LOGS, 'latihan')
FOLDER_HASIL   = os.path.join(ROOT, 'hasil')
PATH_PEMBAGIAN = os.path.join(ROOT, 'pembagian.json')
