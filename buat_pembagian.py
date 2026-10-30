import json
import random

kasus = list(range(1, 301))
random.Random(2026).shuffle(kasus)
lawan = ['v2', 'v1', 'polisi', 'penebak']
pembagian = {}
for i, nama in enumerate(['GK', 'JC', 'HD']):        # inisial Grevi, Jason, Dharma
    daftar = kasus[i * 100:(i + 1) * 100]
    pembagian[nama] = [dict(no=j + 1, seed=s, lawan=lawan[j % 4]) for j, s in enumerate(daftar)]
json.dump(pembagian, open('pembagian.json', 'w'), indent=1)

