"""
log.py
Logic — membaca dan menyimpan file log permainan. Log test mode ada di logs/, log latihan di
logs/latihan/ (tidak masuk git dan tidak ikut evaluasi).
"""
import glob
import json
import os

from model.folder_model import FOLDER_LOGS

# MARK: - Baca

def muat_log(folder=FOLDER_LOGS):
    """Semua log di folder (tidak termasuk subfolder latihan), urut nama file."""
    logs = []
    for path in sorted(glob.glob(os.path.join(folder, '*.json'))):
        with open(path, encoding='utf-8') as f:
            logs.append((path, json.load(f)))
    return logs


def log_ada(pemain, seed):
    """Apakah game test mode ini sudah punya log. Dipakai untuk menentukan jatah game berikutnya."""
    return os.path.exists(os.path.join(FOLDER_LOGS, f'{pemain}_{seed}.json'))


# MARK: - Simpan

def simpan_log(isi, folder, nama):
    """Simpan isi log ke folder dengan nama file yang belum dipakai. Mengembalikan path file."""
    os.makedirs(folder, exist_ok=True)
    path = _path_log_baru(folder, nama)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(isi, f, ensure_ascii=False, indent=1)
    return path


# MARK: - Private Helpers

def _path_log_baru(folder, nama):
    """Nama file yang belum dipakai, supaya log lama dengan kasus yang sama tidak tertimpa."""
    path, i = os.path.join(folder, nama + '.json'), 2
    while os.path.exists(path):
        path, i = os.path.join(folder, f'{nama}_{i}.json'), i + 1
    return path
