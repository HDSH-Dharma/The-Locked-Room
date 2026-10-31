"""
fol_model.py
Model — bentuk formula First Order Logic dan konstruktornya. Tanpa logika inferensi
(instansiasi dan CNF ada di fol_service).

Formula disimpan sebagai tuple supaya ringan, immutable, dan bisa dibandingkan:
  ('atom', pred, (arg, ...))     ('not', f)     ('and', (f, ...))   ('or', (f, ...))
  ('imp', a, b)   ('iff', a, b)   ('forall', var, sort, f)   ('exists', var, sort, f)
  ('neq', t1, t2)  ('true',)  ('false',)
Variabel ditulis dengan awalan '?', misalnya '?x'.
"""

# MARK: - Konstanta

TRUE  = ('true',)
FALSE = ('false',)

# MARK: - Konstruktor

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
