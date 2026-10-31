"""
mixin.py
Logic — kemampuan bersama yang dipasang ke Detektif AI atau tim (mixin).

- PengingatTopik   : mencatat topik bukti yang terdengar saat menguping lawan.
- PemeriksaModel   : menyaring 64 kemungkinan jawaban (model checking proposisional).
- PerencanaLangkah : merencanakan gerak dengan A* atau BFS, lalu menjalankan aksi pertamanya.
"""
from logic.kasus.topik import kunci_topik
from logic.layar.teks import teks_rencana
from logic.penalaran.planning import rencanakan
from model.rumah_model import ALL_WORLDS

# MARK: - Menguping

class PengingatTopik:
    """Mixin: menyimpan topik hasil menguping. Topik bukan fakta logika, jadi tidak masuk KB."""

    def dengar(self, jenis, target, topik):
        self.topik[kunci_topik(jenis, target)] = list(topik)

    def _lupakan_topik(self):
        self.topik = {}


# MARK: - Model checking

class PemeriksaModel:
    """Mixin model checking: setiap bukti membuang model (pelaku, senjata, TKP) yang bertentangan."""

    def terbuka(self):
        """Kategori jawaban yang belum pasti."""
        pelaku, senjata, tkp = kemungkinan(self.models)
        return dict(tersangka=len(pelaku) > 1, senjata=len(senjata) > 1, ruangan=len(tkp) > 1)

    def _mulai_model(self):
        self.models = list(ALL_WORLDS)

    def _saring(self, clue):
        self.models = [m for m in self.models if clue['prop'](m)]


def kemungkinan(models):
    """Nilai yang masih mungkin untuk pelaku, senjata, dan TKP."""
    return ({m.s for m in models}, {m.w for m in models}, {m.r for m in models})


# MARK: - Gerak

class PerencanaLangkah:
    """Mixin gerak Detektif AI: rencanakan sampai informasi baru berikutnya, jalankan aksi
    pertamanya saja (online replanning). Subkelas menentukan ALGORITMA ('astar' atau 'bfs')
    dan target(searched, asked) -> (ruangan target, tersangka target)."""
    ALGORITMA = 'astar'

    def target(self, searched, asked):
        raise NotImplementedError

    def aksi(self, pos, searched, asked, punya_tp=False):
        target = self.target(searched, asked)
        if not any(target):
            return None, {}
        plan, expanded, ditahan = rencanakan(pos, searched, asked, target, self.case['loc'],
                                             punya_tp=punya_tp, algoritma=self.ALGORITMA)
        self.stats['simpul_planner'] += expanded
        self.stats['rencana'] += 1
        self.stats['teleport_ditahan'] += ditahan
        if not plan:
            return None, {}
        return plan[0], dict(rencana=teks_rencana(plan), simpul=expanded)
