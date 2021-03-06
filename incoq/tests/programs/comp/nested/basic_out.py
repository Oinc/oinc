from incoq.runtime import *
# Comp1 := {(a, c) : (a, b) in E, (b, c) in E}
# Comp6 := {(x, z) : (x, y) in E, (y, z) in Comp1}
_m_E_out = Map()
def _maint__m_E_out_add(_e):
    (v11_1, v11_2) = _e
    if (v11_1 not in _m_E_out):
        _m_E_out[v11_1] = set()
    _m_E_out[v11_1].add(v11_2)

_m_E_in = Map()
def _maint__m_E_in_add(_e):
    (v9_1, v9_2) = _e
    if (v9_2 not in _m_E_in):
        _m_E_in[v9_2] = set()
    _m_E_in[v9_2].add(v9_1)

_m_Comp1_out = Map()
def _maint__m_Comp1_out_add(_e):
    (v7_1, v7_2) = _e
    if (v7_1 not in _m_Comp1_out):
        _m_Comp1_out[v7_1] = set()
    _m_Comp1_out[v7_1].add(v7_2)

def _maint__m_Comp1_out_remove(_e):
    (v8_1, v8_2) = _e
    _m_Comp1_out[v8_1].remove(v8_2)
    if (len(_m_Comp1_out[v8_1]) == 0):
        del _m_Comp1_out[v8_1]

Comp6 = RCSet()
def _maint_Comp6_E_add(_e):
    # Iterate {(v3_x, v3_y, v3_z) : (v3_x, v3_y) in deltamatch(E, 'bb', _e, 1), (v3_y, v3_z) in Comp1}
    (v3_x, v3_y) = _e
    for v3_z in (_m_Comp1_out[v3_y] if (v3_y in _m_Comp1_out) else set()):
        if ((v3_x, v3_z) not in Comp6):
            Comp6.add((v3_x, v3_z))
        else:
            Comp6.incref((v3_x, v3_z))

def _maint_Comp6_Comp1_add(_e):
    # Iterate {(v5_x, v5_y, v5_z) : (v5_x, v5_y) in E, (v5_y, v5_z) in deltamatch(Comp1, 'bb', _e, 1)}
    (v5_y, v5_z) = _e
    for v5_x in (_m_E_in[v5_y] if (v5_y in _m_E_in) else set()):
        if ((v5_x, v5_z) not in Comp6):
            Comp6.add((v5_x, v5_z))
        else:
            Comp6.incref((v5_x, v5_z))

def _maint_Comp6_Comp1_remove(_e):
    # Iterate {(v6_x, v6_y, v6_z) : (v6_x, v6_y) in E, (v6_y, v6_z) in deltamatch(Comp1, 'bb', _e, 1)}
    (v6_y, v6_z) = _e
    for v6_x in (_m_E_in[v6_y] if (v6_y in _m_E_in) else set()):
        if (Comp6.getref((v6_x, v6_z)) == 1):
            Comp6.remove((v6_x, v6_z))
        else:
            Comp6.decref((v6_x, v6_z))

Comp1 = RCSet()
def _maint_Comp1_E_add(_e):
    v1_DAS = set()
    # Iterate {(v1_a, v1_b, v1_c) : (v1_a, v1_b) in deltamatch(E, 'bb', _e, 1), (v1_b, v1_c) in E}
    (v1_a, v1_b) = _e
    for v1_c in (_m_E_out[v1_b] if (v1_b in _m_E_out) else set()):
        if ((v1_a, v1_b, v1_c) not in v1_DAS):
            v1_DAS.add((v1_a, v1_b, v1_c))
    # Iterate {(v1_a, v1_b, v1_c) : (v1_a, v1_b) in E, (v1_b, v1_c) in deltamatch(E, 'bb', _e, 1)}
    (v1_b, v1_c) = _e
    for v1_a in (_m_E_in[v1_b] if (v1_b in _m_E_in) else set()):
        if ((v1_a, v1_b, v1_c) not in v1_DAS):
            v1_DAS.add((v1_a, v1_b, v1_c))
    for (v1_a, v1_b, v1_c) in v1_DAS:
        if ((v1_a, v1_c) not in Comp1):
            Comp1.add((v1_a, v1_c))
            # Begin maint _m_Comp1_out after "Comp1.add((v1_a, v1_c))"
            _maint__m_Comp1_out_add((v1_a, v1_c))
            # End maint _m_Comp1_out after "Comp1.add((v1_a, v1_c))"
            # Begin maint Comp6 after "Comp1.add((v1_a, v1_c))"
            _maint_Comp6_Comp1_add((v1_a, v1_c))
            # End maint Comp6 after "Comp1.add((v1_a, v1_c))"
        else:
            Comp1.incref((v1_a, v1_c))
    del v1_DAS

for (v1, v2) in [(1, 2), (2, 3), (3, 4), (4, 5)]:
    # Begin maint _m_E_out after "E.add((v1, v2))"
    _maint__m_E_out_add((v1, v2))
    # End maint _m_E_out after "E.add((v1, v2))"
    # Begin maint _m_E_in after "E.add((v1, v2))"
    _maint__m_E_in_add((v1, v2))
    # End maint _m_E_in after "E.add((v1, v2))"
    # Begin maint Comp6 after "E.add((v1, v2))"
    _maint_Comp6_E_add((v1, v2))
    # End maint Comp6 after "E.add((v1, v2))"
    # Begin maint Comp1 after "E.add((v1, v2))"
    _maint_Comp1_E_add((v1, v2))
    # End maint Comp1 after "E.add((v1, v2))"
print(sorted(Comp6))