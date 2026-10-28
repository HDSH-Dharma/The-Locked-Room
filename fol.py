"""
First Order Logic sederhana untuk Rumah Terkunci (materi Lecture 05).

- Sintaks : konstanta, variabel, predikat, ¬ ∧ ∨ → ↔, ∀ dan ∃ (bertipe/sort)
- Universal instantiation : ∀x α  menjadi semua SUBST({x/k}, α)  (slide Reasoning hal. 3)
- Reduksi ke proposisional : setelah instansiasi, tiap atom ground menjadi
  satu simbol proposisi (slide Reasoning hal. 5)
- Konversi CNF : hilangkan ↔, hilangkan →, De Morgan, distribusi ∨ (slide hal. 7)

Formula disimpan sebagai tuple supaya ringan:
  ('atom', pred, (arg, ...))     ('not', f)     ('and', (f, ...))   ('or', (f, ...))
  ('imp', a, b)   ('iff', a, b)   ('forall', var, sort, f)   ('exists', var, sort, f)
  ('neq', t1, t2)  ('true',)  ('false',)
Variabel ditulis dengan awalan '?', misalnya '?x'.
"""
from itertools import product

TRUE = ('true',)
FALSE = ('false',)


# ---------- konstruktor ----------
def Atom(pred, *args):
    return ('atom', pred, tuple(args))


def Not(f):
    return ('not', f)


def And(*fs):
    return ('and', tuple(fs))


def Or(*fs):
    return ('or', tuple(fs))


def Imp(a, b):
    return ('imp', a, b)


def Iff(a, b):
    return ('iff', a, b)


def ForAll(var, sort, f):
    return ('forall', var, sort, f)


def Exists(var, sort, f):
    return ('exists', var, sort, f)


def Neq(a, b):
    return ('neq', a, b)


# ---------- tampilan ----------
def atom_str(pred, args):
    return f"{pred}({', '.join(args)})" if args else pred


def show(f):
    t = f[0]
    if t == 'atom':
        return atom_str(f[1], f[2])
    if t == 'not':
        inner = show(f[1])
        return '¬' + (inner if f[1][0] in ('atom', 'not') else f'({inner})')
    if t in ('and', 'or'):
        sym = ' ∧ ' if t == 'and' else ' ∨ '
        return sym.join(show(x) if x[0] in ('atom', 'not', 'neq') else f'({show(x)})' for x in f[1])
    if t == 'imp':
        return f'{_wrap(f[1])} → {_wrap(f[2])}'
    if t == 'iff':
        return f'{_wrap(f[1])} ↔ {_wrap(f[2])}'
    if t == 'forall':
        return f'∀{f[1][1:]} {_wrap(f[3])}'
    if t == 'exists':
        return f'∃{f[1][1:]} {_wrap(f[3])}'
    if t == 'neq':
        return f'{f[1].lstrip("?")}≠{f[2].lstrip("?")}'
    return '⊤' if t == 'true' else '⊥'


def _wrap(f):
    return show(f) if f[0] in ('atom', 'not', 'forall', 'exists') else f'({show(f)})'


# ---------- universal instantiation / reduksi ke proposisional ----------
def instantiate(f, domain, env=None):
    """Ganti setiap ∀ dengan konjungsi semua instansiasinya dan setiap ∃ dengan
    disjungsi (domain tertutup: hanya konstanta yang dikenal), lalu sederhanakan."""
    env = env or {}
    t = f[0]
    if t == 'atom':
        return ('atom', f[1], tuple(env.get(a, a) for a in f[2]))
    if t == 'neq':
        a, b = env.get(f[1], f[1]), env.get(f[2], f[2])
        return TRUE if a != b else FALSE
    if t in ('true', 'false'):
        return f
    if t == 'not':
        return _not(instantiate(f[1], domain, env))
    if t in ('and', 'or'):
        parts = [instantiate(x, domain, env) for x in f[1]]
        return _and(parts) if t == 'and' else _or(parts)
    if t == 'imp':
        return ('imp', instantiate(f[1], domain, env), instantiate(f[2], domain, env))
    if t == 'iff':
        return ('iff', instantiate(f[1], domain, env), instantiate(f[2], domain, env))
    if t in ('forall', 'exists'):
        var, sort, body = f[1], f[2], f[3]
        parts = [instantiate(body, domain, {**env, var: k}) for k in domain[sort]]
        return _and(parts) if t == 'forall' else _or(parts)
    raise ValueError(f)


def _not(f):
    if f == TRUE:
        return FALSE
    if f == FALSE:
        return TRUE
    return ('not', f)


def _and(parts):
    out = []
    for p in parts:
        if p == FALSE:
            return FALSE
        if p != TRUE:
            out.append(p)
    return TRUE if not out else out[0] if len(out) == 1 else ('and', tuple(out))


def _or(parts):
    out = []
    for p in parts:
        if p == TRUE:
            return TRUE
        if p != FALSE:
            out.append(p)
    return FALSE if not out else out[0] if len(out) == 1 else ('or', tuple(out))


# ---------- CNF ----------
def _elim(f):
    """Hilangkan ↔ lalu → (α ↔ β  =  (α → β) ∧ (β → α);  α → β  =  ¬α ∨ β)."""
    t = f[0]
    if t == 'iff':
        a, b = _elim(f[1]), _elim(f[2])
        return ('and', (('or', (('not', a), b)), ('or', (('not', b), a))))
    if t == 'imp':
        return ('or', (('not', _elim(f[1])), _elim(f[2])))
    if t == 'not':
        return ('not', _elim(f[1]))
    if t in ('and', 'or'):
        return (t, tuple(_elim(x) for x in f[1]))
    return f


def _nnf(f, neg=False):
    """Dorong negasi ke dalam dengan hukum De Morgan dan negasi ganda."""
    t = f[0]
    if t == 'not':
        return _nnf(f[1], not neg)
    if t == 'atom':
        return ('lit', atom_str(f[1], f[2]), not neg)
    if t in ('true', 'false'):
        return FALSE if (t == 'true') == neg else TRUE
    if t in ('and', 'or'):
        flip = {'and': 'or', 'or': 'and'}[t] if neg else t
        return (flip, tuple(_nnf(x, neg) for x in f[1]))
    raise ValueError(f)


def _clauses(f):
    """NNF -> daftar klausa (frozenset literal), distribusi ∨ atas ∧."""
    t = f[0]
    if t == 'lit':
        return [frozenset([(f[1], f[2])])]
    if t == 'true':
        return []
    if t == 'false':
        return [frozenset()]
    if t == 'and':
        out = []
        for x in f[1]:
            out.extend(_clauses(x))
        return out
    if t == 'or':
        result = [frozenset()]
        for x in f[1]:
            sub = _clauses(x)
            result = [a | b for a, b in product(result, sub)]
        return [c for c in result if not is_tautology(c)]
    raise ValueError(f)


def is_tautology(clause):
    return any((a, not p) in clause for a, p in clause)


def to_cnf(ground_formula):
    """Formula ground (tanpa kuantor) -> daftar klausa unik."""
    seen, out = set(), []
    for c in _clauses(_nnf(_elim(ground_formula))):
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def lit_str(lit):
    a, p = lit
    return a if p else '¬' + a


def clause_str(clause):
    if not clause:
        return '□ (klausa kosong)'
    return ' ∨ '.join(lit_str(l) for l in sorted(clause, key=lambda l: (l[0], not l[1])))
