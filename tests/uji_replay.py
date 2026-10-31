"""
uji_replay.py
Test — replay log di logs/ melawan AI yang dilawan saat main harus memberi hasil yang sama, dan
replay melawan semua AI lain harus jalan tanpa error.

  python -m tests.uji_replay
"""
from agents.daftar_agent import LAWAN_AI
from models.folder_model import FOLDER_LOGS
from services.log_service import muat_log
from services.replay_service import replay

# MARK: - Uji

def uji_replay(folder=FOLDER_LOGS):
    """Replay melawan AI yang dilawan saat main harus memberi hasil yang sama, dan replay
    melawan semua AI lain harus jalan tanpa error."""
    beda = konflik = 0
    logs = muat_log(folder)
    for path, log in logs:
        for nama, buat_agen in LAWAN_AI.items():
            _, hasil, k = replay(log, buat_agen())
            konflik += k
            if nama == log['ai_live'] and hasil['tipe'] != log['hasil']:
                beda += 1
                print('BEDA', path, hasil['tipe'], log['hasil'])
    print(f'{len(logs)} log, beda dengan hasil live: {beda}, konflik teleport: {konflik}')


if __name__ == '__main__':
    uji_replay()
