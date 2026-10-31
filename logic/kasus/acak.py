"""
acak.py
Logic — RNG mulberry32 dan pemilihan acak.

Disalin persis dari versi JavaScript awal, supaya nomor kasus yang sama selalu menghasilkan
kasus yang sama. Python tidak punya integer 32-bit, jadi setiap operasi di-mask 0xFFFFFFFF.
"""

# MARK: - Konstanta

MASK = 0xFFFFFFFF


# MARK: - RNG

def make_rng(seed):
    state = [seed & MASK]

    def rnd():
        a = (state[0] + 0x6D2B79F5) & MASK
        state[0] = a
        t = _imul(a ^ (a >> 15), 1 | a)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & MASK) ^ t
        return ((t ^ (t >> 14)) & MASK) / 4294967296
    return rnd


def pick(rnd, arr):
    return arr[int(rnd() * len(arr))]


def shuffle(rnd, arr):
    a = list(arr)
    for i in range(len(a) - 1, 0, -1):
        j = int(rnd() * (i + 1))
        a[i], a[j] = a[j], a[i]
    return a


def weighted_pick(rnd, opts):
    total = sum(o['weight'] for o in opts)
    x     = rnd() * total
    for o in opts:
        x -= o['weight']
        if x <= 0:
            return o
    return opts[-1]


# MARK: - Private Helpers

def _imul(a, b):
    return (a * b) & MASK
