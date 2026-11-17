import json, os, random, shutil, tempfile, zipfile

# Ванильные enchantment/*.json берутся прямо из серверного jar 26.2.
# Путь можно задать переменной окружения MC_SERVER_JAR, иначе ищется рядом со скриптом.
PACK = os.path.dirname(os.path.abspath(__file__))
JAR = os.environ.get('MC_SERVER_JAR', os.path.join(PACK, 'server-26.2.jar'))
SRC = os.path.join(tempfile.mkdtemp(prefix='enchantqol-'), 'vanilla')
BUILD = os.path.join(PACK, 'build')
VERSION = '1.0.0'

os.makedirs(SRC, exist_ok=True)
with zipfile.ZipFile(JAR) as _z:
    for _n in _z.namelist():
        if _n.startswith('data/minecraft/enchantment/') and _n.endswith('.json'):
            with open(os.path.join(SRC, os.path.basename(_n)), 'wb') as _f:
                _f.write(_z.read(_n))


# --- что кладём в стол (treasure-чары, без проклятий) ---
TREASURE_IN_TABLE = ['mending', 'frost_walker', 'soul_speed', 'swift_sneak', 'wind_burst']

# --- правки min_cost: (base, per_level_above_first) ---
COST_PATCH = {
    'sharpness':           (6, 7),    # 45 -> 34
    'smite':               (6, 7),    # 37 -> 34
    'bane_of_arthropods':  (6, 7),    # 37 -> 34
    'efficiency':          (1, 8),    # 41 -> 33
    'power':               (1, 8),    # 41 -> 33
    'quick_charge':        (12, 6),   # 52 -> 24  (в ваниле min>max, III не выпадал вообще)
    'thorns':              (10, 10),  # 50 -> 30
    'swift_sneak':         (15, 9),   # 75 -> 33
    'mending':             (20, 0),   # 25 -> 20, чтобы ловился уже со 2-й кнопки (2 уровня + 2 лазурита)
}

# --- правки weight (как часто чара выпадает из пула) ---
WEIGHT_PATCH = {
    'mending': 8,   # 2 -> 8: чтобы книга Mending ловилась за десяток прокруток, а не за сотню
}

# ---------- сборка пака ----------
if os.path.isdir(BUILD):
    shutil.rmtree(BUILD)
ench_dir = os.path.join(PACK, 'data', 'minecraft', 'enchantment')
tag_dir = os.path.join(PACK, 'data', 'minecraft', 'tags', 'enchantment')
os.makedirs(ench_dir, exist_ok=True)
os.makedirs(tag_dir, exist_ok=True)
os.makedirs(BUILD, exist_ok=True)

json.dump({
    'pack': {
        'min_format': [107, 0],
        'max_format': [108, 0],
        'pack_format': 107,
        'description': 'Enchant QoL: treasure enchants in the table, top levels reachable at 30',
    }
}, open(os.path.join(PACK, 'pack.mcmeta'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)

json.dump({'replace': False, 'values': ['#minecraft:non_treasure'] +
           ['minecraft:' + e for e in TREASURE_IN_TABLE]},
          open(os.path.join(tag_dir, 'in_enchanting_table.json'), 'w', encoding='utf-8'),
          indent=2, ensure_ascii=False)

for name in set(COST_PATCH) | set(WEIGHT_PATCH):
    d = json.load(open(os.path.join(SRC, name + '.json'), encoding='utf-8'))
    if name in COST_PATCH:
        base, per = COST_PATCH[name]
        d['min_cost'] = {'base': base, 'per_level_above_first': per}
    if name in WEIGHT_PATCH:
        d['weight'] = WEIGHT_PATCH[name]
    json.dump(d, open(os.path.join(ench_dir, name + '.json'), 'w', encoding='utf-8'),
              indent=2, ensure_ascii=False)

zpath = os.path.join(BUILD, 'enchant-qol-%s.zip' % VERSION)
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(os.path.join(PACK, 'pack.mcmeta'), 'pack.mcmeta')
    for root, _, files in os.walk(os.path.join(PACK, 'data')):
        for f in files:
            p = os.path.join(root, f)
            z.write(p, os.path.relpath(p, PACK).replace('\\', '/'))
print('собран', zpath, os.path.getsize(zpath), 'байт')

# ---------- симуляция ванильного алгоритма ----------
def load(pool, patched):
    out = {}
    for n in os.listdir(SRC):
        name = n[:-5]
        if patched and name in (set(COST_PATCH) | set(WEIGHT_PATCH)):
            d = json.load(open(os.path.join(ench_dir, n), encoding='utf-8'))
        else:
            d = json.load(open(os.path.join(SRC, n), encoding='utf-8'))
        if name in pool:
            out[name] = d
    return out

def level_for(d, power):
    for lvl in range(d['max_level'], 0, -1):
        mn = d['min_cost']['base'] + d['min_cost'].get('per_level_above_first', 0) * (lvl - 1)
        mx = d['max_cost']['base'] + d['max_cost'].get('per_level_above_first', 0) * (lvl - 1)
        if mn <= power <= mx:
            return lvl
    return None

def roll(pool, power, rng):
    res = []
    cands = list(pool)
    while True:
        avail = [(n, level_for(pool[n], power)) for n in cands]
        avail = [(n, l) for n, l in avail if l]
        if not avail:
            break
        total = sum(pool[n]['weight'] for n, _ in avail)
        r = rng.random() * total
        for n, l in avail:
            r -= pool[n]['weight']
            if r <= 0:
                pick = (n, l)
                break
        res.append(pick)
        if rng.randint(0, 49) >= power:
            break
        ex = pool[pick[0]].get('exclusive_set')
        if ex:
            cands = [n for n in cands if n == pick[0] or pool[n].get('exclusive_set') != ex]
        if not cands:
            break
        power //= 2
    return res

def cost(slot, rng, shelves=15):
    shelves = min(shelves, 15)
    base = rng.randint(0, 7) + 1 + (shelves >> 1) + rng.randint(0, shelves)
    if slot == 0:
        return max(base // 3, 1)
    if slot == 1:
        return base * 2 // 3 + 1
    return max(base, shelves * 2)

def sim(pool, slot, ench_value, n=20000, seed=7):
    rng = random.Random(seed)
    hits = {}
    for _ in range(n):
        p = cost(slot, rng)
        p += 1 + rng.randint(0, ench_value // 4 + 1) + rng.randint(0, ench_value // 4 + 1)
        p = round(p * (1 + (rng.random() + rng.random() - 1) * 0.15))
        for name, lvl in roll(pool, p, rng):
            key = '%s %s' % (name, lvl)
            hits[key] = hits.get(key, 0) + 1
    return {k: v * 100.0 / n for k, v in hits.items()}

ALL = [n[:-5] for n in os.listdir(SRC) if n.endswith('.json')]
GEAR = {
    'алмазный меч (кнопка 3)': (['sharpness', 'smite', 'bane_of_arthropods', 'knockback', 'fire_aspect',
                                 'looting', 'sweeping_edge', 'unbreaking', 'mending'], 2, 10),
    'алмазная кирка (кнопка 3)': (['efficiency', 'fortune', 'silk_touch', 'unbreaking', 'mending'], 2, 10),
    'алмазный нагрудник (кнопка 3)': (['protection', 'fire_protection', 'blast_protection',
                                       'projectile_protection', 'thorns', 'unbreaking', 'mending'], 2, 10),
    'книга (кнопка 3)': (ALL, 2, 1),
    'книга (кнопка 2)': (ALL, 1, 1),
    'книга (кнопка 1)': (ALL, 0, 1),
}

for patched in (False, True):
    label = 'ПОСЛЕ' if patched else 'ДО'
    print('\n=== %s ===' % label)
    for title, (pool_names, slot, ev) in GEAR.items():
        pool = load(pool_names, patched)
        st = sim(pool, slot, ev)
        top = sorted(st.items(), key=lambda x: -x[1])[:6]
        interesting = {k: round(v, 1) for k, v in st.items()
                       if k.split()[0] in ('mending', 'sharpness', 'efficiency', 'protection', 'unbreaking',
                                           'fortune', 'looting', 'quick_charge', 'swift_sneak', 'thorns')}
        print('%-28s топ: %s' % (title, ', '.join('%s=%.1f%%' % (k, v) for k, v in top)))
        print('%-28s ключевые: %s' % ('', ', '.join('%s=%.1f%%' % (k, v) for k, v in sorted(interesting.items()))))
