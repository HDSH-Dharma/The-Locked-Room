"""
kb_service.py
Service — basis pengetahuan Detektif AI v2: TELL menambah formula, ASK memakai resolusi.

Aturan dan pengetahuan latar ada di aturan_model. Di sini aturan diinstansiasi (universal
instantiation), diubah ke CNF, lalu dijawab dengan resolusi refutasi.
"""
from models.aturan_model import ATURAN, LATAR
from models.fol_model import Atom, Not
from models.rumah_model import C, DOMAIN, S_IDS, TKP, W_IDS
from services.fol_service import atom_str, instantiate, to_cnf
from services.resolusi_service import Prover

# MARK: - Predikat

def predikat(f, out):
    if f[0] == 'atom':
        out.add(f[1])
    elif f[0] == 'not':
        predikat(f[1], out)
    elif f[0] in ('and', 'or'):
        for g in f[1]:
            predikat(g, out)
    elif f[0] in ('imp', 'iff'):
        predikat(f[1], out)
        predikat(f[2], out)
    elif f[0] in ('forall', 'exists'):
        predikat(f[3], out)
    return out


# MARK: - Indeks (dihitung sekali saat modul dimuat)

RULE_PREDICATES = set()
for _, _, _f in ATURAN:
    predikat(_f, RULE_PREDICATES)

# Atom yang ditanyakan untuk menentukan jawaban
QUERY_ATOMS = [('s', i, atom_str('Pelaku', (C[i],))) for i in S_IDS] \
    + [('w', i, atom_str('Senjata', (C[i],))) for i in W_IDS] \
    + [('r', i, atom_str('TKP', (C[i],))) for i in TKP]


# MARK: - Knowledge base

def ground_clauses(formula, label):
    return [(c, label) for c in to_cnf(instantiate(formula, DOMAIN))]


class KB:
    """Basis pengetahuan FOL: TELL menambah formula, ASK memakai resolusi."""

    def __init__(self, found, pure=True, limit=60000):
        self.pure, self.limit = pure, limit
        self.clauses      = []
        self.rule_clauses = []
        for name, _, f in ATURAN:
            self.rule_clauses += ground_clauses(f, name)
        for f in LATAR:
            self.rule_clauses += ground_clauses(f, 'latar')
        self.clauses = list(self.rule_clauses)
        # Informasi publik: tempat jasad ditemukan
        for t in TKP:
            f = Atom('DitemukanDi', C[t]) if t == found else Not(Atom('DitemukanDi', C[t]))
            self.clauses += ground_clauses(f, 'jasad ditemukan')
        self._prover       = None
        self._rules_prover = None

    def tell(self, formula, label):
        new = ground_clauses(formula, label)
        self.clauses += new
        self._prover = None
        return new

    def prover(self):
        if self._prover is None:
            self._prover = Prover(self.clauses, self.limit, self.pure)
        return self._prover

    def rules_prover(self):
        if self._rules_prover is None:
            self._rules_prover = Prover(self.rule_clauses, self.limit, self.pure)
        return self._rules_prover

    def ask(self, lit):
        """KB ⊨ lit? Mengembalikan (hasil, prover, id klausa kosong); hasil None = kena batas langkah."""
        return self.prover().entails(lit)

    def atoms(self):
        return {a for c, _ in self.clauses for a, _ in c}
